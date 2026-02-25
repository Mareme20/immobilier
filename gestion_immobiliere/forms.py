# gestion_immobiliere/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import Profile, Proprietaire
from .models import Logement, Zone
from django import forms
from .models import RendezVous
from datetime import datetime, timedelta
import pytz
from django.forms import inlineformset_factory
from .models import Logement, ImageLogement, ContratGestion, Zone, Proprietaire

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'exemple@email.com'})
    )
    first_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Votre prénom'})
    )
    last_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Votre nom'})
    )
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Choisissez un nom d\'utilisateur'})
    )
    telephone = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'XX XX XX XX'})
    )
    adresse = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Votre adresse complète...'})
    )
    date_naissance = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    role = forms.ChoiceField(
        choices=Profile.ROLE_CHOICES,
        initial='client',
        widget=forms.RadioSelect(attrs={'class': 'd-none'})  # Caché, géré par JavaScript
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Votre mot de passe'})
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirmez votre mot de passe'})
    )
    
    # Champs supplémentaires pour les propriétaires
    numero_fiscal = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Votre numéro fiscal'})
    )
    rib = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Votre RIB'})
    )
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 
                 'password1', 'password2', 'telephone', 'adresse', 
                 'date_naissance', 'role', 'numero_fiscal', 'rib']
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        
        if commit:
            user.save()
            
            # Mettre à jour le profil
            profile = user.profile
            profile.role = self.cleaned_data.get('role', 'client')
            profile.telephone = self.cleaned_data.get('telephone')
            profile.adresse = self.cleaned_data.get('adresse')
            profile.date_naissance = self.cleaned_data.get('date_naissance')
            profile.save()
            
            # Si c'est un propriétaire, créer l'entrée Proprietaire
            if profile.role == 'proprietaire':
                Proprietaire.objects.create(
                    profile=profile,
                    numero_fiscal=self.cleaned_data.get('numero_fiscal', ''),
                    rib=self.cleaned_data.get('rib', '')
                )
        
        return user

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nom d\'utilisateur',
            'autocomplete': 'username'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Mot de passe',
            'autocomplete': 'current-password'
        })
    )

 

class SearchForm(forms.Form):
    """Formulaire de recherche pour le catalogue"""
    type_logement = forms.ChoiceField(
        choices=[('', 'Tous types')] + Logement.TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    zone = forms.ModelChoiceField(
        queryset=Zone.objects.all(),
        empty_label="Toutes zones",
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    surface_min = forms.DecimalField(
        required=False,
        min_value=0,
        max_value=1000,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Surface min (m²)'
        })
    )
    
    surface_max = forms.DecimalField(
        required=False,
        min_value=0,
        max_value=1000,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Surface max (m²)'
        })
    )
    
    prix_min = forms.DecimalField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Prix min (€)'
        })
    )
    
    prix_max = forms.DecimalField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Prix max (€)'
        })
    )
    
    order_by = forms.ChoiceField(
        choices=[
            ('date_creation', 'Plus récents'),
            ('surface', 'Surface croissante'),
            ('-surface', 'Surface décroissante'),
            ('prix', 'Prix croissant'),
            ('-prix', 'Prix décroissant'),
        ],
        required=False,
        initial='date_creation',
        widget=forms.Select(attrs={'class': 'form-select'})
    )


# Ajouter ces formulaires à forms.py
class UserUpdateForm(forms.ModelForm):
    """Formulaire pour mettre à jour l'utilisateur"""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }


class ProfileUpdateForm(forms.ModelForm):
    """Formulaire pour mettre à jour le profil"""
    class Meta:
        model = Profile
        fields = ['telephone', 'adresse', 'date_naissance', 'avatar']
        widgets = {
            'telephone': forms.TextInput(attrs={'class': 'form-control'}),
            'adresse': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'date_naissance': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'avatar': forms.FileInput(attrs={'class': 'form-control'}),
        }
 
class LogementForm(forms.ModelForm):
    """Formulaire pour ajouter/modifier un logement"""
    class Meta:
        model = Logement
        fields = [
            'type_logement', 'reference', 'adresse', 'surface',
            'zone', 'proprietaire', 'description', 'caution_fixe',
            'etat'
        ]
        widgets = {
            'adresse': forms.Textarea(attrs={'rows': 3}),
            'description': forms.Textarea(attrs={'rows': 3}),
            'reference': forms.TextInput(attrs={'class': 'form-control'}),
            'surface': forms.NumberInput(attrs={'class': 'form-control'}),
            'caution_fixe': forms.NumberInput(attrs={'class': 'form-control'}),
            'type_logement': forms.Select(attrs={'class': 'form-select'}),
            'zone': forms.Select(attrs={'class': 'form-select'}),
            'proprietaire': forms.Select(attrs={'class': 'form-select'}),
            'etat': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrer les propriétaires actifs
        self.fields['proprietaire'].queryset = Proprietaire.objects.filter(
            profile__user__is_active=True
        ).select_related('profile__user')

class ImageLogementForm(forms.ModelForm):
    """Formulaire pour les images d'un logement"""
    class Meta:
        model = ImageLogement
        fields = ['image', 'ordre']
        widgets = {
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'ordre': forms.NumberInput(attrs={'class': 'form-control'}),
        }

# Formset pour les images
ImageLogementFormSet = inlineformset_factory(
    Logement, ImageLogement,
    form=ImageLogementForm,
    extra=3,
    can_delete=True,
    min_num=0,
    validate_min=True
)

class ContratGestionForm(forms.ModelForm):
    """Formulaire pour les contrats de gestion"""
    class Meta:
        model = ContratGestion
        fields = [
            'logement', 'proprietaire', 'date_debut', 'date_fin',
            'montant_mensuel', 'etat', 'fichier_contrat', 'remarques'
        ]
        widgets = {
            'logement': forms.Select(attrs={'class': 'form-select'}),
            'proprietaire': forms.Select(attrs={'class': 'form-select'}),
            'date_debut': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'date_fin': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'montant_mensuel': forms.NumberInput(attrs={'class': 'form-control'}),
            'etat': forms.Select(attrs={'class': 'form-select'}),
            'fichier_contrat': forms.FileInput(attrs={'class': 'form-control'}),
            'remarques': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrer les logements sans contrat actif
        if self.instance and self.instance.pk:
            # En mode édition, on garde le logement actuel
            pass
        else:
            # En mode création, on ne montre que les logements sans contrat actif
            self.fields['logement'].queryset = Logement.objects.exclude(
                contrats_gestion__etat='en_cours'
            ).distinct()

class ZoneForm(forms.ModelForm):
    """Formulaire pour les zones"""
    class Meta:
        model = Zone
        fields = ['nom', 'forfait_agence', 'description']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'forfait_agence': forms.NumberInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }



        # gestion_immobiliere/forms.py (ajouter)

class ProprietaireForm(forms.ModelForm):
    """Formulaire pour modifier les informations d'un propriétaire"""
    class Meta:
        model = Proprietaire
        fields = ['numero_fiscal', 'rib']
        widgets = {
            'numero_fiscal': forms.TextInput(attrs={'class': 'form-control'}),
            'rib': forms.TextInput(attrs={'class': 'form-control'}),
        }

class ProfileForm(forms.ModelForm):
    """Formulaire pour modifier le profil utilisateur"""
    class Meta:
        model = Profile
        fields = ['telephone', 'adresse', 'date_naissance', 'avatar']
        widgets = {
            'telephone': forms.TextInput(attrs={'class': 'form-control'}),
            'adresse': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'date_naissance': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'avatar': forms.FileInput(attrs={'class': 'form-control'}),
        }

class UserForm(forms.ModelForm):
    """Formulaire pour modifier les informations de l'utilisateur"""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }









# gestion_immobiliere/forms.py (ajouter)

 

class RendezVousForm(forms.ModelForm):
    """Formulaire pour planifier un rendez-vous"""
    class Meta:
        model = RendezVous
        fields = ['date_rendez_vous', 'duree_estimee', 'lieu', 'contact_client', 'notes']
        widgets = {
            'date_rendez_vous': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local',
                    'class': 'form-control',
                    'min': datetime.now().strftime('%Y-%m-%dT%H:%M')
                }
            ),
            'duree_estimee': forms.Select(
                choices=[
                    (30, '30 minutes'),
                    (60, '1 heure'),
                    (90, '1 heure 30'),
                    (120, '2 heures'),
                ],
                attrs={'class': 'form-select'}
            ),
            'lieu': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_client': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        self.demande = kwargs.pop('demande', None)
        super().__init__(*args, **kwargs)
        
        if self.demande:
            # Pré-remplir le contact client
            self.fields['contact_client'].initial = self.demande.client.telephone
            
            # Pré-remplir le lieu (adresse du logement)
            self.fields['lieu'].initial = self.demande.logement.adresse
    
    def clean_date_rendez_vous(self):
        date_rendez_vous = self.cleaned_data['date_rendez_vous']
        
        # Vérifier que le rendez-vous est dans le futur
        if date_rendez_vous < datetime.now().replace(tzinfo=pytz.UTC):
            raise forms.ValidationError("Le rendez-vous doit être dans le futur.")
        
        # Vérifier que c'est en heure de bureau (9h-18h, du lundi au vendredi)
        if date_rendez_vous.weekday() >= 5:  # Samedi (5) ou Dimanche (6)
            raise forms.ValidationError("Les rendez-vous se prennent du lundi au vendredi.")
        
        if date_rendez_vous.hour < 9 or date_rendez_vous.hour >= 18:
            raise forms.ValidationError("Les rendez-vous se prennent entre 9h et 18h.")
        
        return date_rendez_vous
