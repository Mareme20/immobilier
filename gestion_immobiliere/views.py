# gestion_immobiliere/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from .forms import UserRegistrationForm, LoginForm
from django.core.paginator import Paginator
from django.db.models import Q, F
from .models import Logement, Zone, ImageLogement, ContratGestion
from .forms import SearchForm, UserUpdateForm, ProfileUpdateForm, ProprietaireForm, UserForm, ProfileForm
from django.utils import timezone
from django.http import JsonResponse
from django.contrib.auth.views import PasswordChangeView
import logging
from django.urls import reverse_lazy
from .models import Proprietaire
from .models import DemandeLocation, Profile, PaiementLoyer, ContratLocation, Client

logger = logging.getLogger(__name__)

def home(request):
    """Page d'accueil pour les visiteurs"""
    # Récupérer quelques logements en vedette
    from .models import Logement
    logements_vedette = Logement.objects.filter(
        etat='disponible'
    ).select_related('zone', 'proprietaire__profile__user')[:6]
    
    # Annoter avec les prix
    for logement in logements_vedette:
        try:
            contrat = logement.contrat_gestion
            logement.prix_mensuel = contrat.prix_loyer_total
        except:
            logement.prix_mensuel = None
    
    context = {
        'title': 'TECH IIBS - Location immobilière',
        'logements_vedette': logements_vedette,
    }
    return render(request, 'gestion_immobiliere/home.html', context)

# Dans gestion_immobiliere/views.py, mettez à jour la vue register

# gestion_immobiliere/views.py (modifier la vue register)

def register(request):
    """Inscription des utilisateurs"""
    if request.user.is_authenticated:
        messages.info(request, 'Vous êtes déjà connecté.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                
                # Connecter automatiquement l'utilisateur
                from django.contrib.auth import login
                login(request, user)
                
                messages.success(
                    request, 
                    f'Bienvenue {user.first_name}! Votre compte a été créé avec succès.'
                )
                return redirect('dashboard')
                
            except Exception as e:
                logger.error(f"Erreur lors de l'inscription: {str(e)}")
                messages.error(
                    request, 
                    f'Une erreur est survenue lors de la création du compte : {str(e)}'
                )
    else:
        form = UserRegistrationForm()
    
    return render(request, 'gestion_immobiliere/register.html', {'form': form})
def login_view(request):
    """Connexion des utilisateurs"""
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Bienvenue {user.first_name}!')
                return redirect('dashboard')
    else:
        form = LoginForm()
    
    return render(request, 'gestion_immobiliere/login.html', {'form': form})

def logout_view(request):
    """Déconnexion"""
    logout(request)
    messages.info(request, 'Vous avez été déconnecté.')
    return redirect('home')

@login_required
def dashboard(request):
    """Tableau de bord selon le rôle"""
    user_role = request.user.profile.role
    
    if user_role == 'gestionnaire':
        return redirect('gestionnaire_dashboard')
    elif user_role == 'proprietaire':
        return redirect('proprietaire_dashboard')
    elif user_role == 'responsable_location':
        return redirect('rl_dashboard')
    elif user_role == 'responsable_financier':
        return redirect('rf_dashboard')
    elif user_role == 'client':
        return redirect('client_dashboard')
    else:
        # Rediriger les visiteurs vers le catalogue
        return redirect('catalogue')

@login_required
def mes_demandes(request):
    """Vue pour les demandes du client"""
    if request.user.profile.role != 'client':
        messages.error(request, 'Cette page est réservée aux clients.')
        return redirect('dashboard')
    
    from .models import DemandeLocation
    demandes = DemandeLocation.objects.filter(
        client=request.user.profile.client
    ).order_by('-date_demande')
    
    context = {
        'demandes': demandes,
    }
    return render(request, 'gestion_immobiliere/client/mes_demandes.html', context)

@login_required
def mes_contrats(request):
    """Vue pour les contrats du client"""
    if request.user.profile.role != 'client':
        messages.error(request, 'Cette page est réservée aux clients.')
        return redirect('dashboard')
    
    from .models import ContratLocation
    contrats = ContratLocation.objects.filter(
        client=request.user.profile.client
    ).order_by('-date_signature')
    
    context = {
        'contrats': contrats,
    }
    return render(request, 'gestion_immobiliere/client/mes_contrats.html', context)

# Ajouter à gestion_immobiliere/views.py

@login_required
def mon_profil(request):
    """Afficher et modifier le profil utilisateur"""
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        # Créer le profil s'il n'existe pas
        profile = Profile.objects.create(user=request.user)
        messages.info(request, 'Profil créé automatiquement.')
    
    if request.method == 'POST':
        # Formulaire pour mettre à jour les informations de base
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Votre profil a été mis à jour avec succès!')
            return redirect('mon_profil')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=profile)
    
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'profile': profile,
    }
    
    return render(request, 'gestion_immobiliere/profil/mon_profil.html', context)
 

# Ajouter à la fin de gestion_immobiliere/views.py

# ===== DASHBOARDS PAR RÔLE =====

@login_required
def gestionnaire_dashboard(request):
    """Dashboard du gestionnaire"""
    if request.user.profile.role != 'gestionnaire':
        messages.error(request, 'Accès réservé aux gestionnaires.')
        return redirect('dashboard')
    
    # Statistiques
    total_logements = Logement.objects.count()
    logements_disponibles = Logement.objects.filter(etat='disponible').count()
    logements_loues = Logement.objects.filter(etat='loue').count()
    total_proprietaires = Proprietaire.objects.count()
    total_clients = Client.objects.count()
    
    # Contrats de gestion
    contrats_gestion = ContratGestion.objects.filter(
        etat='en_cours'
    ).select_related('logement', 'proprietaire__profile__user')[:5]
    
    # Demandes récentes
    demandes_recentes = DemandeLocation.objects.filter(
        etat='attente'
    ).select_related('client__profile__user', 'logement')[:5]
    
    # Logements récemment ajoutés
    logements_recents = Logement.objects.all().order_by('-date_creation')[:5]
    
    context = {
        'total_logements': total_logements,
        'logements_disponibles': logements_disponibles,
        'logements_loues': logements_loues,
        'total_proprietaires': total_proprietaires,
        'total_clients': total_clients,
        'contrats_gestion': contrats_gestion,
        'demandes_recentes': demandes_recentes,
        'logements_recents': logements_recents,
    }
    
    return render(request, 'gestion_immobiliere/dashboards/gestionnaire_dashboard.html', context)

@login_required
def proprietaire_dashboard(request):
    """Dashboard du propriétaire"""
    if request.user.profile.role != 'proprietaire':
        messages.error(request, 'Accès réservé aux propriétaires.')
        return redirect('dashboard')
    
    try:
        proprietaire = request.user.profile.proprietaire
    except Proprietaire.DoesNotExist:
        messages.error(request, 'Profil propriétaire introuvable.')
        return redirect('dashboard')
    
    # Statistiques
    total_logements = proprietaire.logements.count()
    logements_disponibles = proprietaire.logements.filter(etat='disponible').count()
    logements_loues = proprietaire.logements.filter(etat='loue').count()
    
    # Contrats de gestion actifs
    contrats_actifs = proprietaire.contrats_gestion.filter(
        etat='en_cours'
    ).select_related('logement')[:5]
    
    # Revenus mensuels totaux
    revenus_mensuels = 0
    for contrat in contrats_actifs:
        revenus_mensuels += contrat.montant_mensuel
    
    # Paiements à venir
    from datetime import date
    from dateutil.relativedelta import relativedelta
    
    paiements_a_venir = []
    for contrat in contrats_actifs:
        next_payment = {
            'contrat': contrat,
            'montant': contrat.montant_mensuel,
            'date_limite': date.today().replace(day=5) + relativedelta(months=1)
        }
        paiements_a_venir.append(next_payment)
    
    # Demandes pour mes logements
    demandes_mes_logements = DemandeLocation.objects.filter(
        logement__proprietaire=proprietaire,
        etat='attente'
    ).select_related('client__profile__user', 'logement')[:5]
    
    context = {
        'proprietaire': proprietaire,
        'total_logements': total_logements,
        'logements_disponibles': logements_disponibles,
        'logements_loues': logements_loues,
        'revenus_mensuels': revenus_mensuels,
        'contrats_actifs': contrats_actifs,
        'paiements_a_venir': paiements_a_venir[:3],
        'demandes_mes_logements': demandes_mes_logements,
    }
    
    return render(request, 'gestion_immobiliere/dashboards/proprietaire_dashboard.html', context)

@login_required
def responsable_location_dashboard(request):
    """Dashboard du responsable location"""
    if request.user.profile.role != 'responsable_location':
        messages.error(request, 'Accès réservé aux responsables location.')
        return redirect('dashboard')
    
    # Demandes en attente
    demandes_attente = DemandeLocation.objects.filter(
        etat='attente'
    ).select_related('client__profile__user', 'logement').count()
    
    # Demandes à traiter aujourd'hui
    from datetime import date, timedelta
    aujourdhui = date.today()
    demandes_aujourdhui = DemandeLocation.objects.filter(
        date_demande__date=aujourdhui
    ).count()
    
    # Contrats à signer
    contrats_a_signer = ContratLocation.objects.filter(
        etat='en_attente'
    ).select_related('client__profile__user', 'logement').count()
    
    # Visites à organiser
    # (On pourrait avoir un modèle Visite, mais pour l'instant on utilise les demandes)
    
    # Liste des demandes récentes
    demandes_recentes = DemandeLocation.objects.filter(
        etat='attente'
    ).select_related('client__profile__user', 'logement')[:10]
    
    # Contrats récemment créés
    contrats_recents = ContratLocation.objects.filter(
        etat='en_cours'
    ).select_related('client__profile__user', 'logement').order_by('-date_signature')[:5]
    
    context = {
        'demandes_attente': demandes_attente,
        'demandes_aujourdhui': demandes_aujourdhui,
        'contrats_a_signer': contrats_a_signer,
        'demandes_recentes': demandes_recentes,
        'contrats_recents': contrats_recents,
    }
    
    return render(request, 'gestion_immobiliere/dashboards/responsable_location_dashboard.html', context)

@login_required
def responsable_financier_dashboard(request):
    """Dashboard du responsable financier"""
    if request.user.profile.role != 'responsable_financier':
        messages.error(request, 'Accès réservé aux responsables financiers.')
        return redirect('dashboard')
    
    from datetime import date
    from django.db.models import Sum
    
    # Paiements en retard
    paiements_retard = PaiementLoyer.objects.filter(
        statut='en_retard'
    ).select_related('contrat_location__client__profile__user').count()
    
    # Montant total des retards
    montant_retards = PaiementLoyer.objects.filter(
        statut='en_retard'
    ).aggregate(total=Sum('montant'))['total'] or 0
    
    # Paiements du mois courant
    mois_courant = date.today().replace(day=1)
    paiements_mois = PaiementLoyer.objects.filter(
        mois=mois_courant,
        statut='paye'
    ).aggregate(total=Sum('montant'))['total'] or 0
    
    # Paiements à effectuer aux propriétaires
    # (On aurait besoin d'un modèle PaiementProprietaire)
    
    # Liste des retards
    retards_liste = PaiementLoyer.objects.filter(
        statut='en_retard'
    ).select_related(
        'contrat_location__client__profile__user',
        'contrat_location__logement'
    )[:10]
    
    # Paiements récents
    paiements_recents = PaiementLoyer.objects.filter(
        statut='paye'
    ).select_related(
        'contrat_location__client__profile__user'
    ).order_by('-date_paiement')[:10]
    
    context = {
        'paiements_retard': paiements_retard,
        'montant_retards': montant_retards,
        'paiements_mois': paiements_mois,
        'retards_liste': retards_liste,
        'paiements_recents': paiements_recents,
    }
    
    return render(request, 'gestion_immobiliere/dashboards/responsable_financier_dashboard.html', context)

@login_required
def client_dashboard(request):
    """Dashboard du client"""
    if request.user.profile.role != 'client':
        messages.error(request, 'Accès réservé aux clients.')
        return redirect('dashboard')
    
    try:
        client = request.user.profile.client
    except Client.DoesNotExist:
        messages.error(request, 'Profil client introuvable.')
        return redirect('dashboard')
    
    # Statistiques
    total_demandes = client.demandes_location.count()
    demandes_actives = client.demandes_location.filter(etat='attente').count()
    total_contrats = client.contrats_location.count()
    contrats_actifs = client.contrats_location.filter(etat='en_cours').count()
    
    # Prochain paiement
    from datetime import date
    prochain_paiement = None
    for contrat in client.contrats_location.filter(etat='en_cours'):
        paiements = contrat.paiements.filter(statut='impaye').order_by('date_limite').first()
        if paiements:
            prochain_paiement = paiements
            break
    
    # Demandes récentes
    demandes_recentes = client.demandes_location.all().order_by('-date_demande')[:5]
    
    # Contrats actifs
    contrats_actifs_liste = client.contrats_location.filter(
        etat='en_cours'
    ).select_related('logement')[:5]
    
    # Logements favoris (à implémenter si on ajoute un système de favoris)
    
    context = {
        'client': client,
        'total_demandes': total_demandes,
        'demandes_actives': demandes_actives,
        'total_contrats': total_contrats,
        'contrats_actifs': contrats_actifs,
        'prochain_paiement': prochain_paiement,
        'demandes_recentes': demandes_recentes,
        'contrats_actifs_liste': contrats_actifs_liste,
    }
    
    return render(request, 'gestion_immobiliere/dashboards/client_dashboard.html', context)
 
def catalogue(request):
    """Afficher le catalogue des logements disponibles"""
    form = SearchForm(request.GET or None)
    
    # Récupérer tous les logements disponibles
    queryset = Logement.objects.filter(etat='disponible').select_related('zone', 'proprietaire__profile__user')
    
    if form.is_valid():
        # Filtrer par type de logement
        type_logement = form.cleaned_data.get('type_logement')
        if type_logement:
            queryset = queryset.filter(type_logement=type_logement)
        
        # Filtrer par zone
        zone = form.cleaned_data.get('zone')
        if zone:
            queryset = queryset.filter(zone=zone)
        
        # Filtrer par surface
        surface_min = form.cleaned_data.get('surface_min')
        if surface_min:
            queryset = queryset.filter(surface__gte=surface_min)
        
        surface_max = form.cleaned_data.get('surface_max')
        if surface_max:
            queryset = queryset.filter(surface__lte=surface_max)
        
        # Filtrer par prix (via ContratGestion)
        prix_min = form.cleaned_data.get('prix_min')
        prix_max = form.cleaned_data.get('prix_max')
        
        if prix_min or prix_max:
            # Sous-requête pour les contrats de gestion actifs
            contrats_actifs = ContratGestion.objects.filter(
                logement__in=queryset,
                etat='en_cours'
            )
            
            if prix_min:
                contrats_actifs = contrats_actifs.annotate(
                    prix_total=F('montant_mensuel') + F('logement__zone__forfait_agence') + F('logement__caution_fixe')
                ).filter(prix_total__gte=prix_min)
            
            if prix_max:
                contrats_actifs = contrats_actifs.annotate(
                    prix_total=F('montant_mensuel') + F('logement__zone__forfait_agence') + F('logement__caution_fixe')
                ).filter(prix_total__lte=prix_max)
            
            # Filtrer les logements ayant un contrat actif correspondant
            logement_ids = contrats_actifs.values_list('logement_id', flat=True)
            queryset = queryset.filter(id__in=logement_ids)
        
        # Trier les résultats
        order_by = form.cleaned_data.get('order_by', 'date_creation')
        if order_by == 'prix':
            # Trier par prix via annotation
            queryset = queryset.filter(contrats_gestion__etat='en_cours').annotate(
                prix_total=F('contrats_gestion__montant_mensuel') + F('zone__forfait_agence') + F('caution_fixe')
            ).order_by('prix_total')
        elif order_by == '-prix':
            queryset = queryset.filter(contrats_gestion__etat='en_cours').annotate(
                prix_total=F('contrats_gestion__montant_mensuel') + F('zone__forfait_agence') + F('caution_fixe')
            ).order_by('-prix_total')
        else:
            queryset = queryset.order_by(order_by)
    
    # Pagination
    paginator = Paginator(queryset, 12)  # 12 logements par page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Annoter chaque logement avec son prix
    for logement in page_obj.object_list:
        try:
            contrat = logement.contrat_gestion
            logement.prix_mensuel = contrat.prix_loyer_total
            logement.prix_formatted = f"{logement.prix_mensuel:.2f}"
        except ContratGestion.DoesNotExist:
            logement.prix_mensuel = None
            logement.prix_formatted = "Non disponible"
    
    context = {
        'form': form,
        'page_obj': page_obj,
        'total_logements': queryset.count(),
        'zones': Zone.objects.all(),
        'search_params': request.GET.dict(),
    }
    
    return render(request, 'gestion_immobiliere/catalogue/catalogue.html', context)
def logement_detail(request, reference):
    logement = get_object_or_404(Logement, reference=reference)

    # Récupérer les images du logement
    images = ImageLogement.objects.filter(logement=logement).order_by('ordre')
    
    # Calculer le prix mensuel
    prix_mensuel = None
    try:
        prix_mensuel = logement.contrat_gestion.prix_loyer_total
    except ContratGestion.DoesNotExist:
        prix_mensuel = None
    
    # --- CORRECTION ICI ---
    # On utilise .exclude() pour retirer le logement actuel de la liste
    logements_similaires = Logement.objects.filter(
        etat='disponible'
    ).exclude(
        id=logement.id
    ).filter(
        Q(type_logement=logement.type_logement) | Q(zone=logement.zone)
    )[:4]
    # ----------------------
    
    # Annoter le prix pour les logements similaires
    for sim_logement in logements_similaires:
        try:
            contrat = sim_logement.contrat_gestion
            sim_logement.prix_mensuel = contrat.prix_loyer_total
        except ContratGestion.DoesNotExist:
            sim_logement.prix_mensuel = None
    
    context = {
        'logement': logement,
        'images': images,
        'prix_mensuel': prix_mensuel,
        'logements_similaires': logements_similaires,
        'main_image': images.first() if images.exists() else None,
    }
    
    return render(request, 'gestion_immobiliere/catalogue/logement_detail.html', context)
def demander_visite(request, reference):
    """Formulaire pour demander une visite"""
    if not request.user.is_authenticated:
        request.session['next_url'] = request.path
        from django.contrib import messages
        messages.warning(request, 'Veuillez vous connecter pour demander une visite.')
        return redirect('login')
    
    # --- MODIFICATION ICI ---
    # 1. On cherche par référence sans tenir compte de la casse (__iexact)
    # 2. On enlève etat='disponible' pour éviter la 404 si le statut a changé
    from django.shortcuts import get_object_or_404
    logement = get_object_or_404(Logement, reference__iexact=reference)
    
    # 3. On vérifie l'état séparément pour afficher un message clair
    if logement.etat != 'disponible':
        from django.contrib import messages
        messages.error(request, f"Ce logement ({reference}) n'est plus disponible à la visite.")
        return redirect('catalogue')
    # -------------------------

    if request.method == 'POST':
        from .models import DemandeLocation
        from django.utils import timezone
        from django.contrib import messages
        
        try:
            # Vérifiez bien que l'utilisateur a un profil et un client lié
            client = getattr(request.user.profile, 'client', None)
            if not client:
                messages.error(request, "Votre compte n'est pas configuré comme un compte client.")
                return redirect('home')

            date_visite = request.POST.get('date_visite')
            message = request.POST.get('message', '')
            from datetime import datetime
            date_debut = timezone.now().date()
            if date_visite:
                try:
                    date_debut = datetime.strptime(date_visite, "%Y-%m-%d").date()
                except ValueError:
                    pass
            
            DemandeLocation.objects.create(
                client=client,
                logement=logement,
                date_debut_souhaitee=date_debut,
                duree_souhaitee=1,
                notes=f"Demande de visite le {date_visite}. Message: {message}"
            )
            
            messages.success(request, 'Votre demande de visite a été enregistrée !')
            return redirect('client_dashboard') # Assurez-vous que cette URL existe
            
        except Exception as e:
            messages.error(request, f'Erreur: {str(e)}')
    
    context = {
        'logement': logement,
    }
    
    return render(request, 'gestion_immobiliere/catalogue/demander_visite.html', context)

@login_required
def gerer_contrats_gestion(request):
    """Gestion des contrats de gestion (gestionnaire)"""
    if request.user.profile.role != 'gestionnaire':
        messages.error(request, 'Accès réservé aux gestionnaires.')
        return redirect('dashboard')
    
    contrats = ContratGestion.objects.all().select_related(
        'logement', 'proprietaire__profile__user'
    ).order_by('-date_creation')

    etat = request.GET.get('etat', '').strip()
    date_debut = request.GET.get('date_debut', '').strip()
    search = request.GET.get('search', '').strip()
    proprietaire_id = request.GET.get('proprietaire', '').strip()

    if etat:
        contrats = contrats.filter(etat=etat)

    if date_debut:
        contrats = contrats.filter(date_debut=date_debut)

    if proprietaire_id:
        contrats = contrats.filter(proprietaire_id=proprietaire_id)

    if search:
        contrats = contrats.filter(
            Q(logement__reference__icontains=search) |
            Q(proprietaire__profile__user__first_name__icontains=search) |
            Q(proprietaire__profile__user__last_name__icontains=search)
        )
    
    context = {
        'contrats': contrats,
        'proprietaires': Proprietaire.objects.select_related('profile__user').all(),
    }
    return render(request, 'gestion_immobiliere/gestion/gerer_contrats_gestion.html', context)

@login_required
def mes_biens(request):
    """Liste des biens d'un propriétaire"""
    if request.user.profile.role != 'proprietaire':
        messages.error(request, 'Accès réservé aux propriétaires.')
        return redirect('dashboard')
    
    try:
        proprietaire = request.user.profile.proprietaire
    except Proprietaire.DoesNotExist:
        messages.error(request, 'Profil propriétaire introuvable.')
        return redirect('dashboard')
    
    logements = proprietaire.logements.all().select_related('zone')
    etat = request.GET.get('etat', '').strip()
    if etat:
        logements = logements.filter(etat=etat)
    
    context = {
        'logements': logements,
        'proprietaire': proprietaire,
    }
    return render(request, 'gestion_immobiliere/proprietaire/mes_biens.html', context)

@login_required
def traiter_demandes(request):
    """Traiter les demandes de location (responsable location)"""
    if request.user.profile.role != 'responsable_location':
        messages.error(request, 'Accès réservé aux responsables location.')
        return redirect('dashboard')
    
    demandes = DemandeLocation.objects.filter(
        etat='attente'
    ).select_related('client__profile__user', 'logement')
    
    context = {
        'demandes': demandes,
    }
    return render(request, 'gestion_immobiliere/responsable_location/traiter_demandes.html', context)

class CustomPasswordChangeView(PasswordChangeView):
    template_name = 'gestion_immobiliere/profil/change_password.html'
    success_url = reverse_lazy('mon_profil')
    
    def form_valid(self, form):
        messages.success(self.request, 'Votre mot de passe a été changé avec succès!')
        return super().form_valid(form)
from .forms import LogementForm, ImageLogementFormSet, ContratGestionForm, ZoneForm
 
@login_required
def ajouter_logement(request):
    """Ajouter un nouveau logement"""
    if request.method == 'POST':
        form = LogementForm(request.POST)
        formset = ImageLogementFormSet(request.POST, request.FILES)
        
        if form.is_valid() and formset.is_valid():
            logement = form.save()
            formset.instance = logement
            formset.save()
            
            messages.success(request, f'Logement {logement.reference} ajouté avec succès!')
            return redirect('gerer_logements')
    else:
        form = LogementForm()
        formset = ImageLogementFormSet()
    
    context = {
        'form': form,
        'formset': formset,
        'title': 'Ajouter un logement',
    }
    return render(request, 'gestion_immobiliere/gestion/ajouter_logement.html', context)

@login_required
def modifier_logement(request, pk):
    """Modifier un logement existant"""
    logement = get_object_or_404(Logement, pk=pk)
    
    if request.method == 'POST':
        form = LogementForm(request.POST, instance=logement)
        formset = ImageLogementFormSet(request.POST, request.FILES, instance=logement)
        
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            
            messages.success(request, f'Logement {logement.reference} modifié avec succès!')
            return redirect('gerer_logements')
    else:
        form = LogementForm(instance=logement)
        formset = ImageLogementFormSet(instance=logement)
    
    context = {
        'form': form,
        'formset': formset,
        'logement': logement,
        'title': f'Modifier {logement.reference}',
    }
    return render(request, 'gestion_immobiliere/gestion/ajouter_logement.html', context)

@login_required
def supprimer_logement(request, pk):
    """Supprimer un logement"""
    logement = get_object_or_404(Logement, pk=pk)
    
    if request.method == 'POST':
        reference = logement.reference
        logement.delete()
        messages.success(request, f'Logement {reference} supprimé avec succès!')
        return redirect('gerer_logements')
    
    context = {
        'logement': logement,
    }
    return render(request, 'gestion_immobiliere/gestion/supprimer_logement.html', context)

@login_required
def archiver_logement(request, pk):
    """Archiver/désarchiver un logement"""
    logement = get_object_or_404(Logement, pk=pk)
    
    if logement.etat == 'archive':
        logement.etat = 'disponible'
        action = 'désarchivé'
    else:
        logement.etat = 'archive'
        action = 'archivé'
    
    logement.save()
    messages.success(request, f'Logement {logement.reference} {action} avec succès!')
    return redirect('gerer_logements')

@login_required
def ajouter_contrat_gestion(request):
    """Ajouter un nouveau contrat de gestion"""
    if request.method == 'POST':
        form = ContratGestionForm(request.POST, request.FILES)
        if form.is_valid():
            contrat = form.save()
            messages.success(request, f'Contrat de gestion #{contrat.id} ajouté avec succès!')
            return redirect('gerer_contrats_gestion')
    else:
        form = ContratGestionForm()
    
    context = {
        'form': form,
        'title': 'Ajouter un contrat de gestion',
    }
    return render(request, 'gestion_immobiliere/gestion/ajouter_contrat_gestion.html', context)

@login_required
def modifier_contrat_gestion(request, pk):
    """Modifier un contrat de gestion existant"""
    contrat = get_object_or_404(ContratGestion, pk=pk)
    
    if request.method == 'POST':
        form = ContratGestionForm(request.POST, request.FILES, instance=contrat)
        if form.is_valid():
            form.save()
            messages.success(request, f'Contrat de gestion #{contrat.id} modifié avec succès!')
            return redirect('gerer_contrats_gestion')
    else:
        form = ContratGestionForm(instance=contrat)
    
    context = {
        'form': form,
        'contrat': contrat,
        'title': f'Modifier le contrat #{contrat.id}',
    }
    return render(request, 'gestion_immobiliere/gestion/ajouter_contrat_gestion.html', context)

@login_required
def supprimer_contrat_gestion(request, pk):
    """Supprimer un contrat de gestion"""
    contrat = get_object_or_404(ContratGestion, pk=pk)
    
    if request.method == 'POST':
        contrat_id = contrat.id
        contrat.delete()
        messages.success(request, f'Contrat de gestion #{contrat_id} supprimé avec succès!')
        return redirect('gerer_contrats_gestion')
    
    context = {
        'contrat': contrat,
    }
    return render(request, 'gestion_immobiliere/gestion/supprimer_contrat_gestion.html', context)



@login_required
def gerer_logements(request):
    """Gestion des logements (gestionnaire)"""
    if request.user.profile.role != 'gestionnaire':
        messages.error(request, 'Accès réservé aux gestionnaires.')
        return redirect('dashboard')
    
    logements = Logement.objects.all().select_related(
        'zone', 'proprietaire__profile__user'
    ).order_by('-date_creation')
    
    # Filtres
    search = request.GET.get('search', '')
    type_logement = request.GET.get('type', '')
    etat = request.GET.get('etat', '')
    zone_id = request.GET.get('zone', '')
    proprietaire_id = request.GET.get('proprietaire', '')
    
    if search:
        logements = logements.filter(
            Q(reference__icontains=search) |
            Q(adresse__icontains=search) |
            Q(description__icontains=search)
        )
    
    if type_logement:
        logements = logements.filter(type_logement=type_logement)
    
    if etat:
        logements = logements.filter(etat=etat)
    
    if zone_id:
        logements = logements.filter(zone_id=zone_id)
    
    if proprietaire_id:
        logements = logements.filter(proprietaire_id=proprietaire_id)
    
    # Pagination
    paginator = Paginator(logements, 25)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Statistiques
    stats = {
        'disponibles': Logement.objects.filter(etat='disponible').count(),
        'loues': Logement.objects.filter(etat='loue').count(),
        'maintenance': Logement.objects.filter(etat='maintenance').count(),
        'archives': Logement.objects.filter(etat='archive').count(),
    }
    
    context = {
        'logements': page_obj,
        'page_obj': page_obj,
        'is_paginated': paginator.num_pages > 1,
        'stats': stats,
        'zones': Zone.objects.all(),
        'proprietaires': Proprietaire.objects.all().select_related('profile__user'),
    }
    
    return render(request, 'gestion_immobiliere/gestion/gerer_logements.html', context)



# gestion_immobiliere/views.py (ajouter)

@login_required
def gerer_zones(request):
    """Gestion des zones"""
    zones = Zone.objects.all().order_by('nom')
    
    if request.method == 'POST':
        form = ZoneForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Zone ajoutée avec succès!')
            return redirect('gerer_zones')
    else:
        form = ZoneForm()
    
    context = {
        'zones': zones,
        'form': form,
    }
    return render(request, 'gestion_immobiliere/gestion/gerer_zones.html', context)

@login_required
def modifier_zone(request, pk):
    """Modifier une zone"""
    zone = get_object_or_404(Zone, pk=pk)
    
    if request.method == 'POST':
        form = ZoneForm(request.POST, instance=zone)
        if form.is_valid():
            form.save()
            messages.success(request, f'Zone "{zone.nom}" modifiée avec succès!')
            return redirect('gerer_zones')
    else:
        form = ZoneForm(instance=zone)
    
    context = {
        'form': form,
        'zone': zone,
    }
    return render(request, 'gestion_immobiliere/gestion/modifier_zone.html', context)

@login_required
def supprimer_zone(request, pk):
    """Supprimer une zone"""
    zone = get_object_or_404(Zone, pk=pk)
    
    if request.method == 'POST':
        nom = zone.nom
        zone.delete()
        messages.success(request, f'Zone "{nom}" supprimée avec succès!')
        return redirect('gerer_zones')
    
    context = {
        'zone': zone,
    }
    return render(request, 'gestion_immobiliere/gestion/supprimer_zone.html', context)




    # gestion_immobiliere/views.py (ajouter)
 
@login_required
def ajouter_bien(request):
    """Ajouter un nouveau bien (propriétaire)"""
    try:
        proprietaire = request.user.profile.proprietaire
    except Proprietaire.DoesNotExist:
        messages.error(request, 'Profil propriétaire introuvable.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = LogementForm(request.POST)
        formset = ImageLogementFormSet(request.POST, request.FILES)
        
        if form.is_valid() and formset.is_valid():
            logement = form.save(commit=False)
            logement.proprietaire = proprietaire
            logement.save()
            
            formset.instance = logement
            formset.save()
            
            messages.success(request, f'Bien {logement.reference} ajouté avec succès!')
            return redirect('mes_biens')
    else:
        form = LogementForm(initial={'proprietaire': proprietaire})
        form.fields['proprietaire'].disabled = True
        formset = ImageLogementFormSet()
    
    context = {
        'form': form,
        'formset': formset,
        'title': 'Ajouter un bien immobilier',
    }
    return render(request, 'gestion_immobiliere/proprietaire/ajouter_bien.html', context)

@login_required
def mes_paiements(request):
    """Voir les paiements reçus (propriétaire)"""
    try:
        proprietaire = request.user.profile.proprietaire
    except Proprietaire.DoesNotExist:
        messages.error(request, 'Profil propriétaire introuvable.')
        return redirect('dashboard')
    
    # Récupérer les paiements via les contrats de gestion
    contrats = proprietaire.contrats_gestion.all()
    
    # Pour l'instant, on affiche les contrats
    # (À compléter avec le modèle PaiementProprietaire)
    
    context = {
        'contrats': contrats,
        'proprietaire': proprietaire,
    }
    return render(request, 'gestion_immobiliere/proprietaire/mes_paiements.html', context)

@login_required
def modifier_profil(request):
    """Modifier le profil utilisateur"""
    user = request.user
    profile = user.profile
    
    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=user)
        profile_form = ProfileForm(request.POST, request.FILES, instance=profile)
        
        # Formulaire spécifique au propriétaire
        proprietaire_form = None
        if hasattr(profile, 'proprietaire'):
            proprietaire_form = ProprietaireForm(request.POST, instance=profile.proprietaire)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            
            if proprietaire_form and proprietaire_form.is_valid():
                proprietaire_form.save()
            
            messages.success(request, 'Profil mis à jour avec succès!')
            return redirect('mon_profil')
    else:
        user_form = UserForm(instance=user)
        profile_form = ProfileForm(instance=profile)
        
        proprietaire_form = None
        if hasattr(profile, 'proprietaire'):
            proprietaire_form = ProprietaireForm(instance=profile.proprietaire)
    
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'proprietaire_form': proprietaire_form,
    }
    
    return render(request, 'gestion_immobiliere/profil/modifier_profil.html', context)



# gestion_immobiliere/views.py (ajouter)
 
@login_required
def valider_demande(request, demande_id):
    """Valider une demande de location"""
    if request.user.profile.role != 'responsable_location':
        messages.error(request, 'Accès réservé aux responsables location.')
        return redirect('dashboard')

    demande = get_object_or_404(DemandeLocation, id=demande_id, etat='attente')
    
    if request.method == 'POST':
        demande.etat = 'validee'
        demande.valide_par = request.user
        demande.date_validation = timezone.now()
        demande.save()
        
        # Mettre à jour l'état du logement
        demande.logement.etat = 'loue'
        demande.logement.save()
        
        messages.success(request, f'Demande #{demande.id} validée avec succès!')
        return redirect('traiter_demandes')
    
    context = {
        'demande': demande,
    }
    return render(request, 'gestion_immobiliere/responsable_location/valider_demande.html', context)

@login_required
def rejeter_demande(request, demande_id):
    """Rejeter une demande de location"""
    if request.user.profile.role != 'responsable_location':
        messages.error(request, 'Accès réservé aux responsables location.')
        return redirect('dashboard')

    demande = get_object_or_404(DemandeLocation, id=demande_id, etat='attente')
    
    if request.method == 'POST':
        motif = request.POST.get('motif', '')
        demande.etat = 'rejetee'
        demande.motif_rejet = motif
        demande.valide_par = request.user
        demande.date_validation = timezone.now()
        demande.save()
        
        messages.success(request, f'Demande #{demande.id} rejetée avec succès!')
        return redirect('traiter_demandes')
    
    context = {
        'demande': demande,
    }
    return render(request, 'gestion_immobiliere/responsable_location/rejeter_demande.html', context)

@login_required
def creer_contrat_location(request, demande_id):
    """Créer un contrat de location à partir d'une demande validée"""
    if request.user.profile.role != 'responsable_location':
        messages.error(request, 'Accès réservé aux responsables location.')
        return redirect('dashboard')

    demande = get_object_or_404(DemandeLocation, id=demande_id, etat='validee')
    
    if request.method == 'POST':
        try:
            # Récupérer le contrat de gestion du logement
            contrat_gestion = demande.logement.contrat_gestion
            
            # Calculer la date de fin
            from dateutil.relativedelta import relativedelta
            date_fin = demande.date_debut_souhaitee + relativedelta(months=demande.duree_souhaitee)
            
            # Créer le contrat de location
            contrat = ContratLocation.objects.create(
                demande_location=demande,
                client=demande.client,
                logement=demande.logement,
                contrat_gestion=contrat_gestion,
                date_debut=demande.date_debut_souhaitee,
                date_fin=date_fin,
                montant_loyer=contrat_gestion.prix_loyer_total,
                caution_versee=demande.logement.caution_fixe,
                etat='en_attente'  # À signer
            )
            
            # Mettre à jour l'état de la demande
            demande.etat = 'convertie'
            demande.save()
            
            messages.success(request, f'Contrat de location #{contrat.id} créé avec succès!')
            return redirect('traiter_demandes')
            
        except Exception as e:
            messages.error(request, f'Erreur: {str(e)}')
    
    context = {
        'demande': demande,
    }
    return render(request, 'gestion_immobiliere/responsable_location/creer_contrat_location.html', context)



# gestion_immobiliere/views.py (ajouter)
from django.db.models import Sum, Count

@login_required
def gerer_paiements(request):
    """Gérer les paiements de loyer"""
    if request.user.profile.role != 'responsable_financier':
        messages.error(request, 'Accès réservé aux responsables financiers.')
        return redirect('dashboard')

    paiements = PaiementLoyer.objects.all().select_related(
        'contrat_location__client__profile__user',
        'contrat_location__logement'
    ).order_by('-date_limite')
    
    # Filtres
    statut = request.GET.get('statut', '')
    mois = request.GET.get('mois', '')
    search = request.GET.get('search', '').strip()
    
    if statut:
        paiements = paiements.filter(statut=statut)
    
    if mois:
        try:
            year, month = map(int, mois.split('-'))
            paiements = paiements.filter(mois__year=year, mois__month=month)
        except (ValueError, TypeError):
            messages.warning(request, 'Filtre mois invalide. Format attendu: YYYY-MM.')

    if search:
        paiements = paiements.filter(
            Q(contrat_location__client__profile__user__first_name__icontains=search) |
            Q(contrat_location__client__profile__user__last_name__icontains=search) |
            Q(contrat_location__logement__reference__icontains=search)
        )
    
    # Statistiques
    stats = {
        'total': paiements.count(),
        'payes': paiements.filter(statut='paye').count(),
        'retard': paiements.filter(statut='en_retard').count(),
        'impayes': paiements.filter(statut='impaye').count(),
        'montant_total': paiements.filter(statut='paye').aggregate(total=Sum('montant'))['total'] or 0,
        'montant_retard': paiements.filter(statut='en_retard').aggregate(total=Sum('montant'))['total'] or 0,
    }
    
    context = {
        'paiements': paiements,
        'stats': stats,
    }
    return render(request, 'gestion_immobiliere/responsable_financier/gerer_paiements.html', context)

@login_required
def enregistrer_paiement(request, paiement_id):
    """Enregistrer un paiement"""
    if request.user.profile.role != 'responsable_financier':
        messages.error(request, 'Accès réservé aux responsables financiers.')
        return redirect('dashboard')

    paiement = get_object_or_404(PaiementLoyer, id=paiement_id)
    
    if request.method == 'POST':
        montant = request.POST.get('montant', paiement.montant)
        mode_paiement = request.POST.get('mode_paiement')
        reference = request.POST.get('reference_paiement', '')
        
        try:
            paiement.montant = montant
            paiement.mode_paiement = mode_paiement
            paiement.reference_paiement = reference
            paiement.statut = 'paye'
            paiement.date_paiement = timezone.now()
            paiement.encaisse_par = request.user
            paiement.save()
            
            messages.success(request, f'Paiement enregistré avec succès!')
            return redirect('gerer_paiements')
            
        except Exception as e:
            messages.error(request, f'Erreur: {str(e)}')
    
    context = {
        'paiement': paiement,
    }
    return render(request, 'gestion_immobiliere/responsable_financier/enregistrer_paiement.html', context)

@login_required
def rapport_financier(request):
    """Générer un rapport financier"""
    if request.user.profile.role != 'responsable_financier':
        messages.error(request, 'Accès réservé aux responsables financiers.')
        return redirect('dashboard')

    from datetime import date, timedelta
    from dateutil.relativedelta import relativedelta
    
    # Période par défaut : dernier mois
    fin_periode = date.today().replace(day=1) - timedelta(days=1)
    debut_periode = fin_periode.replace(day=1)
    
    # Récupérer les paiements de la période
    paiements = PaiementLoyer.objects.filter(
        mois__range=[debut_periode, fin_periode]
    )
    
    # Statistiques
    stats = {
        'total_paiements': paiements.count(),
        'paiements_payes': paiements.filter(statut='paye').count(),
        'montant_total': paiements.filter(statut='paye').aggregate(total=Sum('montant'))['total'] or 0,
        'taux_recouvrement': (paiements.filter(statut='paye').count() / paiements.count() * 100) if paiements.count() > 0 else 0,
    }
    
    # Paiements par mode
    modes_paiement = paiements.filter(statut='paye').values('mode_paiement').annotate(
        total=Sum('montant'),
        count=Count('id')
    )
    
    context = {
        'debut_periode': debut_periode,
        'fin_periode': fin_periode,
        'stats': stats,
        'modes_paiement': modes_paiement,
        'paiements': paiements[:50],  # Limiter pour l'affichage
    }
    
    return render(request, 'gestion_immobiliere/responsable_financier/rapport_financier.html', context)








# gestion_immobiliere/views.py (ajouter)

from .forms import RendezVousForm
from .models import RendezVous

@login_required
def prendre_rendez_vous(request, demande_id):
    """Prendre un rendez-vous après validation d'une demande"""
    if request.user.profile.role != 'responsable_location':
        messages.error(request, 'Accès réservé aux responsables location.')
        return redirect('dashboard')

    demande = get_object_or_404(
        DemandeLocation, 
        id=demande_id, 
        etat='validee'
    )
    
    # Vérifier qu'il n'y a pas déjà un rendez-vous
    if hasattr(demande, 'rendez_vous'):
        messages.info(request, 'Un rendez-vous existe déjà pour cette demande.')
        return redirect('detail_rendez_vous', demande.rendez_vous.pk)
    
    if request.method == 'POST':
        form = RendezVousForm(request.POST, demande=demande)
        if form.is_valid():
            rendez_vous = form.save(commit=False)
            rendez_vous.demande_location = demande
            rendez_vous.contact_agence = request.user
            rendez_vous.save()
            
            messages.success(request, 'Rendez-vous planifié avec succès !')
            
            # Notifier le client (à implémenter)
            # envoyer_notification_rendez_vous(rendez_vous)
            
            return redirect('traiter_demandes')
    else:
        form = RendezVousForm(demande=demande)
    
    context = {
        'form': form,
        'demande': demande,
        'title': 'Prendre un rendez-vous',
    }
    return render(request, 'gestion_immobiliere/responsable_location/prendre_rendez_vous.html', context)

@login_required
def mes_rendez_vous(request):
    """Liste des rendez-vous du responsable location"""
    if request.user.profile.role != 'responsable_location':
        messages.error(request, 'Accès réservé aux responsables location.')
        return redirect('dashboard')

    aujourdhui = timezone.now().date()
    
    # Rendez-vous à venir
    rendez_vous_a_venir = RendezVous.objects.filter(
        date_rendez_vous__gte=timezone.now(),
        statut__in=['planifie', 'confirme']
    ).select_related(
        'demande_location__client__profile__user',
        'demande_location__logement'
    ).order_by('date_rendez_vous')
    
    # Rendez-vous passés
    rendez_vous_passes = RendezVous.objects.filter(
        date_rendez_vous__lt=timezone.now()
    ).select_related(
        'demande_location__client__profile__user',
        'demande_location__logement'
    ).order_by('-date_rendez_vous')[:10]
    
    # Rendez-vous d'aujourd'hui
    rendez_vous_aujourdhui = RendezVous.objects.filter(
        date_rendez_vous__date=aujourdhui,
        statut__in=['planifie', 'confirme']
    ).select_related(
        'demande_location__client__profile__user',
        'demande_location__logement'
    )
    
    context = {
        'rendez_vous_a_venir': rendez_vous_a_venir,
        'rendez_vous_passes': rendez_vous_passes,
        'rendez_vous_aujourdhui': rendez_vous_aujourdhui,
        'aujourdhui': aujourdhui,
    }
    
    return render(request, 'gestion_immobiliere/responsable_location/mes_rendez_vous.html', context)

@login_required
def detail_rendez_vous(request, rendez_vous_id):
    """Détails d'un rendez-vous"""
    if request.user.profile.role != 'responsable_location':
        messages.error(request, 'Accès réservé aux responsables location.')
        return redirect('dashboard')

    rendez_vous = get_object_or_404(
        RendezVous.objects.select_related(
            'demande_location__client__profile__user',
            'demande_location__logement',
            'contact_agence'
        ),
        pk=rendez_vous_id
    )
    
    context = {
        'rdv': rendez_vous,
    }
    
    return render(request, 'gestion_immobiliere/responsable_location/detail_rendez_vous.html', context)

@login_required
def annuler_rendez_vous(request, rendez_vous_id):
    """Annuler un rendez-vous"""
    if request.user.profile.role != 'responsable_location':
        messages.error(request, 'Accès réservé aux responsables location.')
        return redirect('dashboard')

    rendez_vous = get_object_or_404(RendezVous, pk=rendez_vous_id)
    
    if not rendez_vous.peut_etre_annule:
        messages.error(request, 'Ce rendez-vous ne peut plus être annulé.')
        return redirect('mes_rendez_vous')
    
    if request.method == 'POST':
        motif = request.POST.get('motif', '')
        rendez_vous.statut = 'annule'
        rendez_vous.notes = f"{rendez_vous.notes or ''}\n\nAnnulé le {timezone.now().strftime('%d/%m/%Y %H:%M')}. Motif: {motif}"
        rendez_vous.save()
        
        messages.success(request, 'Rendez-vous annulé avec succès.')
        
        # Notifier le client (à implémenter)
        # envoyer_notification_annulation(rendez_vous, motif)
        
        return redirect('mes_rendez_vous')
    
    context = {
        'rendez_vous': rendez_vous,
    }
    
    return render(request, 'gestion_immobiliere/responsable_location/annuler_rendez_vous.html', context)

@login_required
def confirmer_rendez_vous(request, rendez_vous_id):
    """Confirmer un rendez-vous"""
    if request.user.profile.role != 'responsable_location':
        messages.error(request, 'Accès réservé aux responsables location.')
        return redirect('dashboard')

    rendez_vous = get_object_or_404(RendezVous, pk=rendez_vous_id, statut='planifie')
    
    rendez_vous.statut = 'confirme'
    rendez_vous.save()
    
    messages.success(request, 'Rendez-vous confirmé.')
    
    # Notifier le client (à implémenter)
    # envoyer_notification_confirmation(rendez_vous)
    
    return redirect('mes_rendez_vous')


@login_required
def api_dashboard_alertes(request):
    """Endpoint léger pour éviter les 404 côté dashboard."""
    return JsonResponse({'alertes': []})
