# gestion_immobiliere/signals.py
from django.db.models.signals import post_save, pre_save, pre_delete
from django.dispatch import receiver
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
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
                # Valeurs minimales pour éviter les erreurs sur les champs requis.
                Profile.objects.create(user=instance, telephone='', adresse='')
                logger.info(f"Profil créé pour l'utilisateur {instance.username}")
    except Exception as e:
        logger.error(f"Erreur lors de la création du profil: {str(e)}")

@receiver(post_save, sender=User)
def ensure_user_profile(sender, instance, created, **kwargs):
    """S'assurer qu'un profil existe pour l'utilisateur."""
    if created:
        return
    if not hasattr(instance, 'profile'):
        Profile.objects.create(user=instance, telephone='', adresse='')

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
            
            # Mettre à jour is_staff sans relancer le signal post_save(User)
            should_be_staff = instance.role in ['gestionnaire', 'responsable_location', 'responsable_financier']
            if instance.user.is_staff != should_be_staff:
                User.objects.filter(pk=instance.user.pk).update(is_staff=should_be_staff)
                instance.user.is_staff = should_be_staff
            
            # Pour 'proprietaire', la création se fait via formulaire dédié
            # car 'numero_fiscal' est requis.
            if instance.role == 'client' and not hasattr(instance, 'client'):
                Client.objects.create(profile=instance)
                logger.info(f"Client créé pour {instance.user.username}")
                
    except Exception as e:
        logger.error(f"Erreur dans assign_user_to_group: {str(e)}")

@receiver(pre_save, sender=DemandeLocation)
def verifier_disponibilite_logement(sender, instance, **kwargs):
    """Vérifier que le logement est disponible avant de créer une demande"""
    if instance.pk is None and instance.etat == 'attente' and not instance.logement.disponible:
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
    if instance.etat == 'en_cours' and not instance.contrat_gestion.est_actif:
        raise ValidationError(
            "Le contrat de gestion n'est pas actif pour ce logement."
        )

@receiver(post_save, sender=ContratLocation)
def generer_paiements_mensuels(sender, instance, created, **kwargs):
    """Générer les échéances de paiement mensuelles pour un nouveau contrat"""
    if instance.etat in ['en_attente', 'en_cours']:
        from dateutil.relativedelta import relativedelta
        from .models import PaiementLoyer
        
        date_paiement = instance.date_debut
        mois_numero = 1
        
        while date_paiement < instance.date_fin:
            date_limite = date_paiement.replace(day=5)
            if date_limite < date_paiement:
                date_limite = date_limite + relativedelta(months=1)
            
            PaiementLoyer.objects.get_or_create(
                contrat_location=instance,
                mois=date_paiement,
                defaults={
                    'montant': instance.montant_loyer,
                    'date_limite': date_limite,
                    'statut': 'impaye',
                }
            )
            
            date_paiement += relativedelta(months=1)
            mois_numero += 1

@receiver(post_save, sender=ContratLocation)
def generer_paiements_proprietaire(sender, instance, created, **kwargs):
    """Générer les échéances de paiement pour le propriétaire"""
    if instance.etat in ['en_attente', 'en_cours']:
        from dateutil.relativedelta import relativedelta
        from .models import PaiementProprietaire
        contrat_gestion = instance.contrat_gestion
        date_paiement = instance.date_debut
        
        while date_paiement < instance.date_fin:
            date_limite = date_paiement + timedelta(days=30)  # 30 jours après le début du mois
            
            PaiementProprietaire.objects.get_or_create(
                contrat_gestion=contrat_gestion,
                mois=date_paiement,
                defaults={
                    'montant': contrat_gestion.montant_mensuel,
                    'date_limite': date_limite,
                    'statut': 'impaye',
                }
            )
            
            date_paiement += relativedelta(months=1)

@receiver(pre_delete, sender=Logement)
def supprimer_images_logement(sender, instance, **kwargs):
    """Supprimer les images associées au logement"""
    for image in instance.images.all():
        image.delete()
