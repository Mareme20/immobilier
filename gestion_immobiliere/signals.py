# gestion_immobiliere/signals.py
from django.db.models.signals import post_save, pre_save, pre_delete
from django.dispatch import receiver
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from .models import Profile, Proprietaire, Client, Logement, DemandeLocation, ContratLocation

# NOTE: La création du Profile est gérée par le formulaire UserRegistrationForm
# car le modèle Profile nécessite les champs 'telephone' et 'adresse' qui ne sont
# pas disponibles lors de la création automatique du User via le signal post_save.
# 
# Pour les utilisateurs créés via l'admin Django, les champs devront être ajoutés
# manuellement ou via une autre méthode.

# gestion_immobiliere/signals.py
from django.db.models.signals import post_save, pre_save, pre_delete
from django.dispatch import receiver
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from .models import Profile, Proprietaire, Client, Logement, DemandeLocation, ContratLocation
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Créer automatiquement un profil quand un utilisateur est créé
    """
    try:
        if created:
            # Vérifier d'abord si un profil existe déjà
            if not hasattr(instance, 'profile'):
                Profile.objects.create(user=instance)
                logger.info(f"Profil créé pour l'utilisateur {instance.username}")
    except Exception as e:
        logger.error(f"Erreur lors de la création du profil: {str(e)}")

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Sauvegarder le profil quand l'utilisateur est modifié
    """
    try:
        if hasattr(instance, 'profile'):
            instance.profile.save()
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde du profil: {str(e)}")

@receiver(post_save, sender=Profile)
def assign_user_to_group(sender, instance, created, **kwargs):
    """
    Assigner l'utilisateur au groupe correspondant à son rôle
    """
    try:
        if instance.role:
            # Chercher ou créer le groupe correspondant au rôle
            group_name = instance.role.replace('_', ' ').title()
            group, _ = Group.objects.get_or_create(name=group_name)
            
            # Retirer l'utilisateur de tous ses groupes actuels
            instance.user.groups.clear()
            
            # Ajouter au nouveau groupe
            instance.user.groups.add(group)
            
            # Mettre à jour is_staff pour certains rôles
            if instance.role in ['gestionnaire', 'responsable_location', 'responsable_financier']:
                instance.user.is_staff = True
                instance.user.save()
            
            # Créer Proprietaire ou Client selon le rôle
            if instance.role == 'proprietaire' and not hasattr(instance, 'proprietaire'):
                Proprietaire.objects.create(profile=instance)
                logger.info(f"Propriétaire créé pour {instance.user.username}")
                
            elif instance.role == 'client' and not hasattr(instance, 'client'):
                Client.objects.create(profile=instance)
                logger.info(f"Client créé pour {instance.user.username}")
                
    except Exception as e:
        logger.error(f"Erreur dans assign_user_to_group: {str(e)}")

@receiver(pre_save, sender=DemandeLocation)
def verifier_disponibilite_logement(sender, instance, **kwargs):
    """Vérifier que le logement est disponible avant de créer une demande"""
    if instance.etat == 'attente' and not instance.logement.disponible:
        raise ValidationError(
            f"Le logement {instance.logement.reference} n'est pas disponible."
        )

@receiver(post_save, sender=DemandeLocation)
def mettre_a_jour_etat_demande(sender, instance, created, **kwargs):
    """Mettre à jour l'état du logement quand une demande est validée"""
    if instance.etat == 'validee' and created:
        instance.logement.etat = 'loue'
        instance.logement.save()

@receiver(post_save, sender=ContratLocation)
def mettre_a_jour_etat_logement_contrat(sender, instance, created, **kwargs):
    """Mettre à jour l'état du logement quand un contrat est créé"""
    if instance.etat == 'en_cours':
        instance.logement.etat = 'loue'
        instance.logement.save()
        # Mettre à jour l'état de la demande
        if instance.demande_location:
            instance.demande_location.etat = 'convertie'
            instance.demande_location.save()

@receiver(pre_save, sender=ContratLocation)
def verifier_contrat_gestion(sender, instance, **kwargs):
    """Vérifier que le contrat de gestion est actif"""
    if not instance.contrat_gestion.est_actif:
        raise ValidationError(
            "Le contrat de gestion n'est pas actif pour ce logement."
        )

@receiver(post_save, sender=ContratLocation)
def generer_paiements_mensuels(sender, instance, created, **kwargs):
    """Générer les échéances de paiement mensuelles pour un nouveau contrat"""
    if created and instance.etat == 'en_cours':
        from dateutil.relativedelta import relativedelta
        from .models import PaiementLoyer
        
        date_paiement = instance.date_debut
        mois_numero = 1
        
        while date_paiement < instance.date_fin:
            date_limite = date_paiement.replace(day=5)
            if date_limite < date_paiement:
                date_limite = date_limite + relativedelta(months=1)
            
            PaiementLoyer.objects.create(
                contrat_location=instance,
                mois=date_paiement,
                montant=instance.montant_loyer,
                date_limite=date_limite,
                statut='impaye'
            )
            
            date_paiement += relativedelta(months=1)
            mois_numero += 1

@receiver(post_save, sender=ContratLocation)
def generer_paiements_proprietaire(sender, instance, created, **kwargs):
    """Générer les échéances de paiement pour le propriétaire"""
    if created and instance.etat == 'en_cours':
        from dateutil.relativedelta import relativedelta
        from .models import PaiementProprietaire
        contrat_gestion = instance.contrat_gestion
        date_paiement = instance.date_debut
        
        while date_paiement < instance.date_fin:
            date_limite = date_paiement + timedelta(days=30)  # 30 jours après le début du mois
            
            PaiementProprietaire.objects.create(
                contrat_gestion=contrat_gestion,
                mois=date_paiement,
                montant=contrat_gestion.montant_mensuel,
                date_limite=date_limite,
                statut='impaye'
            )
            
            date_paiement += relativedelta(months=1)

@receiver(pre_delete, sender=Logement)
def supprimer_images_logement(sender, instance, **kwargs):
    """Supprimer les images associées au logement"""
    for image in instance.images.all():
        image.delete()
