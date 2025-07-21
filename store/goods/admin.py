# app goods\admin
from django.contrib import admin
from django.utils.html import format_html
from django.utils.text import slugify
from .models import Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent_link', 'slug_display', 'product_count')
    list_filter = ('parent',)
    search_fields = ('name',)
    fields = ('name', 'parent')  # slug исключен из формы

    # Метод для отображения родительской категории как ссылки
    def parent_link(self, obj):
        if obj.parent:
            return format_html('<a href="../{}/">{}</a>', obj.parent.id, obj.parent.name)
        return "-"

    parent_link.short_description = 'Родительская категория'

    # Метод для красивого отображения slug
    def slug_display(self, obj):
        return obj.slug or "Не сгенерирован"

    slug_display.short_description = 'ЧПУ'

    # Метод для подсчета товаров в категории
    def product_count(self, obj):
        return obj.products.count()

    product_count.short_description = 'Товаров'

    # Метод сохранения модели - ДОЛЖЕН БЫТЬ ВНУТРИ КЛАССА CategoryAdmin
    def save_model(self, request, obj, form, change):
        """
        Автоматическая генерация slug при сохранении.
        Этот метод должен быть внутри класса CategoryAdmin!
        """
        if not obj.slug:
            base_slug = slugify(obj.name)
            unique_slug = base_slug
            counter = 1

            # Проверяем уникальность slug
            while Category.objects.filter(slug=unique_slug).exists():
                unique_slug = f"{base_slug}-{counter}"
                counter += 1

            obj.slug = unique_slug
        super().save_model(request, obj, form, change)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'category', 'main_image_preview', 'images_count')
    readonly_fields = ('main_image_preview', 'images_list')
    fieldsets = (
        ('Основная информация', {
            'fields': ('code', 'name', 'category')
        }),
        ('Описание', {
            'fields': ('description',),
            'classes': ('collapse',)
        }),
        ('Изображения', {
            'fields': ('main_image_preview', 'images_list'),
        }),
    )

    def main_image_preview(self, obj):
        main_image = obj.product_images.filter(is_main=True).first()
        if main_image:
            return format_html(
                '<img src="{}" style="max-height: 100px; max-width: 100px; '
                'border: 1px solid #ddd; border-radius: 4px;"/>',
                main_image.image.url
            )
        return "Нет главного изображения"
    main_image_preview.short_description = 'Главное изображение'

    def images_list(self, obj):
        images = obj.product_images.all().order_by('-is_main')
        if images:
            return format_html(' '.join(
                f'<a href="/admin/files/productimage/{img.id}/change/">'
                f'<img src="{img.image.url}" style="max-height: 50px; margin: 5px; '
                'border: 1px solid #ddd; border-radius: 3px;"/></a>'
                for img in images
            ))
        return "Нет изображений"
    images_list.short_description = 'Все изображения'

    def images_count(self, obj):
        return obj.product_images.count()
    images_count.short_description = 'Изобр.'