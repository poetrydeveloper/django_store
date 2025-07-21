# app sales\admin
from django.contrib import admin
from django.utils.html import format_html
from .models import Sale, SaleItem, SaleCancellation


class SaleItemInline(admin.TabularInline):
    """Позиции продажи в интерфейсе Sale"""
    model = SaleItem
    extra = 0
    readonly_fields = ('get_product_info', 'cancelled')
    fields = ('get_product_info', 'product_unit', 'actual_price', 'cancelled')

    def get_product_info(self, obj):
        return f"{obj.product_unit.product.name} (SN: {obj.product_unit.serial_number})"

    get_product_info.short_description = 'Товар'


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at', 'customer', 'sale_type', 'display_total', 'is_cancelled')
    list_filter = ('sale_type', 'created_at')
    search_fields = ('id', 'customer__name')
    inlines = (SaleItemInline,)
    readonly_fields = ('created_at', 'display_items')

    fieldsets = (
        (None, {
            'fields': ('created_at', 'customer', 'sale_type', 'request_item', 'total_amount', 'notes')
        }),
        ('Позиции', {
            'fields': ('display_items',),
            'classes': ('collapse',)
        }),
    )

    def display_total(self, obj):
        return f"{obj.total_amount} ₽"

    display_total.short_description = 'Сумма'

    def is_cancelled(self, obj):
        return hasattr(obj, 'salecancellation')

    is_cancelled.boolean = True
    is_cancelled.short_description = 'Отменена'

    def display_items(self, obj):
        items = obj.items.all()
        if not items:
            return "Нет позиций"

        html = "<ul>"
        for item in items:
            html += f"""
            <li>
                {item.product_unit.product.name} (SN: {item.product_unit.serial_number}) - 
                {item.actual_price} ₽ {'❌' if item.cancelled else '✅'}
            </li>
            """
        html += "</ul>"
        return format_html(html)

    display_items.short_description = 'Состав заказа'


class SaleCancellationInline(admin.StackedInline):
    """Отмена продажи прямо в интерфейсе Sale"""
    model = SaleCancellation
    extra = 0
    readonly_fields = ('created_at',)
    fields = ('created_at', 'reason', 'restored_units')

    def has_add_permission(self, request, obj=None):
        # Запрещаем создание отмены, если она уже существует
        return not (obj and hasattr(obj, 'salecancellation'))


@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'sale', 'get_product', 'actual_price', 'cancelled')
    list_filter = ('cancelled', 'sale__sale_type')
    search_fields = ('product_unit__serial_number', 'sale__id')

    def get_product(self, obj):
        return f"{obj.product_unit.product.name} (SN: {obj.product_unit.serial_number})"

    get_product.short_description = 'Товар'


@admin.register(SaleCancellation)
class SaleCancellationAdmin(admin.ModelAdmin):
    list_display = ('id', 'sale_link', 'created_at', 'reason_short')
    list_filter = ('created_at',)
    readonly_fields = ('created_at', 'sale_link')

    fieldsets = (
        (None, {
            'fields': ('sale_link', 'created_at', 'reason', 'restored_units')
        }),
    )

    def sale_link(self, obj):
        return format_html('<a href="/admin/sales/sale/{}/change/">{}</a>', obj.sale.id, obj.sale)

    sale_link.short_description = 'Продажа'

    def reason_short(self, obj):
        return obj.reason[:50] + '...' if len(obj.reason) > 50 else obj.reason

    reason_short.short_description = 'Причина'