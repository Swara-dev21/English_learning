# learning/templatetags/learning_filters.py

from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()


@register.filter
def getattr_filter(obj, attr_name):
    """
    Get attribute from object dynamically.
    Usage: {{ object|getattr_filter:"field_name" }}
    """
    if obj is None or not attr_name:
        return None
    try:
        return getattr(obj, attr_name, None)
    except AttributeError:
        return None
    except Exception:
        return None


@register.filter
def get_section_status(progress, section_name):
    """
    Get completion status for a specific section.
    Usage: {{ progress|get_section_status:"listening" }}
    Returns: True/False
    """
    if not progress or not section_name:
        return False
    
    # Handle 'game' as 'activity' for backward compatibility
    if section_name == 'game':
        section_name = 'activity'
    
    # Use the model's method if available (cleaner)
    if hasattr(progress, 'get_section_status'):
        return progress.get_section_status(section_name)
    
    # Fallback to direct attribute access
    field_name = f"{section_name}_completed"
    try:
        return getattr(progress, field_name, False)
    except AttributeError:
        return False


@register.filter
def multiply(value, arg):
    """
    Multiply value by arg.
    Usage: {{ value|multiply:2 }}
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def divide(value, arg):
    """
    Divide value by arg.
    Usage: {{ value|divide:100 }}
    """
    try:
        if float(arg) == 0:
            return 0
        return float(value) / float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def percentage(value, total):
    """
    Calculate percentage.
    Usage: {{ value|percentage:total }}
    """
    try:
        if float(total) == 0:
            return 0
        return (float(value) / float(total)) * 100
    except (ValueError, TypeError):
        return 0


@register.filter
@stringfilter
def truncate_chars(value, arg):
    """
    Truncate string to specified number of characters.
    Usage: {{ text|truncate_chars:100 }}
    """
    try:
        limit = int(arg)
        if len(value) <= limit:
            return value
        return value[:limit] + '...'
    except (ValueError, TypeError):
        return value


@register.filter
def get_item(dictionary, key):
    """
    Get item from dictionary by key.
    Usage: {{ dict|get_item:"key_name" }}
    """
    if dictionary is None:
        return None
    try:
        return dictionary.get(key)
    except AttributeError:
        return None
    except Exception:
        return None


@register.filter
def get_progress_percentage(progress, day):
    """
    Get overall progress percentage for a day.
    Usage: {{ progress|get_progress_percentage:day }}
    """
    if not progress:
        return 0
    try:
        return progress.get_overall_progress()
    except AttributeError:
        return 0


@register.filter
def is_completed(progress):
    """
    Check if a day is completed.
    Usage: {{ progress|is_completed }}
    """
    if not progress:
        return False
    try:
        return progress.is_completed
    except AttributeError:
        return False


@register.filter
def get_score(progress):
    """
    Get score for a day.
    Usage: {{ progress|get_score }}
    """
    if not progress:
        return 0
    try:
        return int(progress.score)
    except (AttributeError, ValueError):
        return 0


@register.filter
def format_time(minutes):
    """
    Format minutes into readable time.
    Usage: {{ minutes|format_time }}
    """
    try:
        minutes = int(minutes)
        if minutes < 60:
            return f"{minutes} min"
        hours = minutes // 60
        mins = minutes % 60
        if mins == 0:
            return f"{hours} hour{'s' if hours > 1 else ''}"
        return f"{hours}h {mins}m"
    except (ValueError, TypeError):
        return "30 min"


@register.filter
def get_task_type_icon(task_type):
    """
    Get FontAwesome icon for task type.
    Usage: {{ task.task_type|get_task_type_icon }}
    """
    icons = {
        'mcq': 'fas fa-question-circle',
        'text': 'fas fa-pencil-alt',
        'audio': 'fas fa-headphones',
        'speaking': 'fas fa-microphone',
    }
    return icons.get(task_type, 'fas fa-tasks')


@register.filter
def get_section_icon(section_name):
    """
    Get FontAwesome icon for section.
    Usage: {{ section.name|get_section_icon }}
    """
    icons = {
        'listening': 'fas fa-headphones',
        'reading': 'fas fa-book-open',
        'writing': 'fas fa-pen-fancy',
        'speaking': 'fas fa-microphone-alt',
        'game': 'fas fa-puzzle-piece',
        'activity': 'fas fa-puzzle-piece',
    }
    return icons.get(section_name, 'fas fa-folder')


@register.filter
def get_section_color(section_name):
    """
    Get color class for section.
    Usage: {{ section.name|get_section_color }}
    """
    colors = {
        'listening': '#3b82f6',
        'reading': '#8b5cf6',
        'writing': '#10b981',
        'speaking': '#f59e0b',
        'game': '#ec4898',
        'activity': '#ec4898',
    }
    return colors.get(section_name, '#6b7280')


@register.filter
def get_level_color(level_name):
    """
    Get color for level.
    Usage: {{ level.name|get_level_color }}
    """
    colors = {
        'beginner': '#667eea',
        'intermediate': '#f59e0b',
        'advanced': '#10b981',
    }
    return colors.get(level_name, '#4a62b0')


@register.filter
def split(value, arg):
    """
    Split a string by the given delimiter.
    Usage: {{ text|split:"," }}
    """
    if not value:
        return []
    try:
        return value.split(arg)
    except (AttributeError, TypeError):
        return [value]


@register.simple_tag
def get_progress_width(completed, total):
    """
    Calculate progress bar width percentage.
    Usage: {% get_progress_width completed total %}
    """
    try:
        if total == 0:
            return 0
        return int((completed / total) * 100)
    except (ValueError, TypeError):
        return 0