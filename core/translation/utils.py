"""
ASL Translation Engine — Text/Symbol/Gesture Conversion Rules

This module is the core of the ASL Connect communication system.
It determines what each participant sees when a message is sent,
based on the sender's and receiver's user types.

Communication Rules Summary:
╔══════════════╦═══════════════╦═══════════════════════════════════════╗
║  Sender      ║  Receiver     ║  What Receiver Sees                  ║
╠══════════════╬═══════════════╬═══════════════════════════════════════╣
║ ASL User     ║ Hearing       ║ Translated English text              ║
║ Hearing      ║ ASL User      ║ Gesture video or ASL symbol display ║
║ Same type    ║ Same type     ║ Original format unchanged            ║
╚══════════════╩═══════════════╩═══════════════════════════════════════╝

Key functions:
- translate_message(): Master dispatcher — converts based on user types
- find_gesture_match(): Matches text to known gesture database
- translate_text_to_asl(): Converts text strings to ASL symbol arrays
- translate_asl_symbols_to_text(): Converts ASL symbols back to text
"""

from core.categories.models import ASLSymbol, Gesture


def resolve_asl_image_urls(asl_content):
    """
    Re-resolve ASL symbol image URLs from the database to ensure they
    use the current file format (e.g., .webp instead of stale .jpeg).
    """
    if not asl_content:
        return asl_content
    chars = [item['char'] for item in asl_content if item.get('char') and item['char'] != ' ']
    if not chars:
        return asl_content
    symbol_map = {
        s.character: s.image.url
        for s in ASLSymbol.objects.filter(character__in=chars)
    }
    resolved = []
    for item in asl_content:
        item = dict(item)
        char = item.get('char')
        if char and char in symbol_map:
            item['image_url'] = symbol_map[char]
        resolved.append(item)
    return resolved


def translate_asl_to_text(asl_symbol_ids):
    """
    Convert ASL symbol database IDs back to a readable text string.

    Used when loading stored message data that references symbols by ID.
    Example: [12, 5, 8] → 'HEL'
    """
    if not asl_symbol_ids:
        return ''
    symbols = ASLSymbol.objects.filter(id__in=asl_symbol_ids)
    symbol_map = {s.id: s.character for s in symbols}
    return ''.join(symbol_map.get(sid, '?') for sid in asl_symbol_ids)


def translate_asl_symbols_to_text(asl_symbol_data):
    """
    Convert ASL symbol data array (with char fields) back to a text string.

    Used for real-time message display where the symbol data is sent
    inline rather than referenced by ID.
    Example: [{'char': 'H'}, {'char': 'I'}] → 'HI'
    """
    if not asl_symbol_data:
        return ''
    chars = []
    for item in asl_symbol_data:
        char = item.get('char')
        if char is not None:
            chars.append(char)
    return ''.join(chars)


def translate_text_to_asl(text):
    """
    Convert English text to an array of ASL symbol image references.

    Each character A-Z and 0-9 is looked up in the database for its
    hand-sign image. Spaces are preserved as explicit space markers.
    Unmatched characters are returned without an image.

    Used by the Normal→ASL translation path so hearing users' text
    messages are displayed as ASL finger-spelling for deaf users.
    """
    if not text:
        return []
    chars = text.upper()
    symbols = ASLSymbol.objects.filter(character__in=list(chars))
    symbol_map = {s.character: s for s in symbols}
    result = []
    for char in chars:
        if char == ' ':
            result.append({'char': ' ', 'image_url': None, 'id': None})
        elif char in symbol_map:
            s = symbol_map[char]
            result.append({'char': s.character, 'image_url': s.image.url if s.image else None, 'id': s.id})
        else:
            result.append({'char': char, 'image_url': None, 'id': None})
    return result


def find_gesture_match(text):
    """
    Attempt to match a text string to a known gesture in the database.

    Matching priority:
    1. Exact match on gesture.translation (most specific)
    2. Exact match on gesture.title
    3. Keyword list contains the text (comma-separated in gesture.keywords)

    Returns the first matching Gesture object, or None if no match found.
    Used by the Normal→ASL path to show a gesture video when the
    hearing user types a word that corresponds to a known ASL sign.
    """
    if not text:
        return None
    text_lower = text.strip().lower()
    gestures = Gesture.objects.all()
    for gesture in gestures:
        if gesture.translation and gesture.translation.strip().lower() == text_lower:
            return gesture
    for gesture in gestures:
        if gesture.title and gesture.title.strip().lower() == text_lower:
            return gesture
    for gesture in gestures:
        if gesture.keywords:
            keywords = [k.strip().lower() for k in gesture.keywords.split(',')]
            if text_lower in keywords:
                return gesture
    return None


def translate_message(sender_is_asl, receiver_is_asl, content, message_type, asl_content=None, gesture_id=None):
    """
    Master translation function implementing all communication rules.

    Determines how a message should be displayed to each participant
    based on their user types (ASL user vs hearing user).

    Parameters:
    - sender_is_asl: Whether the sender is an ASL (deaf) user
    - receiver_is_asl: Whether the receiver is an ASL (deaf) user
    - content: Raw text content of the message
    - message_type: 'text', 'asl', or 'gesture'
    - asl_content: JSON array of ASL symbol data (for asl-type messages)
    - gesture_id: FK to Gesture model (for gesture-type messages)

    Returns a dict with separate display fields for sender and receiver:
    - display_content / sender_display_content
    - display_type / sender_display_type
    - display_asl / sender_display_asl (ASL symbol array)
    - display_gesture / sender_display_gesture (gesture object)

    Translation Rules:
    - ASL sender → Hearing receiver: Symbols/gestures become English text
    - Hearing sender → ASL receiver: English text becomes gestures or ASL symbols
    - Same-type communication: Original format is preserved
    - Senders always see their own original message format
    """
    from core.categories.models import Gesture

    # --- Receiver display: translated for the viewer's user type ---
    receiver = {
        'display_content': content,
        'display_type': message_type,
        'display_asl': resolve_asl_image_urls(asl_content) if message_type == 'asl' else None,
        'display_gesture': None,
    }

    # ASL -> Normal: translate symbols/gestures to English text
    if sender_is_asl and not receiver_is_asl:
        if gesture_id:
            try:
                gesture = Gesture.objects.get(id=gesture_id)
                receiver['display_content'] = gesture.translation or gesture.title
                receiver['display_type'] = 'text'
            except Gesture.DoesNotExist:
                receiver['display_content'] = content or ''
                receiver['display_type'] = 'text'
        elif asl_content:
            receiver['display_content'] = translate_asl_symbols_to_text(asl_content)
            receiver['display_type'] = 'text'
        else:
            receiver['display_content'] = content or ''
            receiver['display_type'] = 'text'
        receiver['display_asl'] = None
        receiver['display_gesture'] = None

    # Same type (ASL->ASL or Normal->Normal): no translation needed
    elif sender_is_asl == receiver_is_asl:
        if gesture_id:
            try:
                gesture = Gesture.objects.get(id=gesture_id)
                receiver['display_gesture'] = {
                    'id': gesture.id,
                    'title': gesture.title,
                    'translation': gesture.translation,
                    'video_url': gesture.video.url if gesture.video else None,
                }
                receiver['display_type'] = 'gesture'
                receiver['display_asl'] = None
            except Gesture.DoesNotExist:
                pass
        elif asl_content:
            receiver['display_asl'] = resolve_asl_image_urls(asl_content)
            receiver['display_type'] = 'asl'

    # Normal -> ASL: check gesture match first, then fall back to ASL symbols
    elif not sender_is_asl and receiver_is_asl:
        gesture_match = find_gesture_match(content) if content else None
        if gesture_match:
            receiver['display_gesture'] = {
                'id': gesture_match.id,
                'title': gesture_match.title,
                'translation': gesture_match.translation,
                'video_url': gesture_match.video.url if gesture_match.video else None,
            }
            receiver['display_type'] = 'gesture'
            receiver['display_asl'] = None
        else:
            asl_symbols = translate_text_to_asl(content) if content else []
            receiver['display_asl'] = asl_symbols
            receiver['display_type'] = 'asl'

    # --- Sender display: always shows original message format ---
    sender = {
        'display_content': content,
        'display_type': message_type,
        'display_asl': resolve_asl_image_urls(asl_content) if message_type == 'asl' else None,
        'display_gesture': None,
    }

    # Enrich sender display with gesture data if applicable (both ASL and normal senders)
    if gesture_id:
        try:
            gesture = Gesture.objects.get(id=gesture_id)
            sender['display_gesture'] = {
                'id': gesture.id,
                'title': gesture.title,
                'translation': gesture.translation,
                'video_url': gesture.video.url if gesture.video else None,
            }
            sender['display_type'] = 'gesture'
            sender['display_asl'] = None
        except Gesture.DoesNotExist:
            pass

    return {
        'content': content,
        'message_type': message_type,
        'asl_content': asl_content,
        'gesture_id': gesture_id,
        # Receiver display fields (what the OTHER person sees)
        'display_content': receiver['display_content'],
        'display_type': receiver['display_type'],
        'display_asl': receiver['display_asl'],
        'display_gesture': receiver['display_gesture'],
        # Sender display fields (what the SENDER sees for their own message)
        'sender_display_content': sender['display_content'],
        'sender_display_type': sender['display_type'],
        'sender_display_asl': sender['display_asl'],
        'sender_display_gesture': sender['display_gesture'],
    }
