# gestion_immobiliere/views/utils.py
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied
from functools import wraps

def role_required(*allowed_roles):
    """
    Décorateur pour vérifier le rôle de l'utilisateur
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(request.get_full_path())
            
            user_role = request.user.profile.role if hasattr(request.user, 'profile') else None
            
            if user_role not in allowed_roles:
                raise PermissionDenied("Vous n'avez pas la permission d'accéder à cette page.")
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def gestionnaire_required(view_func):
    """Vue réservée aux gestionnaires"""
    return role_required('gestionnaire')(view_func)

def proprietaire_required(view_func):
    """Vue réservée aux propriétaires"""
    return role_required('proprietaire')(view_func)

def client_required(view_func):
    """Vue réservée aux clients"""
    return role_required('client')(view_func)

def responsable_location_required(view_func):
    """Vue réservée aux responsables location"""
    return role_required('responsable_location')(view_func)

def responsable_financier_required(view_func):
    """Vue réservée aux responsables financiers"""
    return role_required('responsable_financier')(view_func)
# gestion_immobiliere/views/utils.py (complet)
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from functools import wraps

def role_required(*allowed_roles):
    """
    Décorateur pour vérifier le rôle de l'utilisateur
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(request.get_full_path())
            
            user_role = request.user.profile.role if hasattr(request.user, 'profile') else None
            
            if user_role not in allowed_roles:
                raise PermissionDenied("Vous n'avez pas la permission d'accéder à cette page.")
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def gestionnaire_required(view_func):
    """Vue réservée aux gestionnaires"""
    return role_required('gestionnaire')(view_func)

def proprietaire_required(view_func):
    """Vue réservée aux propriétaires"""
    return role_required('proprietaire')(view_func)

def client_required(view_func):
    """Vue réservée aux clients"""
    return role_required('client')(view_func)

def responsable_location_required(view_func):
    """Vue réservée aux responsables location"""
    return role_required('responsable_location')(view_func)

def responsable_financier_required(view_func):
    """Vue réservée aux responsables financiers"""
    return role_required('responsable_financier')(view_func)

def staff_required(view_func):
    """Vue réservée au staff (gestionnaire, responsables)"""
    return role_required('gestionnaire', 'responsable_location', 'responsable_financier')(view_func)