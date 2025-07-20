# app warehouse/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import F, Sum, Q
from .models import Delivery, DeliveryItem, Request, RequestItem, Supplier, Customer
from unit.models import ProductUnit
from django import forms

# ========== БАЗОВЫЕ НАСТРОЙКИ ==========
class BaseAdmin(admin.ModelAdmin):
    save_on_top = True
    list_per_page = 50

# ========== ПОСТАВЩИКИ ==========
@admin.register(Supplier)
class SupplierAdmin(BaseAdmin):
    list_display = ('name', 'contact_person', 'phone', 'notes_short')
    search_fields = ('name', 'contact_person', 'phone')

    def notes_short(self, obj):
        return obj.notes[:50] + '...' if obj.notes else '-'
    notes_short.short_description = 'Примечания'

# ========== КЛИЕНТЫ ==========
@admin.register(Customer)
class CustomerAdmin(BaseAdmin):
    list_display = ('name', 'phone', 'email', 'notes_short')
    search_fields = ('name', 'phone', 'email')

    def notes_short(self, obj):
        return obj.notes[:50] + '...' if obj.notes else '-'
    notes_short.short_description = 'Примечания'

# ========== ФОРМА ДЛЯ ПОЗИЦИЙ ПОСТАВКИ ==========
class DeliveryItemForm(forms.ModelForm):
    class Meta:
        model = DeliveryItem
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'request_item' in self.fields:
            self.fields['request_item'].label_from_instance = lambda obj: format_html("Z-{}", f"{obj.id:03d}")

        # Фильтрация для received_units
        if self.instance and self.instance.pk:
            self.fields['received_units'].queryset = ProductUnit.objects.filter(
                Q(status='in_request') | Q(pk__in=self.instance.received_units.all())
            )
        else:
            self.fields['received_units'].queryset = ProductUnit.objects.filter(status='in_request')

        # Форматирование отображения заявок
        if 'request_item' in self.fields:
            self.fields['request_item'].label_from_instance = lambda obj: f"Z-{obj.id:03d}"

# ========== INLINE ДЛЯ ПОЗИЦИЙ ПОСТАВКИ ==========
class DeliveryItemInline(admin.TabularInline):
    form = DeliveryItemForm
    model = DeliveryItem
    extra = 1
    fields = (
        'product',
        'request_item',
        'quantity_received',
        'price_per_unit',
        'received_units',
        'total_price',
        'completion_status'
    )
    readonly_fields = ('total_price', 'completion_status')
    filter_horizontal = ('received_units',)

    def total_price(self, obj):
        if obj.quantity_received and obj.price_per_unit:
            return f"{obj.quantity_received * obj.price_per_unit:.2f} ₽"
        return "—"
    total_price.short_description = 'Сумма'

    def completion_status(self, obj):
        if obj.request_item:
            return f"{obj.received_units.count()} из {obj.request_item.quantity_ordered}"
        return "—"
    completion_status.short_description = 'Выполнено'

# ========== ПОСТАВКИ ==========
@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    inlines = [DeliveryItemInline]
    list_display = (
        'id',
        'supplier_link',
        'delivery_date',
        'total_amount_display',
        'status_badge',
        'items_count'
    )
    list_filter = ('supplier', 'delivery_date')
    search_fields = ('supplier__name', 'notes')
    date_hierarchy = 'delivery_date'
    readonly_fields = ('total_amount_display',)

    def supplier_link(self, obj):
        return format_html(
            '<a href="/admin/warehouse/supplier/{}/change/">{}</a>',
            obj.supplier.id,
            obj.supplier.name
        )
    supplier_link.short_description = 'Поставщик'

    def total_amount_display(self, obj):
        return f"{obj.total_amount:.2f} ₽" if obj.total_amount else "—"
    total_amount_display.short_description = 'Общая сумма'

    def status_badge(self, obj):
        color = 'green' if obj.total_amount > 0 else 'gray'
        text = 'Завершена' if obj.total_amount > 0 else 'В процессе'
        return format_html(
            '<span style="color:white;background:{};padding:2px 6px;border-radius:3px">{}</span>',
            color, text
        )
    status_badge.short_description = 'Статус'

    def items_count(self, obj):
        return obj.items.count()
    items_count.short_description = 'Позиций'

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        total = sum(
            item.quantity_received * item.price_per_unit
            for item in form.instance.items.all()
            if item.quantity_received and item.price_per_unit
        )
        form.instance.total_amount = total
        form.instance.save()

# ========== ПОЗИЦИИ ЗАЯВКИ (INLINE) ==========
class RequestItemInline(admin.TabularInline):
    model = RequestItem
    extra = 1
    fields = (
        'product',
        'supplier',
        'quantity_ordered',
        'price_per_unit',
        'is_customer_order',
        'customer'
    )
    raw_id_fields = ('customer',)

# ========== ЗАЯВКИ ==========
@admin.register(Request)
class RequestAdmin(BaseAdmin):
    inlines = [RequestItemInline]
    list_display = (
        'id_formatted',
        'created_at',
        'is_completed',
        'total_sum',
        'items_count'
    )
    list_filter = ('is_completed', 'created_at')
    search_fields = ('id', 'items__product__name')
    date_hierarchy = 'created_at'

    def id_formatted(self, obj):
        return format_html("<b>Z-{}</b>", f"{obj.id:03d}")  # Форматируем число до передачи в format_html

    id_formatted.short_description = 'Номер'
    id_formatted.admin_order_field = 'id'

    def total_sum(self, obj):
        result = obj.items.aggregate(
            total=Sum(F('quantity_ordered') * F('price_per_unit'))
        )['total']
        return f"{result:.2f} ₽" if result else "—"
    total_sum.short_description = 'Общая сумма'

    def items_count(self, obj):
        return obj.items.count()
    items_count.short_description = 'Позиций'