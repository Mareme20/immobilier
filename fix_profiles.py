# fix_profiles.py
import os
import django
import logging

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tech_iibs.settings')
django.setup()

from django.contrib.auth.models import User, Group
from gestion_immobiliere.models import Profile, Proprietaire, Client

def fix_existing_users():
    """Corriger les utilisateurs existants sans profil"""
    print("Vérification des profils utilisateurs...")
    
    users_without_profile = []
    for user in User.objects.all():
        try:
            # Vérifier si l'utilisateur a un profil
            profile = user.profile
        except Profile.DoesNotExist:
            users_without_profile.append(user)
            # Créer le profil
            Profile.objects.create(user=user)
            print(f"✅ Profil créé pour {user.username}")
    
    # Mettre à jour les profils existants
    for profile in Profile.objects.all():
        # Assigner le groupe
        if profile.role:
            group_name = profile.role.replace('_', ' ').title()
            group, _ = Group.objects.get_or_create(name=group_name)
            profile.user.groups.clear()
            profile.user.groups.add(group)
            
            # Créer Proprietaire ou Client si nécessaire
            if profile.role == 'proprietaire' and not hasattr(profile, 'proprietaire'):
                Proprietaire.objects.create(profile=profile)
                print(f"✅ Propriétaire créé pour {profile.user.username}")
                
            elif profile.role == 'client' and not hasattr(profile, 'client'):
                Client.objects.create(profile=profile)
                print(f"✅ Client créé pour {profile.user.username}")
    
    if users_without_profile:
        print(f"\n✅ {len(users_without_profile)} profils ont été créés/corrigés.")
    else:
        print("\n✅ Tous les utilisateurs ont déjà un profil.")
    
    return users_without_profile

if __name__ == '__main__':
    fix_existing_users()