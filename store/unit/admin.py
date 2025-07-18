from django.contrib import admin
from .models import ProductUnit

@admin.register(ProductUnit)
class ProductUnitAdmin(admin.ModelAdmin):
    list_display = ('product', 'serial_number', 'status', 'created_at')
    list_filter = ('status', 'product__category')
    search_fields = ('serial_number', 'product__name', 'product__code')
    readonly_fields = ('created_at',)
    fieldsets = (
        (None, {
            'fields': ('product', 'serial_number', 'status')
        }),
        ('Связи', {
            'fields': ('request_item', 'delivery_item', 'sale_item'),
            'classes': ('collapse',)
        }),
        ('Даты', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )