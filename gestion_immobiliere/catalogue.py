# gestion_immobiliere/views/catalogue.py
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q, F, Value, CharField
from django.db.models.functions import Concat
from .models import Logement, Zone, ImageLogement, ContratGestion
from .forms import SearchForm
import math
from django.shortcuts import render, redirect
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
                    prix_total=F('montant_mensuel') + F('logement__zone__forfait_agence')
                ).filter(prix_total__gte=prix_min)
            
            if prix_max:
                contrats_actifs = contrats_actifs.annotate(
                    prix_total=F('montant_mensuel') + F('logement__zone__forfait_agence')
                ).filter(prix_total__lte=prix_max)
            
            # Filtrer les logements ayant un contrat actif correspondant
            logement_ids = contrats_actifs.values_list('logement_id', flat=True)
            queryset = queryset.filter(id__in=logement_ids)
        
        # Trier les résultats
        order_by = form.cleaned_data.get('order_by', 'date_creation')
        if order_by == 'prix':
            # Trier par prix via annotation
            queryset = queryset.annotate(
                prix_total=F('contrat_gestion__montant_mensuel') + F('zone__forfait_agence')
            ).order_by('prix_total')
        elif order_by == '-prix':
            queryset = queryset.annotate(
                prix_total=F('contrat_gestion__montant_mensuel') + F('zone__forfait_agence')
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
            logement.prix_mensuel = contrat.montant_mensuel + logement.zone.forfait_agence
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
    """Détails d'un logement spécifique"""
    logement = get_object_or_404(
        Logement.objects.select_related(
            'zone', 
            'proprietaire__profile__user',
            'contrat_gestion'
        ),
        reference=reference,
        etat='disponible'
    )
    
    # Récupérer les images du logement
    images = ImageLogement.objects.filter(logement=logement).order_by('ordre')
    
    # Calculer le prix mensuel
    prix_mensuel = None
    if hasattr(logement, 'contrat_gestion'):
        prix_mensuel = logement.contrat_gestion.montant_mensuel + logement.zone.forfait_agence
    
    # Logements similaires (même type ou même zone)
    logements_similaires = Logement.objects.filter(
        etat='disponible',
        id__ne=logement.id
    ).filter(
        Q(type_logement=logement.type_logement) | Q(zone=logement.zone)
    )[:4]
    
    # Annoter le prix pour les logements similaires
    for sim_logement in logements_similaires:
        try:
            contrat = sim_logement.contrat_gestion
            sim_logement.prix_mensuel = contrat.montant_mensuel + sim_logement.zone.forfait_agence
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
        # Stocker l'URL de redirection
        request.session['next_url'] = request.path
        from django.contrib import messages
        messages.warning(request, 'Veuillez vous connecter pour demander une visite.')
        return redirect('login')
    
    logement = get_object_or_404(Logement, reference=reference, etat='disponible')
    
    if request.method == 'POST':
        # Créer une demande de location
        from .models import DemandeLocation, Client
        from django.utils import timezone
        
        try:
            client = request.user.profile.client
            date_visite = request.POST.get('date_visite')
            message = request.POST.get('message', '')
            
            # Créer la demande
            DemandeLocation.objects.create(
                client=client,
                logement=logement,
                date_debut_souhaitee=timezone.now().date(),
                duree_souhaitee=12,  # Par défaut 12 mois
                notes=f"Demande de visite le {date_visite}. Message: {message}"
            )
            
            from django.contrib import messages
            messages.success(request, 'Votre demande de visite a été enregistrée !')
            return redirect('mes_demandes')
            
        except Exception as e:
            from django.contrib import messages
            messages.error(request, f'Erreur: {str(e)}')
    
    context = {
        'logement': logement,
    }
    
    return render(request, 'gestion_immobiliere/catalogue/demander_visite.html', context)