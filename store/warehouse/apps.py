from django.apps import AppConfig

class WarehouseConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'warehouse'

    def ready(self):
        # Просто импортируем модуль сигналов
        import warehouse.signals