# app warehouse/models
from django.db import models
from unit.models import ProductUnit
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError

class Customer(models.Model):
    """Клиент (покупатель)"""
    name = models.CharField('Наименование', max_length=255)
    phone = models.CharField('Телефон', max_length=20)
    email = models.EmailField('Email', blank=True)
    notes = models.TextField('Примечания', blank=True)

    class Meta:
        verbose_name = 'Клиент'
        verbose_name_plural = 'Клиенты'
        ordering = ['name']

    def __str__(self):
        return self.name


class Supplier(models.Model):
    """Поставщик"""
    name = models.CharField('Наименование', max_length=255)
    contact_person = models.CharField('Контактное лицо', max_length=255)
    phone = models.CharField('Телефон', max_length=20)
    notes = models.TextField('Примечания', blank=True)

    class Meta:
        verbose_name = 'Поставщик'
        verbose_name_plural = 'Поставщики'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.contact_person})"


class Delivery(models.Model):
    """Поставка (заголовок)"""
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        verbose_name='Поставщик'
    )
    delivery_date = models.DateField('Дата поставки')
    total_amount = models.DecimalField(
        'Сумма поставки',
        max_digits=12,
        decimal_places=2,
        default=0
    )
    notes = models.TextField('Примечания', blank=True)

    class Meta:
        verbose_name = 'Поставка'
        verbose_name_plural = 'Поставки'
        ordering = ['-delivery_date']

    def __str__(self):
        return f"Поставка #{self.id} от {self.delivery_date}"


class DeliveryItem(models.Model):
    delivery = models.ForeignKey(
        'warehouse.Delivery',
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Поставка'
    )
    product = models.ForeignKey(
        'goods.Product',
        on_delete=models.PROTECT,
        verbose_name='Товар'
    )
    quantity_received = models.PositiveIntegerField(
        'Количество получено',
        validators=[MinValueValidator(1)],
        default=1
    )
    price_per_unit = models.DecimalField(
        'Цена за единицу',
        max_digits=10,
        decimal_places=2
    )
    request_item = models.ForeignKey(
        'warehouse.RequestItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='delivery_items',
        verbose_name='Связанная заявка'
    )
    received_units = models.ManyToManyField(
        'unit.ProductUnit',
        related_name='delivery_items_received',  # Уникальное имя для обратной связи
        verbose_name='Полученные единицы',
        blank=True
    )

    class Meta:
        verbose_name = 'Позиция поставки'
        verbose_name_plural = 'Позиции поставок'
        ordering = ['delivery', 'product']

    def __str__(self):
        return f"{self.product.name} x {self.quantity_received} (Поставка #{self.delivery.id})"

    def clean(self):
        """Валидация данных перед сохранением"""
        if self.quantity_received is None:
            raise ValidationError({'quantity_received': 'Укажите количество'})
        if self.price_per_unit is None:
            raise ValidationError({'price_per_unit': 'Укажите цену'})
        if self.quantity_received <= 0:
            raise ValidationError({'quantity_received': 'Количество должно быть положительным'})

    def save(self, *args, **kwargs):
        """Автоматическое обновление статусов ProductUnit при сохранении"""
        super().save(*args, **kwargs)

        # Обновляем статус всех привязанных единиц
        for unit in self.received_units.all():
            unit.status = 'in_delivery'
            unit.delivery_item = self
            unit.save()

    @property
    def total_price(self):
        """Вычисляемая общая сумма"""
        if self.quantity_received and self.price_per_unit:
            return self.quantity_received * self.price_per_unit
        return None

class Request(models.Model):
    """Заявка (заголовок)"""
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    is_completed = models.BooleanField('Выполнена', default=False)
    notes = models.TextField('Примечания', blank=True)

    class Meta:
        verbose_name = 'Заявка'
        verbose_name_plural = 'Заявки'
        ordering = ['-created_at']

    def __str__(self):
        return f"Заявка #{self.id}"


class RequestItem(models.Model):
    """Позиция заявки"""
    request = models.ForeignKey(
        Request,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Заявка'
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    quantity_received = models.PositiveIntegerField(default=0)

    product = models.ForeignKey(
        'goods.Product',
        on_delete=models.PROTECT,
        verbose_name='Товар'
    )
    quantity_ordered = models.PositiveIntegerField(
        'Заказанное количество',
        validators=[MinValueValidator(1)]
    )
    price_per_unit = models.DecimalField(
        'Цена за единицу',
        max_digits=10,
        decimal_places=2
    )
    is_customer_order = models.BooleanField('Заказ клиента', default=False)
    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Клиент'
    )

    class Meta:
        verbose_name = 'Позиция заявки'
        verbose_name_plural = 'Позиции заявок'

    def save(self, *args, **kwargs):
        # Сначала сохраняем объект
        super().save(*args, **kwargs)

        # Если это заказ клиента и нужно создать единицы товара
        if self.is_customer_order and not self.product.productunit_set.exists():
            for i in range(self.quantity_ordered):
                ProductUnit.objects.create(
                    product=self.product,
                    serial_number=f"{self.product.code}-{i + 1:03d}",  # Генерация серийного номера
                    status='in_request',
                    request_item=self
                )

    def __str__(self):
        return f"{self.product.name} x {self.quantity_ordered}"