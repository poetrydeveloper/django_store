from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Customer,
    Supplier,
    Delivery,
    DeliveryItem,
    Request,
    RequestItem
)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'email', 'notes_short')
    search_fields = ('name', 'phone', 'email')
    list_filter = ('name',)
    list_per_page = 20

    def notes_short(self, obj):
        return obj.notes[:50] + '...' if obj.notes else '-'

    notes_short.short_description = 'Примечания (кратко)'


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'phone', 'notes_short')
    search_fields = ('name', 'contact_person', 'phone')
    list_filter = ('name',)
    list_per_page = 20

    def notes_short(self, obj):
        return obj.notes[:50] + '...' if obj.notes else '-'

    notes_short.short_description = 'Примечания (кратко)'


class DeliveryItemInline(admin.TabularInline):
    model = DeliveryItem
    extra = 1
    fields = ('product', 'quantity_received', 'price_per_unit', 'notes')
    readonly_fields = ('total_price',)

    def total_price(self, obj):
        return obj.quantity_received * obj.price_per_unit

    total_price.short_description = 'Сумма'


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ('id', 'supplier', 'delivery_date', 'total_amount')
    list_filter = ('supplier', 'delivery_date')
    search_fields = ('supplier__name', 'notes')
    date_hierarchy = 'delivery_date'
    inlines = [DeliveryItemInline]

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        # Обновляем общую сумму поставки
        total = sum(
            item.quantity_received * item.price_per_unit
            for item in form.instance.items.all()
        )
        form.instance.total_amount = total
        form.instance.save()


class RequestItemInline(admin.TabularInline):
    model = RequestItem
    extra = 1
    fields = (
        'product',
        'quantity_ordered',
        'price_per_unit',
        'is_customer_order',
        'customer'
    )
    readonly_fields = ('item_total',)

    def item_total(self, obj):
        return obj.quantity_ordered * obj.price_per_unit

    item_total.short_description = 'Сумма'


@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at', 'is_completed', 'notes_short')
    list_filter = ('is_completed', 'created_at')
    search_fields = ('notes',)
    date_hierarchy = 'created_at'
    inlines = [RequestItemInline]

    def notes_short(self, obj):
        return obj.notes[:50] + '...' if obj.notes else '-'

    notes_short.short_description = 'Примечания (кратко)'


@admin.register(DeliveryItem)
class DeliveryItemAdmin(admin.ModelAdmin):
    list_display = (
        'product',
        'delivery_link',
        'quantity_received',
        'price_per_unit',
        'total_price',
        'units_list'
    )
    list_filter = ('delivery__supplier', 'product')
    search_fields = ('product__name', 'delivery__id')
    filter_horizontal = ('received_units',)
    readonly_fields = ('total_price', 'units_list')
    fieldsets = (
        (None, {
            'fields': (
                'delivery',
                'product',
                ('quantity_received', 'price_per_unit', 'total_price')
            )
        }),
        ('Полученные единицы', {
            'fields': ('received_units', 'units_list')
        }),
        ('Дополнительно', {
            'fields': ('notes',),
            'classes': ('collapse',)
        })
    )

    def delivery_link(self, obj):
        return format_html(
            '<a href="/admin/warehouse/delivery/{}/change/">{}</a>',
            obj.delivery.id,
            f"Поставка #{obj.delivery.id}"
        )

    delivery_link.short_description = 'Поставка'
    delivery_link.admin_order_field = 'delivery'

    def total_price(self, obj):
        return obj.quantity_received * obj.price_per_unit

    total_price.short_description = 'Сумма'

    def units_list(self, obj):
        units = obj.received_units.all()
        if not units:
            return "-"
        return format_html("<br>".join(
            f'<a href="/admin/unit/productunit/{unit.id}/change/">{unit.serial_number}</a>'
            for unit in units
        ))

    units_list.short_description = 'Список серийных номеров'

    def save_model(self, request, obj, form, change):
        """Автоматическая привязка свободных юнитов товара"""
        super().save_model(request, obj, form, change)

        if not change:  # Только для новых записей
            available_units = obj.product.productunit_set.filter(
                status='in_request',
                delivery_item__isnull=True
            )[:obj.quantity_received]

            obj.received_units.set(available_units)

@admin.register(RequestItem)
class RequestItemAdmin(admin.ModelAdmin):
    list_display = (
        'product',
        'request_link',
        'quantity_ordered',
        'price_per_unit',
        'item_total',
        'is_customer_order',
        'customer'
    )
    list_filter = ('is_customer_order', 'product')
    search_fields = ('product__name', 'request__notes')

    def request_link(self, obj):
        return format_html(
            '<a href="/admin/warehouse/request/{}/change/">{}</a>',
            obj.request.id,
            f"Заявка #{obj.request.id}"
        )

    request_link.short_description = 'Заявка'

    def item_total(self, obj):
        return obj.quantity_ordered * obj.price_per_unit

    item_total.short_description = 'Сумма'