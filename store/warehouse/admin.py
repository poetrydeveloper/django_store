# app warehouse/admin
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
    list_display = ('request_id_formatted', 'created_at', 'is_completed', 'notes_short', 'items_count')
    list_filter = ('is_completed', 'created_at')
    search_fields = ('notes', 'id')
    date_hierarchy = 'created_at'
    inlines = [RequestItemInline]

    def request_id_formatted(self, obj):
        """
        Форматирует номер заявки в виде Z-001 с датой
        Защита от всех возможных ошибок форматирования
        """
        try:
            # Базовые проверки
            if not obj or not hasattr(obj, 'id'):
                return "Новая заявка"

            # Форматируем ID с ведущими нулями
            request_id = f"Z-{obj.id:03d}"

            # Форматируем дату с проверкой
            date_str = obj.created_at.strftime("%d.%m.%Y %H:%M") if obj.created_at else "без даты"

            return format_html(
                '<b>{}</b> <span style="color: #666;">{}</span>',
                request_id,
                date_str
            )
        except Exception:
            # Возвращаем "безопасный" вариант при любых ошибках
            return format_html('<span>Заявка #{}</span>', obj.id if obj and hasattr(obj, 'id') else '?')

    request_id_formatted.short_description = 'Номер заявки'
    request_id_formatted.admin_order_field = 'id'

    def notes_short(self, obj):
        """Сокращенное отображение примечаний"""
        if not obj.notes:
            return "-"
        return format_html(
            '<span title="{}">{}...</span>',
            obj.notes,
            obj.notes[:50]
        )

    notes_short.short_description = 'Примечания'

    def items_count(self, obj):
        """Подсчет товаров в заявке с цветовой индикацией"""
        try:
            count = obj.items.count() if obj and hasattr(obj, 'items') else 0
            color = 'green' if count > 0 else 'gray'
            text = str(count) if count > 0 else 'нет товаров'
            return format_html('<span style="color: {};">{}</span>', color, text)
        except Exception:
            return format_html('<span style="color: red;">ошибка</span>')

    items_count.short_description = 'Товаров'

    def get_queryset(self, request):
        """Оптимизация запросов к БД"""
        return super().get_queryset(request).prefetch_related('items')

    def render_change_form(self, request, context, *args, **kwargs):
        """Настройка отображения формы редактирования"""
        if not kwargs.get('obj'):
            # Для новой заявки скрываем лишние кнопки
            context.update({
                'show_save_and_add_another': False,
                'show_save_and_continue': False
            })
        return super().render_change_form(request, context, *args, **kwargs)

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
        super().save_model(request, obj, form, change)
        if not change:
            available_units = obj.product.productunit_set.filter(
                status='in_request',
                delivery_item__isnull=True
            )[:obj.quantity_received]
            obj.received_units.set(available_units)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        for item in form.instance.items.all():
            item.save()

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
            f"Z-{obj.request.id:03d}"
        )
    request_link.short_description = 'Заявка'

    def item_total(self, obj):
        return obj.quantity_ordered * obj.price_per_unit
    item_total.short_description = 'Сумма'