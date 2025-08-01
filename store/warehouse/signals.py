# app warehouse/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.apps import apps

# Объявляем модели один раз
ProductUnit = apps.get_model('unit', 'ProductUnit')
RequestItem = apps.get_model('warehouse', 'RequestItem')

@receiver(post_save, sender=RequestItem)
def create_product_units(sender, instance, created, **kwargs):
    if sender.__name__ == 'RequestItem' and created:
        from django.utils import timezone
        base_date = timezone.now().strftime("%Y%m%d%H%M")

        for i in range(1, instance.quantity_ordered + 1):
            serial = f"{instance.product.code}-{base_date}-{i:03d}"
            ProductUnit.objects.create(
                product=instance.product,
                request_item=instance,
                serial_number=serial,
                status='in_request'
            )