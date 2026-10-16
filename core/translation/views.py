"""
Translation API Views — Text-to-ASL and ASL-to-Text Conversion Endpoints

Provides AJAX endpoints for the frontend to:
1. Convert English text to ASL symbol images (with optional gesture match)
2. Convert ASL symbol data back to readable English text

These endpoints power the ASL keyboard composition UI and the
real-time message translation preview feature.
"""

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from .utils import (
    translate_text_to_asl,
    translate_asl_to_text,
    translate_asl_symbols_to_text,
    find_gesture_match,
)


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(login_required, name='dispatch')
class TranslateTextToASL(View):
    """
    Convert English text into ASL symbol images for display.

    Also detects if the input text matches a known gesture in the database
    so the UI can offer a gesture video as an alternative visualization.

    POST body: { 'text': 'Hello' }
    Response: {
        'asl_symbols': [{ 'char': 'H', 'image_url': '...' }, ...],
        'gesture': { 'id': 1, 'title': 'Hello', ... } or null
    }
    """

    def post(self, request):
        try:
            data = json.loads(request.body)
            text = data.get('text', '')

            if not text:
                return JsonResponse({'success': False, 'error': 'text required'}, status=400)

            gesture_match = find_gesture_match(text)
            asl_symbols = translate_text_to_asl(text)

            return JsonResponse({
                'success': True,
                'asl_symbols': asl_symbols,
                'gesture': {
                    'id': gesture_match.id,
                    'title': gesture_match.title,
                    'translation': gesture_match.translation,
                    'video_url': gesture_match.video.url if gesture_match.video else None,
                } if gesture_match else None,
            })

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(login_required, name='dispatch')
class TranslateASLToText(View):
    """
    Convert ASL symbol data (IDs or char arrays) back to readable text.

    Accepts either database symbol IDs or inline symbol data arrays,
    making it flexible for both stored and real-time message conversion.

    POST body: { 'asl_ids': [12, 5, 8] } or { 'asl_data': [{ 'char': 'H' }, ...] }
    Response: { 'text': 'HELLO' }
    """

    def post(self, request):
        try:
            data = json.loads(request.body)
            asl_ids = data.get('asl_ids')
            asl_data = data.get('asl_data')

            text = ''
            if asl_ids:
                text = translate_asl_to_text(asl_ids)
            elif asl_data:
                text = translate_asl_symbols_to_text(asl_data)

            return JsonResponse({
                'success': True,
                'text': text,
            })

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
