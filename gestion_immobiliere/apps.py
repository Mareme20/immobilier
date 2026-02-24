# gestion_immobiliere/apps.py
from django.apps import AppConfig

class GestionImmobiliereConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'gestion_immobiliere'
    
    def ready(self):
        """Importer les signaux quand l'app est prête"""
        # Cette importation est cruciale pour que les signaux fonctionnent
        import gestion_immobiliere.signals