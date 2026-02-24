# Plan de Correction - Projet Gestion Immobilière

## Tâches à effectuer

### 1. Corriger signals.py ✅
- [x] Modifier le signal `create_user_profile` pour ne pas créer de Profile automatiquement
- [x] Le formulaire `UserRegistrationForm` gère déjà la création du Profile avec les champs requis

### 2. Ajouter les vues dashboard dans views.py ✅
- [x] Créer `gestionnaire_dashboard`
- [x] Créer `proprietaire_dashboard`
- [x] Créer `rl_dashboard` (Responsable Location)
- [x] Créer `rf_dashboard` (Responsable Financier)
- [x] Créer `client_dashboard`

### 3. Créer requirements.txt ✅
- [x] Ajouter les dépendances du projet

### 4. URLs des dashboards ✅
- [x] Ajouter les routes URL pour chaque dashboard

## Notes
- Le signal de création automatique du Profile a été commenté car le modèle Profile 
  nécessite les champs 'telephone' et 'adresse' qui ne sont pas disponibles lors 
  de la création automatique du User via le signal post_save.
- Le formulaire `UserRegistrationForm` dans forms.py crée correctement le Profile 
  avec tous les champs requis.

## Prochaine étape
Pour les utilisateurs créés via l'admin Django, il faudra ajouter le Profile manuellement
ou créer une méthode pour pré-remplir les champs requis.










 1) seeder factorie
 2)request (validation)->old()
 3)Upload file pdf word  Image 
 4)authentification (breeze)moi
 5)validation message clair 
 6)afficher les messages en cas ajout et update
 
