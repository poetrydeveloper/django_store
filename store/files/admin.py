# app files\admin
from django.contrib import admin
from django.utils.html import format_html
from .models import ProductImage

@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product_link', 'image_preview', 'code', 'is_main', 'created_short')
    list_filter = ('is_main', 'product__category')
    search_fields = ('product__name', 'product__code', 'code')
    list_editable = ('is_main',)
    readonly_fields = ('image_preview', 'created_short')
    fieldsets = (
        (None, {
            'fields': ('product', 'code', 'is_main')
        }),
        ('Изображение', {
            'fields': ('image', 'image_preview'),
        }),
        ('Даты', {
            'fields': ('created_short',),
            'classes': ('collapse',)
        }),
    )

    def product_link(self, obj):
        return format_html(
            '<a href="{}">{}</a>',
            f"/admin/goods/product/{obj.product.id}/change/",
            f"{obj.product.name} ({obj.product.code})"
        )
    product_link.short_description = 'Товар'
    product_link.admin_order_field = 'product'

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 100px; max-width: 100px; '
                'border: 1px solid #ddd; border-radius: 4px;"/>',
                obj.image.url
            )
        return "Нет изображения"
    image_preview.short_description = 'Превью'

    def created_short(self, obj):
        return obj.created_at.strftime('%d.%m.%Y %H:%M')
    created_short.short_description = 'Создано'