# app unit/admin
from django.contrib import admin
from .models import ProductUnit
from django.utils.html import format_html

@admin.register(ProductUnit)
class ProductUnitAdmin(admin.ModelAdmin):
    # ===== 1. ОБНОВЛЕННЫЕ НАСТРОЙКИ ОТОБРАЖЕНИЯ =====
    list_display = (
        'product_link',
        'serial_number',
        'status_badge',
        'created_at',
        'sale_info',  # Новое поле вместо related_links
        'warehouse_links'  # Переименовано из related_links
    )
    list_filter = ('status', 'product__category', 'created_at')
    search_fields = ('serial_number', 'product__name', 'product__code')
    readonly_fields = ('created_at', 'sale_info_detailed')  # Добавлено новое поле
    list_select_related = ('product', 'request_item', 'delivery_item')

    # ===== 2. ОБНОВЛЕННЫЙ FIELDSETS (удален sale_item) =====
    fieldsets = (
        (None, {
            'fields': ('product', 'serial_number', 'status')
        }),
        ('Складские данные', {  # Переименовано из "Связи"
            'fields': ('request_item', 'delivery_item'),
            'classes': ('collapse',)
        }),
        ('Данные о продаже', {  # Новый раздел
            'fields': ('sale_date', 'sale_price', 'sale_info_detailed'),
            'classes': ('collapse',)
        }),
        ('Даты', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    # ===== 3. СУЩЕСТВУЮЩИЕ МЕТОДЫ (без изменений) =====
    def product_link(self, obj):
        return format_html(
            '<a href="/admin/goods/product/{}/change/">{}</a>',
            obj.product.id,
            obj.product.name
        )
    product_link.short_description = 'Товар'
    product_link.admin_order_field = 'product'

    def status_badge(self, obj):
        status_colors = {
            'in_request': 'blue',
            'in_store': 'green',
            'sold': 'purple',
            'broken': 'red',
            'lost': 'orange'
        }
        return format_html(
            '<span style="color: white; background-color: {}; padding: 2px 6px; border-radius: 10px;">{}</span>',
            status_colors.get(obj.status, 'gray'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Статус'

    # ===== 4. НОВЫЕ/ИЗМЕНЕННЫЕ МЕТОДЫ =====
    def sale_info(self, obj):
        """Новый метод для отображения информации о продаже"""
        if obj.status == 'sold':
            date = obj.sale_date.strftime("%d.%m.%Y") if obj.sale_date else "дата не указана"
            price = f"{obj.sale_price} ₽" if obj.sale_price else "цена не указана"
            return format_html(
                '<span style="color: green;">Продано: {} за {}</span>',
                date,
                price
            )
        return format_html('<span style="color: gray;">—</span>')
    sale_info.short_description = 'Продажа'

    def sale_info_detailed(self, obj):
        """Детальная информация о продаже (только для чтения)"""
        if obj.status == 'sold':
            return self.sale_info(obj)
        return "Товар не продан"
    sale_info_detailed.short_description = 'Информация о продаже'

    def warehouse_links(self, obj):
        """Переименованный метод (бывший related_links) без sale_item"""
        links = []
        if obj.request_item:
            links.append(f'<a href="/admin/warehouse/requestitem/{obj.request_item.id}/change/">Заявка</a>')
        if obj.delivery_item:
            links.append(f'<a href="/admin/warehouse/deliveryitem/{obj.delivery_item.id}/change/">Поставка</a>')
        return format_html(' | '.join(links)) if links else '-'
    warehouse_links.short_description = 'Складские связи'