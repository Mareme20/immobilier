# gestion_immobiliere/models.py
from django.db import models
from django.contrib.auth.models import User, Group
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import os
from datetime import date

class Zone(models.Model):
    nom = models.CharField(max_length=100, verbose_name="Nom de la zone")
    forfait_agence = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name="Forfait agence (€)",
        default=Decimal('50.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    description = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name = "Zone"
        verbose_name_plural = "Zones"
        ordering = ['nom']
    
    def __str__(self):
        return f"{self.nom} (+{self.forfait_agence}€)"

class Profile(models.Model):
    """Modèle étendu pour tous les utilisateurs"""
    ROLE_CHOICES = [
        ('gestionnaire', 'Gestionnaire'),
        ('proprietaire', 'Propriétaire'),
        ('responsable_location', 'Responsable Location'),
        ('responsable_financier', 'Responsable Financier'),
        ('client', 'Client'),
        ('visiteur', 'Visiteur'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='visiteur')
    telephone = models.CharField(max_length=20, verbose_name="Téléphone")
    adresse = models.TextField(verbose_name="Adresse")
    date_naissance = models.DateField(null=True, blank=True, verbose_name="Date de naissance")
    date_inscription = models.DateTimeField(auto_now_add=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    
    class Meta:
        verbose_name = "Profil utilisateur"
        verbose_name_plural = "Profils utilisateurs"
    
    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_role_display()})"
    
    def get_display_name(self):
        """Retourne le nom d'affichage"""
        if self.user.first_name and self.user.last_name:
            return f"{self.user.first_name} {self.user.last_name}"
        elif self.user.first_name:
            return self.user.first_name
        else:
            return self.user.username

class Proprietaire(models.Model):
    """Extension spécifique pour les propriétaires"""
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE, primary_key=True)
    numero_fiscal = models.CharField(max_length=50, unique=True, verbose_name="Numéro fiscal")
    rib = models.CharField(max_length=50, verbose_name="RIB", blank=True, null=True)
    
    class Meta:
        verbose_name = "Propriétaire"
        verbose_name_plural = "Propriétaires"
    
    def __str__(self):
        return f"Propriétaire: {self.profile.get_display_name()}"
    
    @property
    def nom_complet(self):
        return self.profile.get_display_name()
    
    @property
    def telephone(self):
        return self.profile.telephone
    
    @property
    def adresse(self):
        return self.profile.adresse

class Logement(models.Model):
    TYPE_CHOICES = [
        ('maison', 'Maison'),
        ('appartement', 'Appartement'),
        ('studio', 'Studio'),
        ('immeuble', 'Immeuble'),
    ]
    
    ETAT_CHOICES = [
        ('disponible', 'Disponible'),
        ('loue', 'Loué'),
        ('maintenance', 'En maintenance'),
        ('archive', 'Archivé'),
    ]
    
    type_logement = models.CharField(
        max_length=20, 
        choices=TYPE_CHOICES,
        verbose_name="Type de logement"
    )
    reference = models.CharField(
        max_length=50, 
        unique=True,
        verbose_name="Référence"
    )
    adresse = models.TextField(verbose_name="Adresse complète")
    surface = models.DecimalField(
        max_digits=8, 
        decimal_places=2,
        verbose_name="Surface (m²)",
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    zone = models.ForeignKey(
        Zone, 
        on_delete=models.PROTECT,
        verbose_name="Zone",
        related_name='logements'
    )
    proprietaire = models.ForeignKey(
        Proprietaire,
        on_delete=models.CASCADE,
        verbose_name="Propriétaire",
        related_name='logements'
    )
    etat = models.CharField(
        max_length=20, 
        choices=ETAT_CHOICES, 
        default='disponible',
        verbose_name="État"
    )
    description = models.TextField(blank=True, null=True, verbose_name="Description")
    caution_fixe = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name="Caution (€)",
        default=Decimal('500.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Logement"
        verbose_name_plural = "Logements"
        ordering = ['-date_creation']
        indexes = [
            models.Index(fields=['reference']),
            models.Index(fields=['etat']),
            models.Index(fields=['type_logement']),
        ]
    
    def __str__(self):
        return f"{self.reference} - {self.get_type_logement_display()} ({self.surface}m²)"
    
    @property
    def disponible(self):
        return self.etat == 'disponible'
    
    @property
    def prix_loyer_base(self):
        """Prix de base du loyer (sans forfait agence)"""
        # Cette logique sera calculée dans ContratGestion
        return Decimal('0.00')

    @property
    def contrat_gestion(self):
        """
        Compatibilité: retourne le contrat de gestion courant.
        Priorité au contrat en cours, sinon le plus récent.
        """
        ContratGestionModel = self._meta.apps.get_model('gestion_immobiliere', 'ContratGestion')
        contrat = self.contrats_gestion.filter(etat='en_cours').order_by('-date_debut').first()
        if not contrat:
            contrat = self.contrats_gestion.order_by('-date_creation').first()
        if not contrat:
            raise ContratGestionModel.DoesNotExist
        return contrat
    
    def save(self, *args, **kwargs):
        # Générer une référence si vide
        if not self.reference:
            prefix = self.type_logement[:3].upper()
            last_ref = Logement.objects.filter(
                reference__startswith=prefix
            ).order_by('-id').first()
            
            if last_ref and last_ref.reference:
                last_num = int(last_ref.reference[3:]) if last_ref.reference[3:].isdigit() else 0
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.reference = f"{prefix}{new_num:04d}"
        
        super().save(*args, **kwargs)

class ImageLogement(models.Model):
    """Modèle pour les images multiples d'un logement"""
    logement = models.ForeignKey(
        Logement,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField(
        upload_to='logements/',
        verbose_name="Image"
    )
    ordre = models.PositiveIntegerField(default=0)
    date_ajout = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Image de logement"
        verbose_name_plural = "Images de logement"
        ordering = ['ordre', 'date_ajout']
    
    def __str__(self):
        return f"Image {self.id} - {self.logement.reference}"
    
    def delete(self, *args, **kwargs):
        """Supprimer le fichier image du stockage"""
        if self.image:
            if os.path.isfile(self.image.path):
                os.remove(self.image.path)
        super().delete(*args, **kwargs)

class ContratGestion(models.Model):
    ETAT_CHOICES = [
        ('en_cours', 'En cours'),
        ('annule', 'Annulé'),
        ('termine', 'Terminé'),
        ('en_attente', 'En attente de signature'),
    ]
    
    logement = models.ForeignKey(
        Logement,
        on_delete=models.CASCADE,
        verbose_name="Logement",
        related_name='contrats_gestion'
    )
    proprietaire = models.ForeignKey(
        Proprietaire,
        on_delete=models.CASCADE,
        verbose_name="Propriétaire",
        related_name='contrats_gestion'
    )
    date_debut = models.DateField(verbose_name="Date de début")
    date_fin = models.DateField(verbose_name="Date de fin")
    montant_mensuel = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Montant mensuel propriétaire (€)",
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    etat = models.CharField(
        max_length=20,
        choices=ETAT_CHOICES,
        default='en_attente',
        verbose_name="État du contrat"
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_signature = models.DateField(null=True, blank=True, verbose_name="Date de signature")
    fichier_contrat = models.FileField(
        upload_to='contrats_gestion/',
        null=True,
        blank=True,
        verbose_name="Contrat signé"
    )
    remarques = models.TextField(blank=True, null=True, verbose_name="Remarques")
    
    class Meta:
        verbose_name = "Contrat de gestion"
        verbose_name_plural = "Contrats de gestion"
        ordering = ['-date_creation']
        constraints = [
            models.UniqueConstraint(
                fields=['logement'],
                condition=models.Q(etat='en_cours'),
                name='unique_contrat_gestion_en_cours_par_logement'
            ),
        ]
        indexes = [
            models.Index(fields=['etat']),
            models.Index(fields=['date_debut', 'date_fin']),
        ]
    
    def __str__(self):
        return f"Contrat Gestion {self.id} - {self.logement.reference}"
    
    @property
    def prix_loyer_total(self):
        """Prix total du loyer (montant propriétaire + forfait zone + caution fixe)"""
        return (
            self.montant_mensuel
            + self.logement.zone.forfait_agence
            + self.logement.caution_fixe
        )
    
    @property
    def est_actif(self):
        """Vérifie si le contrat est actuellement actif"""
        today = date.today()
        return (
            self.etat == 'en_cours' and 
            self.date_debut <= today <= self.date_fin
        )
    
    @property
    def jours_restants(self):
        """Nombre de jours restants avant la fin du contrat"""
        if self.est_actif:
            return (self.date_fin - date.today()).days
        return 0

class Client(models.Model):
    """Extension spécifique pour les clients (locataires)"""
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE, primary_key=True)
    profession = models.CharField(max_length=100, blank=True, null=True, verbose_name="Profession")
    employeur = models.CharField(max_length=100, blank=True, null=True, verbose_name="Employeur")
    revenu_mensuel = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Revenu mensuel (€)"
    )
    
    class Meta:
        verbose_name = "Client"
        verbose_name_plural = "Clients"
    
    def __str__(self):
        return f"Client: {self.profile.get_display_name()}"
    
    @property
    def nom_complet(self):
        return self.profile.get_display_name()
    
    @property
    def telephone(self):
        return self.profile.telephone
    
    @property
    def adresse(self):
        return self.profile.adresse

class DemandeLocation(models.Model):
    ETAT_CHOICES = [
        ('attente', 'En attente'),
        ('validee', 'Validée'),
        ('rejetee', 'Rejetée'),
        ('annulee', 'Annulée'),
        ('convertie', 'Convertie en contrat'),
    ]
    
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        verbose_name="Client",
        related_name='demandes_location'
    )
    logement = models.ForeignKey(
        Logement,
        on_delete=models.CASCADE,
        verbose_name="Logement",
        related_name='demandes_location'
    )
    date_demande = models.DateTimeField(auto_now_add=True, verbose_name="Date de la demande")
    date_debut_souhaitee = models.DateField(verbose_name="Date de début souhaitée")
    duree_souhaitee = models.IntegerField(
        verbose_name="Durée souhaitée (mois)",
        validators=[MinValueValidator(1), MaxValueValidator(60)]
    )
    etat = models.CharField(
        max_length=20,
        choices=ETAT_CHOICES,
        default='attente',
        verbose_name="État de la demande"
    )
    date_validation = models.DateTimeField(null=True, blank=True, verbose_name="Date de validation")
    valide_par = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='demandes_validees',
        verbose_name="Validé par"
    )
    motif_rejet = models.TextField(blank=True, null=True, verbose_name="Motif de rejet")
    notes = models.TextField(blank=True, null=True, verbose_name="Notes")
    
    class Meta:
        verbose_name = "Demande de location"
        verbose_name_plural = "Demandes de location"
        ordering = ['-date_demande']
        indexes = [
            models.Index(fields=['etat']),
            models.Index(fields=['date_demande']),
        ]
    
    def __str__(self):
        return f"Demande {self.id} - {self.client.nom_complet}"
    
    @property
    def date_fin_souhaitee(self):
        """Calcule la date de fin souhaitée"""
        from dateutil.relativedelta import relativedelta
        return self.date_debut_souhaitee + relativedelta(months=self.duree_souhaitee)
    
    @property
    def peut_etre_validee(self):
        """Vérifie si la demande peut être validée"""
        return (
            self.etat == 'attente' and 
            self.logement.etat == 'disponible'
        )

class ContratLocation(models.Model):
    ETAT_CHOICES = [
        ('en_cours', 'En cours'),
        ('termine', 'Terminé'),
        ('resilie', 'Résilié'),
        ('en_attente', 'En attente de signature'),
    ]
    
    demande_location = models.OneToOneField(
        DemandeLocation,
        on_delete=models.CASCADE,
        verbose_name="Demande de location",
        related_name='contrat_location'
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        verbose_name="Client",
        related_name='contrats_location'
    )
    logement = models.ForeignKey(
        Logement,
        on_delete=models.PROTECT,
        verbose_name="Logement",
        related_name='contrats_location'
    )
    contrat_gestion = models.ForeignKey(
        ContratGestion,
        on_delete=models.PROTECT,
        verbose_name="Contrat de gestion",
        related_name='contrats_location'
    )
    date_debut = models.DateField(verbose_name="Date de début")
    date_fin = models.DateField(verbose_name="Date de fin")
    montant_loyer = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Montant du loyer (FCFA)",
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    caution_versee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Caution versée (FCFA))",
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    etat = models.CharField(
        max_length=20,
        choices=ETAT_CHOICES,
        default='en_attente',
        verbose_name="État du contrat"
    )
    date_signature = models.DateTimeField(auto_now_add=True, verbose_name="Date de signature")
    contrat_signe = models.FileField(
        upload_to='contrats_location/',
        blank=True,
        null=True,
        verbose_name="Contrat signé"
    )
    bulletin_salaire = models.FileField(
        upload_to='documents_clients/',
        blank=True,
        null=True,
        verbose_name="Bulletin de salaire"
    )
    casier_judiciaire = models.FileField(
        upload_to='documents_clients/',
        blank=True,
        null=True,
        verbose_name="Casier judiciaire"
    )
    carte_identite = models.FileField(
        upload_to='documents_clients/',
        blank=True,
        null=True,
        verbose_name="Carte d'identité"
    )
    garant = models.CharField(max_length=200, blank=True, null=True, verbose_name="Nom du garant")
    telephone_garant = models.CharField(max_length=20, blank=True, null=True, verbose_name="Téléphone du garant")
    remarques = models.TextField(blank=True, null=True, verbose_name="Remarques")
    
    class Meta:
        verbose_name = "Contrat de location"
        verbose_name_plural = "Contrats de location"
        ordering = ['-date_signature']
        constraints = [
            models.UniqueConstraint(
                fields=['logement'],
                condition=models.Q(etat='en_cours'),
                name='unique_logement_contrat_location_en_cours'
            ),
        ]
        indexes = [
            models.Index(fields=['etat']),
            models.Index(fields=['date_debut', 'date_fin']),
        ]
    
    def __str__(self):
        return f"Contrat Location {self.id} - {self.client.nom_complet}"

    def clean(self):
        super().clean()
        if self.etat == 'en_cours':
            has_other_active = ContratLocation.objects.filter(
                logement=self.logement,
                etat='en_cours'
            ).exclude(pk=self.pk).exists()
            if has_other_active:
                from django.core.exceptions import ValidationError
                raise ValidationError(
                    "Ce logement a déjà un contrat de location en cours."
                )

        if self.etat in ['en_cours', 'termine', 'resilie']:
            missing_docs = []
            if not self.contrat_signe:
                missing_docs.append("contrat signé")
            if not self.bulletin_salaire:
                missing_docs.append("bulletin de salaire")
            if not self.casier_judiciaire:
                missing_docs.append("casier judiciaire")

            if missing_docs:
                from django.core.exceptions import ValidationError
                raise ValidationError(
                    f"Pièces obligatoires manquantes: {', '.join(missing_docs)}."
                )
    
    @property
    def est_actif(self):
        """Vérifie si le contrat est actuellement actif"""
        today = date.today()
        return (
            self.etat == 'en_cours' and 
            self.date_debut <= today <= self.date_fin
        )
    
    @property
    def mois_restants(self):
        """Nombre de mois restants avant la fin du contrat"""
        if self.est_actif:
            from dateutil.relativedelta import relativedelta
            today = date.today()
            months = 0
            temp_date = today
            while temp_date < self.date_fin:
                temp_date += relativedelta(months=1)
                months += 1
            return months
        return 0
    
    @property
    def total_paiements(self):
        """Total des paiements effectués"""
        return self.paiements.filter(statut='paye').aggregate(
            total=models.Sum('montant')
        )['total'] or Decimal('0.00')
    
    @property
    def montant_restant(self):
        """Montant total restant à payer"""
        if self.est_actif:
            from dateutil.relativedelta import relativedelta
            today = date.today()
            
            # Calculer le nombre de mois depuis le début
            months_passed = 0
            temp_date = self.date_debut
            while temp_date <= today and temp_date <= self.date_fin:
                if temp_date.day <= today.day:
                    months_passed += 1
                temp_date += relativedelta(months=1)
            
            total_a_payer = months_passed * self.montant_loyer
            return total_a_payer - self.total_paiements
        
        return Decimal('0.00')

class PaiementLoyer(models.Model):
    STATUT_CHOICES = [
        ('paye', 'Payé'),
        ('en_retard', 'En retard'),
        ('impaye', 'Impayé'),
        ('partiel', 'Paiement partiel'),
    ]
    
    MODE_PAIEMENT_CHOICES = [
        ('especes', 'Espèces'),
        ('cheque', 'Chèque'),
        ('virement', 'Virement'),
        ('mobile', 'Mobile Money'),
        ('carte', 'Carte bancaire'),
    ]
    
    contrat_location = models.ForeignKey(
        ContratLocation,
        on_delete=models.CASCADE,
        verbose_name="Contrat de location",
        related_name='paiements'
    )
    mois = models.DateField(verbose_name="Mois concerné")
    montant = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Montant (€)",
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    date_paiement = models.DateTimeField(null=True, blank=True, verbose_name="Date de paiement")
    date_limite = models.DateField(verbose_name="Date limite de paiement")
    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default='impaye',
        verbose_name="Statut"
    )
    mode_paiement = models.CharField(
        max_length=20,
        choices=MODE_PAIEMENT_CHOICES,
        null=True,
        blank=True,
        verbose_name="Mode de paiement"
    )
    reference_paiement = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Référence du paiement"
    )
    encaisse_par = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Encaisse par"
    )
    notes = models.TextField(blank=True, null=True, verbose_name="Notes")
    
    class Meta:
        verbose_name = "Paiement de loyer"
        verbose_name_plural = "Paiements de loyer"
        ordering = ['-mois']
        unique_together = ['contrat_location', 'mois']
        indexes = [
            models.Index(fields=['statut']),
            models.Index(fields=['date_limite']),
        ]
    
    def __str__(self):
        return f"Paiement {self.mois.strftime('%B %Y')} - {self.contrat_location.client.nom_complet}"
    
    @property
    def est_en_retard(self):
        """Vérifie si le paiement est en retard"""
        return self.statut == 'en_retard'
    
    @property
    def jours_retard(self):
        """Nombre de jours de retard"""
        if self.est_en_retard:
            return max(0, (date.today() - self.date_limite).days)
        return 0

class PaiementProprietaire(models.Model):
    """Paiements effectués aux propriétaires"""
    contrat_gestion = models.ForeignKey(
        ContratGestion,
        on_delete=models.CASCADE,
        verbose_name="Contrat de gestion",
        related_name='paiements_proprietaire'
    )
    mois = models.DateField(verbose_name="Mois concerné")
    montant = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Montant (€)",
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    date_paiement = models.DateTimeField(null=True, blank=True, verbose_name="Date de paiement")
    date_limite = models.DateField(verbose_name="Date limite de paiement")
    statut = models.CharField(
        max_length=20,
        choices=PaiementLoyer.STATUT_CHOICES,
        default='impaye'
    )
    mode_paiement = models.CharField(
        max_length=20,
        choices=PaiementLoyer.MODE_PAIEMENT_CHOICES,
        null=True,
        blank=True
    )
    reference_paiement = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name = "Paiement propriétaire"
        verbose_name_plural = "Paiements propriétaires"
        ordering = ['-mois']
        unique_together = ['contrat_gestion', 'mois']
    
    def __str__(self):
        return f"Paiement Proprio {self.mois.strftime('%B %Y')} - {self.contrat_gestion.proprietaire.nom_complet}"
    







    # gestion_immobiliere/models.py (ajouter à la fin)

class RendezVous(models.Model):
    """Modèle pour les rendez-vous de visite"""
    STATUT_CHOICES = [
        ('planifie', 'Planifié'),
        ('confirme', 'Confirmé'),
        ('effectue', 'Effectué'),
        ('annule', 'Annulé'),
        ('reporte', 'Reporté'),
    ]
    
    demande_location = models.OneToOneField(
        DemandeLocation,
        on_delete=models.CASCADE,
        verbose_name="Demande de location",
        related_name='rendez_vous'
    )
    date_rendez_vous = models.DateTimeField(verbose_name="Date et heure du rendez-vous")
    duree_estimee = models.IntegerField(
        verbose_name="Durée estimée (minutes)",
        default=60
    )
    lieu = models.TextField(verbose_name="Lieu de rendez-vous")
    contact_agence = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Contact agence",
        related_name='rendez_vous_animes'
    )
    contact_client = models.CharField(
        max_length=20,
        verbose_name="Téléphone client"
    )
    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default='planifie',
        verbose_name="Statut"
    )
    notes = models.TextField(blank=True, null=True, verbose_name="Notes")
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Rendez-vous"
        verbose_name_plural = "Rendez-vous"
        ordering = ['date_rendez_vous']
    
    def __str__(self):
        return f"Rendez-vous {self.demande_location.id} - {self.date_rendez_vous.strftime('%d/%m/%Y %H:%M')}"
    
    @property
    def est_passe(self):
        """Vérifie si le rendez-vous est passé"""
        from django.utils import timezone
        return self.date_rendez_vous < timezone.now()
    
    @property
    def peut_etre_annule(self):
        """Vérifie si le rendez-vous peut être annulé"""
        from django.utils import timezone
        from datetime import timedelta
        return (
            self.statut in ['planifie', 'confirme'] and
            self.date_rendez_vous > timezone.now() + timedelta(hours=2)
        )
