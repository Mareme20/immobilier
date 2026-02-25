from django import template

register = template.Library()


@register.filter
def display_name(user):
    """Retourne le nom d'affichage de l'utilisateur."""
    if getattr(user, "first_name", None) and getattr(user, "last_name", None):
        return f"{user.first_name} {user.last_name}"
    return getattr(user, "first_name", None) or getattr(user, "username", "")


@register.filter
def filterby(queryset, filter_string):
    """Filtre une liste d'objets par champ:valeur."""
    try:
        field, value = filter_string.split(":", 1)
        return [item for item in queryset if str(getattr(item, field, "")) == value]
    except Exception:
        return queryset


@register.filter
def groupby(queryset, field):
    """Groupe une liste d'objets par champ."""
    result = {}
    for item in queryset:
        key = getattr(item, field, None)
        result.setdefault(key, []).append(item)
    return result


@register.filter
def percentage(count, total):
    """Calcule un pourcentage."""
    try:
        return (float(count) / float(total)) * 100
    except (ValueError, TypeError, ZeroDivisionError):
        return 0


@register.filter
def multiply(value, arg):
    """Multiplie value par arg."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def divide(value, arg):
    """Divise value par arg."""
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0


@register.filter
def divisibleby(value, arg):
    """Divise value par arg (helper historique du projet)."""
    return divide(value, arg)
