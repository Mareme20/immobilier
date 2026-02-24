from django import template

register = template.Library()

@register.filter
def display_name(user):
    """Retourne le nom d'affichage de l'utilisateur"""
    if user.first_name and user.last_name:
        return f"{user.first_name} {user.last_name}"
    return user.first_name or user.username

@register.filter
def filterby(queryset, filter_string):
    """Filtre une liste d'objets par champ:valeur"""
    try:
        field, value = filter_string.split(':')
        return [item for item in queryset if str(getattr(item, field)) == value]
    except:
        return queryset

@register.filter
def percentage(count, total):
    """Calcule le pourcentage pour les barres de progression"""
    try:
        return (float(count) / float(total)) * 100
    except (ValueError, TypeError, ZeroDivisionError):
        return 0
@register.filter
def multiply(value, arg):
    """Multiplie la valeur par l'argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def divide(value, arg):
    """Divise la valeur par l'argument"""
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0
# gestion_immobiliere/templatetags/custom_filters.py (compléter)

from django import template
from django.db.models import Count

register = template.Library()

@register.filter
def filterby(queryset, filter_string):
    """
    Filtre un queryset par champ:valeur
    """
    try:
        field, value = filter_string.split(':')
        return [item for item in queryset if getattr(item, field) == value]
    except:
        return queryset

@register.filter
def groupby(queryset, field):
    """
    Groupe un queryset par champ
    """
    result = {}
    for item in queryset:
        key = getattr(item, field)
        if key not in result:
            result[key] = []
        result[key].append(item)
    return result

@register.filter
def multiply(value, arg):
    """
    Multiplie value par arg
    """
    try:
        return float(value) * float(arg)
    except:
        return 0

@register.filter
def divisibleby(value, arg):
    """
    Divise value par arg (pour les pourcentages)
    """
    try:
        if float(arg) != 0:
            return (float(value) / float(arg)) * 100
        return 0
    except:
        return 0