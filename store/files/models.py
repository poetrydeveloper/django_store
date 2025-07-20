# app files/models
from django.db import models
from django.conf import settings
import os

def product_image_upload_path(instance, filename):
    """Генерирует путь для сохранения изображений товаров"""
    return os.path.join('products', instance.product.code, filename)

class ProductImage(models.Model):
    """
    Изображение товара
    """
    product = models.ForeignKey(
        'goods.Product',
        on_delete=models.CASCADE,
        related_name='product_images',
        verbose_name='Товар'
    )
    image = models.ImageField(
        upload_to=product_image_upload_path,
        verbose_name='Изображение'
    )
    code = models.CharField(
        max_length=100,
        verbose_name='Код изображения',
        help_text='Должен совпадать с кодом товара'
    )
    is_main = models.BooleanField(
        default=False,
        verbose_name='Главное изображение'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )

    class Meta:
        app_label = 'files'
        verbose_name = 'Изображение товара'
        verbose_name_plural = 'Изображения товаров'
        ordering = ['-is_main', 'created_at']

    def __str__(self):
        return f"Изображение {self.id} для товара {self.product.code}"

    def save(self, *args, **kwargs):
        # Автоматически устанавливаем code равным коду товара
        if not self.code:
            self.code = self.product.code
        super().save(*args, **kwargs)