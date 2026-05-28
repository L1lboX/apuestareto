from django.apps import AppConfig


class AdmindashboardappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'adminDashboardAPP'

    def ready(self):
        import adminDashboardAPP.signals

