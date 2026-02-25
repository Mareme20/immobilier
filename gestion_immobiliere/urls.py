# gestion_immobiliere/urls.py
from django.urls import path
from . import views
from .views import CustomPasswordChangeView
urlpatterns = [
    # Pages publiques
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Profil
    path('profil/', views.mon_profil, name='mon_profil'),
    path('profil/changer-mot-de-passe/', 
         CustomPasswordChangeView.as_view(), 
         name='change_password'),
    
    # Vues de gestion
    path('gestion/logements/', views.gerer_logements, name='gerer_logements'),
    path('gestion/contrats-gestion/', views.gerer_contrats_gestion, name='gerer_contrats_gestion'),
    path('proprietaire/mes-biens/', views.mes_biens, name='mes_biens'),
    path('responsable-location/traiter-demandes/', views.traiter_demandes, name='traiter_demandes'),

    # Vues de gestion (gestionnaire)
# CRUD Logements
    path('gestion/logements/ajouter/', views.ajouter_logement, name='ajouter_logement'),
    path('gestion/logements/<int:pk>/modifier/', views.modifier_logement, name='modifier_logement'),
    path('gestion/logements/<int:pk>/supprimer/', views.supprimer_logement, name='supprimer_logement'),
    path('gestion/logements/<int:pk>/archiver/', views.archiver_logement, name='archiver_logement'),
    
    # CRUD Contrats de gestion
    path('gestion/contrats-gestion/ajouter/', views.ajouter_contrat_gestion, name='ajouter_contrat_gestion'),
    path('gestion/contrats-gestion/<int:pk>/modifier/', views.modifier_contrat_gestion, name='modifier_contrat_gestion'),
    path('gestion/contrats-gestion/<int:pk>/supprimer/', views.supprimer_contrat_gestion, name='supprimer_contrat_gestion'),
    
    # CRUD Zones
    path('gestion/zones/', views.gerer_zones, name='gerer_zones'),
    path('gestion/zones/<int:pk>/modifier/', views.modifier_zone, name='modifier_zone'),
    path('gestion/zones/<int:pk>/supprimer/', views.supprimer_zone, name='supprimer_zone'),    # Tableau de bord (protégé)


    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/gestionnaire/', views.gestionnaire_dashboard, name='gestionnaire_dashboard'),
    path('dashboard/proprietaire/', views.proprietaire_dashboard, name='proprietaire_dashboard'),
    path('dashboard/responsable-location/', views.responsable_location_dashboard, name='rl_dashboard'),
    path('dashboard/responsable-financier/', views.responsable_financier_dashboard, name='rf_dashboard'),
    path('dashboard/client/', views.client_dashboard, name='client_dashboard'),
    # Catalogue
    path('catalogue/', views.catalogue, name='catalogue'),
    path('catalogue/<str:reference>/', views.logement_detail, name='logement_detail'),
    path('catalogue/<str:reference>/visite/', views.demander_visite, name='demander_visite'),
    
    # Vues protégées
    path('mes-demandes/', views.mes_demandes, name='mes_demandes'),
    path('mes-contrats/', views.mes_contrats, name='mes_contrats'),

 
    # Propriétaires
    path('proprietaire/ajouter-bien/', views.ajouter_bien, name='ajouter_bien'),
    path('proprietaire/mes-paiements/', views.mes_paiements, name='mes_paiements'),
    path('profil/modifier/', views.modifier_profil, name='modifier_profil'),
    
    # Responsable Location
    path('responsable-location/demandes/<int:demande_id>/valider/', views.valider_demande, name='valider_demande'),
    path('responsable-location/demandes/<int:demande_id>/rejeter/', views.rejeter_demande, name='rejeter_demande'),
    path('responsable-location/demandes/<int:demande_id>/creer-contrat/', views.creer_contrat_location, name='creer_contrat_location'),
    
    # Responsable Financier
    path('responsable-financier/paiements/', views.gerer_paiements, name='gerer_paiements'),
    path('responsable-financier/paiements/<int:paiement_id>/enregistrer/', views.enregistrer_paiement, name='enregistrer_paiement'),
    path('responsable-financier/rapport/', views.rapport_financier, name='rapport_financier'),

     # Rendez-vous
    path('responsable-location/demandes/<int:demande_id>/prendre-rendez-vous/', 
         views.prendre_rendez_vous, name='prendre_rendez_vous'),
    path('responsable-location/mes-rendez-vous/', 
         views.mes_rendez_vous, name='mes_rendez_vous'),
    path('responsable-location/rendez-vous/<int:rendez_vous_id>/', 
         views.detail_rendez_vous, name='detail_rendez_vous'),
    path('responsable-location/rendez-vous/<int:rendez_vous_id>/annuler/', 
         views.annuler_rendez_vous, name='annuler_rendez_vous'),
    path('responsable-location/rendez-vous/<int:rendez_vous_id>/confirmer/', 
         views.confirmer_rendez_vous, name='confirmer_rendez_vous'),
    path('api/dashboard/alertes', views.api_dashboard_alertes, name='api_dashboard_alertes'),
    path('api/dashboard/alertes/', views.api_dashboard_alertes, name='api_dashboard_alertes_slash'),
]
