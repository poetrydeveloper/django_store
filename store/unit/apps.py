from django.apps import AppConfig

class UnitConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'unit'
    verbose_name = 'Управление единицами товара'

    def ready(self):
        # Убедитесь, что нет прямого импорта моделей здесь
        pass