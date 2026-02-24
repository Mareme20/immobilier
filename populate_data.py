import os
import django
import random
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from django.db import transaction

# Assurez-vous que Django est configuré avant les imports de modèles
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tech_iibs.settings')
django.setup()

from django.contrib.auth.models import User, Group
from gestion_immobiliere.models import (
    Profile, Zone, Proprietaire, Logement, 
    ContratGestion, Client, DemandeLocation, 
    ContratLocation, PaiementLoyer
)

# --- Fonctions utilitaires ---

def assign_user_to_group(user, group_name):
    """Ajoute un utilisateur à un groupe Django spécifique."""
    try:
        group = Group.objects.get(name=group_name)
        user.groups.add(group)
        # print(f"Ajouté {user.username} au groupe {group_name}")
    except Group.DoesNotExist:
        print(f"Le groupe '{group_name}' n'existe pas. Créez les groupes dans l'admin d'abord.")

# --- Fonctions de création de données ---

def create_zones():
    # Zones basées sur Dakar et ses environs
    zones = [
        ('Plateau', 60.00, 'Centre-ville de Dakar, quartier administratif'),
        ('Almadies', 100.00, 'Quartier résidentiel haut standing, bord de mer'),
        ('Ngor', 80.00, 'Quartier touristique et résidentiel'),
        ('Mermoz', 55.00, 'Quartier résidentiel central'),
        ('Guédiawaye', 25.00, 'Banlieue de Dakar en plein développement'),
        ('Diamniadio', 40.00, 'Nouvelle ville, pôle de développement'),
        ('Saly', 70.00, 'Station balnéaire, villas de vacances'),
    ]
    
    for nom, forfait, description in zones:
        Zone.objects.get_or_create(
            nom=nom,
            defaults={'forfait_agence': forfait, 'description': description}
        )
    print("Zones sénégalaises créées")

def create_proprietaires():
    # Noms de famille courants au Sénégal
    noms_senegal = [
        ('Diop', 'Abdoulaye', '776123456', 'Villa 45, Sacré-Cœur 3'),
        ('Ndiaye', 'Fatoumata', '785234567', 'Immeuble Horizon, Plateau'),
        ('Fall', 'Moussa', '763345678', 'Cité Keur Gorgui'),
        ('Sow', 'Marième', '704567890', 'Quartier Almadies Extension'),
        ('Gueye', 'Ibrahima', '775678901', 'Cité Damel, Patte d\'Oie'),
    ]
    
    for nom, prenom, tel, adresse in noms_senegal:
        username = f"{prenom.lower()}.{nom.lower()}"
        
        # Utilisation de transaction.atomic pour garantir la cohérence
        with transaction.atomic():
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'first_name': prenom, 'last_name': nom, 'email': f"{username}@tech-iibs.sn"}
            )
            if created:
                user.set_password('password123')
                user.save()
                assign_user_to_group(user, 'Proprietaire') # Assigner au groupe

            profile, _ = Profile.objects.get_or_create(
                user=user,
                defaults={
                    'role': 'proprietaire',
                    'telephone': tel,
                    'adresse': adresse,
                    'date_naissance': date(1970 + random.randint(10, 40), 1, 1)
                }
            )
            
            # Utilisation de update_or_create pour éviter les conflits de clé étrangère
            Proprietaire.objects.update_or_create(
                profile=profile,
                defaults={
                    'numero_fiscal': f'SN-NINEA-{random.randint(1000000, 9999999)}',
                    'rib': f'SN079{random.randint(10**15, 10**16-1)}'
                }
            )
    
    print("Propriétaires sénégalais créés/mis à jour")

def create_clients():
    clients_data = [
        ('Thiam', 'Oumar', '778123456', 'Consultant IT'),
        ('Ba', 'Awa', '784234567', 'Agent BCEAO'),
        ('Diedhiou', 'Modou', '762345678', 'Commerçant Sandaga'),
        ('Kane', 'Seynabou', '709567890', 'Avocate'),
        ('Seck', 'Cheikh', '771678901', 'Directeur Marketing'),
    ]
    
    for nom, prenom, tel, profession in clients_data:
        username = f"client.{prenom.lower()}.{nom.lower()}"
        
        with transaction.atomic():
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'first_name': prenom, 'last_name': nom, 'email': f"{username}@gmail.com"}
            )
            if created:
                user.set_password('password123')
                user.save()
                assign_user_to_group(user, 'Client') # Assigner au groupe

            profile, _ = Profile.objects.get_or_create(
                user=user,
                defaults={'role': 'client', 'telephone': tel, 'adresse': 'Dakar'}
            )
            
            Client.objects.update_or_create(
                profile=profile,
                defaults={
                    'profession': profession,
                    'employeur': f'Société {random.choice(["Orange SN", "Free", "Port Autonome", "Banque Habitat"])}',
                    'revenu_mensuel': random.randint(300000, 1500000) # En FCFA
                }
            )
    
    print("Clients sénégalais créés/mis à jour")

def create_logements():
    zones = list(Zone.objects.all())
    proprietaires = list(Proprietaire.objects.all())
    
    logements_data = [
        ('DKR-VIL-001', 'maison', 'Villa F5 avec piscine aux Almadies', 300.00, 2000000.00),
        ('DKR-APP-002', 'appartement', 'Appartement standing au Plateau', 120.00, 800000.00),
        ('DKR-STU-003', 'studio', 'Chambre meublée Liberté 6', 35.00, 150000.00),
        ('DKR-IMM-004', 'immeuble', 'Immeuble R+4 à Grand Yoff', 600.00, 5000000.00),
        ('DKR-VIL-005', 'maison', 'Villa basse à Diamniadio', 150.00, 400000.00),
        ('DKR-APP-006', 'appartement', 'Appartement F4 à Mermoz', 140.00, 650000.00),
    ]
    
    for ref, type_log, desc, surface, caution in logements_data:
        # Utilisation de update_or_create pour la robustesse
        Logement.objects.update_or_create(
            reference=ref,
            defaults={
                'type_logement': type_log,
                'adresse': f'Lotissement {random.randint(10, 500)}, {random.choice(["Amitié", "Liberte 6", "Yoff"])}',
                'surface': surface,
                'zone': random.choice(zones),
                'proprietaire': random.choice(proprietaires),
                'description': desc,
                'caution_fixe': caution,
                'etat': random.choice(['disponible', 'disponible', 'disponible', 'loue'])
            }
        )
    
    print("Logements créés/mis à jour")


# --- Exécution ---

if __name__ == '__main__':
    print("Début du peuplement des données (Sénégal 2026)...")
    
    # Assurez-vous d'abord que les groupes existent via l'admin Django 
    # ou créez-les ici si nécessaire.
    
    create_zones()
    create_proprietaires()
    create_clients()
    create_logements()
    # Ajoutez ici les appels pour ContratGestion, DemandeLocation, etc.
    
    print("Terminé !")
