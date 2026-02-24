# gestion_immobiliere/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import (
    Profile, Zone, Proprietaire, Logement, ImageLogement,
    ContratGestion, Client, DemandeLocation, ContratLocation,
    PaiementLoyer, PaiementProprietaire
)

class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'
    fields = ('role', 'telephone', 'adresse', 'date_naissance', 'avatar')
    readonly_fields = ('date_inscription',)

class CustomUserAdmin(UserAdmin):
    inlines = (ProfileInline, )
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_role', 'is_staff', 'is_active')
    list_select_related = ('profile', )
    list_filter = ('profile__role', 'is_staff', 'is_active')
    
    def get_role(self, instance):
        return instance.profile.get_role_display()
    get_role.short_description = 'Rôle'
    
    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super(CustomUserAdmin, self).get_inline_instances(request, obj)

# Désenregistrer l'admin par défaut
admin.site.unregister(User)

# Réenregistrer avec l'admin personnalisé
admin.site.register(User, CustomUserAdmin)

class ImageLogementInline(admin.TabularInline):
    model = ImageLogement
    extra = 1
    fields = ('image', 'ordre', 'date_ajout')
    readonly_fields = ('date_ajout',)

@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ('nom', 'forfait_agence', 'nombre_logements', 'description_short')
    search_fields = ('nom', 'description')
    ordering = ('nom',)
    
    def nombre_logements(self, obj):
        return obj.logements.count()
    nombre_logements.short_description = 'Nb. logements'
    
    def description_short(self, obj):
        return obj.description[:50] + '...' if obj.description else ''
    description_short.short_description = 'Description'

@admin.register(Proprietaire)
class ProprietaireAdmin(admin.ModelAdmin):
    list_display = ('get_nom', 'numero_fiscal', 'telephone', 'nombre_logements', 'date_inscription')
    search_fields = ('profile__user__first_name', 'profile__user__last_name', 'numero_fiscal')
    list_filter = ('profile__user__is_active',)
    readonly_fields = ('date_inscription',)
    
    def get_nom(self, obj):
        return obj.nom_complet
    get_nom.short_description = 'Nom'
    
    def telephone(self, obj):
        return obj.telephone
    telephone.short_description = 'Téléphone'
    
    def date_inscription(self, obj):
        return obj.profile.date_inscription
    date_inscription.short_description = 'Inscription'
    
    def nombre_logements(self, obj):
        return obj.logements.count()
    nombre_logements.short_description = 'Nb. logements'

@admin.register(Logement)
class LogementAdmin(admin.ModelAdmin):
    list_display = ('reference', 'type_logement', 'proprietaire', 'zone', 'surface', 'etat', 'date_creation')
    list_filter = ('type_logement', 'etat', 'zone', 'proprietaire')
    search_fields = ('reference', 'adresse', 'description')
    readonly_fields = ('date_creation', 'date_modification')
    inlines = [ImageLogementInline]
    fieldsets = (
        ('Informations générales', {
            'fields': ('reference', 'type_logement', 'adresse', 'surface', 'description')
        }),
        ('Localisation et propriété', {
            'fields': ('zone', 'proprietaire', 'caution_fixe')
        }),
        ('État et dates', {
            'fields': ('etat', 'date_creation', 'date_modification')
        }),
    )

@admin.register(ContratGestion)
class ContratGestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'logement', 'proprietaire', 'date_debut', 'date_fin', 'montant_mensuel', 'prix_loyer_total', 'etat', 'jours_restants')
    list_filter = ('etat', 'date_debut', 'date_fin')
    search_fields = ('logement__reference', 'proprietaire__profile__user__first_name', 'proprietaire__profile__user__last_name')
    readonly_fields = ('date_creation', 'prix_loyer_total')
    fieldsets = (
        ('Informations du contrat', {
            'fields': ('logement', 'proprietaire', 'date_debut', 'date_fin', 'montant_mensuel')
        }),
        ('État et documents', {
            'fields': ('etat', 'date_signature', 'fichier_contrat', 'remarques')
        }),
        ('Informations calculées', {
            'fields': ('prix_loyer_total', 'date_creation')
        }),
    )
    
    def prix_loyer_total(self, obj):
        return f"{obj.prix_loyer_total} €"
    prix_loyer_total.short_description = 'Prix loyer total'

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('get_nom', 'telephone', 'profession', 'employeur', 'revenu_mensuel', 'date_inscription')
    search_fields = ('profile__user__first_name', 'profile__user__last_name', 'profession', 'employeur')
    list_filter = ('profile__user__is_active',)
    
    def get_nom(self, obj):
        return obj.nom_complet
    get_nom.short_description = 'Nom'
    
    def telephone(self, obj):
        return obj.telephone
    telephone.short_description = 'Téléphone'
    
    def date_inscription(self, obj):
        return obj.profile.date_inscription
    date_inscription.short_description = 'Inscription'

@admin.register(DemandeLocation)
class DemandeLocationAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'logement', 'date_demande', 'date_debut_souhaitee', 'duree_souhaitee', 'etat')
    list_filter = ('etat', 'date_demande', 'logement__type_logement')
    search_fields = ('client__profile__user__first_name', 'client__profile__user__last_name', 'logement__reference')
    readonly_fields = ('date_demande', 'date_validation')
    fieldsets = (
        ('Informations de la demande', {
            'fields': ('client', 'logement', 'date_debut_souhaitee', 'duree_souhaitee', 'notes')
        }),
        ('État et validation', {
            'fields': ('etat', 'valide_par', 'date_validation', 'motif_rejet')
        }),
        ('Dates', {
            'fields': ('date_demande',)
        }),
    )

@admin.register(ContratLocation)
class ContratLocationAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'logement', 'date_debut', 'date_fin', 'montant_loyer', 'etat', 'est_actif')
    list_filter = ('etat', 'date_debut', 'date_fin')
    search_fields = ('client__profile__user__first_name', 'client__profile__user__last_name', 'logement__reference')
    readonly_fields = ('date_signature', 'est_actif', 'mois_restants')
    fieldsets = (
        ('Informations du contrat', {
            'fields': ('demande_location', 'client', 'logement', 'contrat_gestion')
        }),
        ('Détails du contrat', {
            'fields': ('date_debut', 'date_fin', 'montant_loyer', 'caution_versee')
        }),
        ('Documents', {
            'fields': ('contrat_signe', 'bulletin_salaire', 'casier_judiciaire', 'carte_identite')
        }),
        ('Garant', {
            'fields': ('garant', 'telephone_garant')
        }),
        ('État et remarques', {
            'fields': ('etat', 'remarques')
        }),
        ('Informations calculées', {
            'fields': ('est_actif', 'mois_restants', 'date_signature')
        }),
    )

@admin.register(PaiementLoyer)
class PaiementLoyerAdmin(admin.ModelAdmin):
    list_display = ('id', 'contrat_location', 'mois', 'montant', 'date_limite', 'statut', 'date_paiement')
    list_filter = ('statut', 'mode_paiement', 'mois')
    search_fields = ('contrat_location__client__profile__user__first_name', 
                    'contrat_location__client__profile__user__last_name',
                    'reference_paiement')
    readonly_fields = ('est_en_retard', 'jours_retard')
    fieldsets = (
        ('Informations du paiement', {
            'fields': ('contrat_location', 'mois', 'montant', 'date_limite')
        }),
        ('Paiement effectué', {
            'fields': ('date_paiement', 'mode_paiement', 'reference_paiement', 'encaisse_par')
        }),
        ('Statut et notes', {
            'fields': ('statut', 'notes')
        }),
        ('Informations calculées', {
            'fields': ('est_en_retard', 'jours_retard')
        }),
    )

@admin.register(PaiementProprietaire)
class PaiementProprietaireAdmin(admin.ModelAdmin):
    list_display = ('id', 'contrat_gestion', 'mois', 'montant', 'date_limite', 'statut', 'date_paiement')
    list_filter = ('statut', 'mode_paiement', 'mois')
    search_fields = ('contrat_gestion__proprietaire__profile__user__first_name',
                    'contrat_gestion__proprietaire__profile__user__last_name',
                    'reference_paiement')

# Enregistrer ImageLogement (optionnel, géré via inline)
admin.site.register(ImageLogement)