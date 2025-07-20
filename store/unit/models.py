# app unit/models
from django.db import models


class ProductUnit(models.Model):
    STATUS_CHOICES = [
        ('in_request', 'В заявке'),
        ('in_request_cancelled', 'В заявке - отменен'),
        ('in_store', 'В магазине'),
        ('sold', 'Продан'),
        ('broken', 'Сломан'),
        ('lost', 'Утерян'),
        ('transferred', 'Передан'),
    ]
    serial_number = models.CharField(
        'Серийный номер',
        max_length=100,
        unique=True
    )
    product = models.ForeignKey(
        'goods.Product',
        on_delete=models.PROTECT,
        verbose_name='Товар'
    )
    request_item = models.ForeignKey(
        'warehouse.RequestItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Позиция заявки'
    )
    delivery_item = models.ForeignKey(
        'warehouse.DeliveryItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Позиция поставки'
    )
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=STATUS_CHOICES,
        default='in_request'
    )
    created_at = models.DateTimeField(
        'Дата создания',
        auto_now_add=True
    )

    class Meta:
        verbose_name = 'Единица товара'
        verbose_name_plural = 'Единицы товаров'

    def __str__(self):
        return f"{self.serial_number} ({self.get_status_display()})"
