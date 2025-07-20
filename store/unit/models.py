# app unit/models
from django.db import models
from django.core.exceptions import ValidationError
import random
from datetime import datetime




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

    @staticmethod
    def generate_serial_number(product):
        """Генерация гарантированно уникального серийного номера"""
        max_attempts = 100
        base_prefix = f"RF-{product.id}-"

        for attempt in range(max_attempts):
            timestamp = datetime.now().strftime("%d%m:%H%M%S")
            # Добавляем микросекунды и attempt для уникальности
            unique_part = f"{datetime.now().microsecond:06d}{attempt:02d}"[:8]
            full_serial = f"{base_prefix}{timestamp}-{unique_part}"

            if not ProductUnit.objects.filter(serial_number=full_serial).exists():
                return full_serial

        raise ValidationError(
            f"Не удалось сгенерировать уникальный номер после {max_attempts} попыток"
        )

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
    sale_date = models.DateField(
        'Дата продажи',
        null=True,
        blank=True,
        help_text='Фактическая дата продажи (если товар продан)'
    )
    sale_price = models.DecimalField(
        'Цена продажи',
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Цена продажи (если товар продан)'
    )
    class Meta:
        verbose_name = 'Единица товара'
        verbose_name_plural = 'Единицы товаров'
        indexes = [
            models.Index(fields=['status', 'product']),
            models.Index(fields=['sale_date']),
        ]

    def safe_mark_as_sold(self, sale_date=None, sale_price=None):
        """
        Безопасное изменение статуса на 'sold' без обязательных параметров
        Новый метод - можно вызывать даже без указания даты/цены
        """
        self.status = 'sold'
        if sale_date:
            self.sale_date = sale_date
        if sale_price:
            self.sale_price = sale_price
        self.save()
        return self

    def get_purchase_price(self):
        """Возвращает цену закупки (из DeliveryItem)"""
        if self.delivery_item:
            return self.delivery_item.price_per_unit
        return None

    def __str__(self):
        base_str = f"{self.serial_number} ({self.get_status_display()})"
        if self.status == 'sold' and self.sale_date:
            return f"{base_str} - {self.sale_date}"
        return base_str

    def save(self, *args, **kwargs):
        if not self.serial_number:
            if not self.product:
                raise ValidationError("Нельзя создать единицу товара без указания товара")
            self.serial_number = ProductUnit.generate_serial_number(self.product)
        super().save(*args, **kwargs)