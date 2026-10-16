"""
Custom Template Tags -- Design Tags
======================================
Django template filters for rendering JSON-based design settings and
data structures inside Django templates.
"""

import json

from django import template

register = template.Library()


@register.filter
def json_loads(value):
    """Parse a JSON string into a Python object (list or dict).

    Returns an empty list on failure so templates never crash.

    Usage::

        {% for item in data|json_loads %}
            {{ item.title }}
        {% endfor %}
    """
    if not value:
        return []
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []


@register.filter
def get_item(dictionary, key):
    """Safely retrieve a value from a dictionary by key.

    Returns an empty string if the key is missing.

    Usage::

        {{ my_dict|get_item:'some_key' }}
    """
    return dictionary.get(key, '')
