# app goods/models
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class Category(models.Model):
    """
    Категория товаров
    """
    name = models.CharField('Название', max_length=255)
    slug = models.SlugField(unique=True, blank=True)

    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        related_name='children',
        verbose_name='Родительская категория',
        blank=True,
        null=True
    )

    class Meta:
        app_label = 'goods'
        verbose_name = 'Категория товара'
        verbose_name_plural = 'Категории товаров'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Product(models.Model):
    """
    Товар
    """
    code = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Код товара'
    )
    name = models.CharField(
        max_length=255,
        verbose_name='Название товара'
    )
    description = models.TextField(
        verbose_name='Описание товара',
        blank=True,
        null=True
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        related_name='products',
        verbose_name='Категория',
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата последнего обновления'
    )

    class Meta:
        app_label = 'goods'
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"

    def get_availability_status(self) -> str:
        """
        Возвращает статус доступности товара
        (заглушка - нужно реализовать логику)
        """
        return "В наличии"

    @property
    def images(self):
        """Возвращает все изображения товара"""
        return self.product_images.all()