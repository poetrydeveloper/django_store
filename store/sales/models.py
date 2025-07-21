# app sales/models
from django.db import models
from unit.models import ProductUnit


class Sale(models.Model):
    """Документ продажи"""
    SALE_TYPES = [
        ('regular', 'Обычная продажа'),
        ('order', 'Заказная позиция'),  # Связь с RequestItem
    ]

    created_at = models.DateTimeField('Дата продажи', auto_now_add=True)
    customer = models.ForeignKey(
        'warehouse.Customer',  # Строковая ссылка
        on_delete=models.PROTECT,
        verbose_name='Клиент',
        null=True,
        blank=True
    )
    sale_type = models.CharField(
        'Тип продажи',
        max_length=10,
        choices=SALE_TYPES,
        default='regular'
    )
    request_item = models.ForeignKey(
        'warehouse.RequestItem',  # Строковая ссылка
        on_delete=models.SET_NULL,
        verbose_name='Заказная позиция',
        null=True,
        blank=True
    )
    total_amount = models.DecimalField(
        'Сумма продажи',
        max_digits=12,
        decimal_places=2,
        default=0
    )
    notes = models.TextField('Примечания', blank=True)

    class Meta:
        verbose_name = 'Продажа'
        verbose_name_plural = 'Продажи'
        ordering = ['-created_at']

    def __str__(self):
        return f"Продажа #{self.id}"

    def update_total(self):
        """Пересчёт суммы продажи"""
        self.total_amount = sum(item.actual_price for item in self.items.all())
        self.save()

class SaleItem(models.Model):
    """Конкретная проданная единица товара"""
    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Продажа'
    )
    product_unit = models.ForeignKey(
        'unit.ProductUnit',
        on_delete=models.PROTECT,
        verbose_name='Единица товара'
    )
    actual_price = models.DecimalField(
        'Фактическая цена',
        max_digits=10,
        decimal_places=2
    )
    cancelled = models.BooleanField('Отменена', default=False)

    class Meta:
        verbose_name = 'Позиция продажи'
        verbose_name_plural = 'Позиции продаж'

    def __str__(self):
        return f"{self.product_unit.product.name} (Цена: {self.actual_price})"

    def save(self, *args, **kwargs):
        if not self.cancelled:
            if self.product_unit.status not in ['in_store']:
                raise ValidationError("Нельзя продать товар с текущим статусом")
            self.product_unit.status = 'sold'
            self.product_unit.save()
        super().save(*args, **kwargs)

class SaleCancellation(models.Model):
    """Документ отмены продажи"""
    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        verbose_name='Продажа'
    )
    created_at = models.DateTimeField('Дата отмены', auto_now_add=True)
    reason = models.TextField('Причина отмены')
    restored_units = models.ManyToManyField(
        ProductUnit,
        verbose_name='Возвращённые единицы'
    )

    class Meta:
        verbose_name = 'Отмена продажи'
        verbose_name_plural = 'Отмены продаж'

    def __str__(self):
        return f"Отмена продажи #{self.sale.id}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Всегда возвращаем товары в статус 'in_store'
        for unit in self.restored_units.all():
            unit.status = 'in_store'
            unit.save()