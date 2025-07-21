# app warehouse/admin.py
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.utils.html import format_html
from django.db.models import F, Sum, Q
from .models import Delivery, DeliveryItem, Request, RequestItem, Supplier, Customer
from unit.models import ProductUnit
from django import forms
from django.contrib import messages


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

    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get('product')
        quantity_received = cleaned_data.get('quantity_received', 0)

        # Добавлена проверка на корректность quantity_received
        if not quantity_received or quantity_received <= 0:
            raise forms.ValidationError("Укажите положительное количество")

        if product and quantity_received:
            try:
                for _ in range(quantity_received):
                    ProductUnit.generate_serial_number(product)
            except ValidationError as e:
                raise forms.ValidationError(
                    f"Ошибка генерации серийных номеров: {str(e)}"
                )
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        if commit and instance.product and instance.quantity_received:
            units = []
            error = None
            for _ in range(instance.quantity_received):
                try:
                    unit = ProductUnit(
                        product=instance.product,
                        status='in_stock',
                        request_item=instance.request_item,
                        delivery_item=instance
                    )
                    unit.save()
                    units.append(unit)
                except ValidationError as e:
                    error = e
                    continue

            if len(units) < instance.quantity_received:
                raise forms.ValidationError(
                    f"Удалось создать только {len(units)} из {instance.quantity_received} единиц товара. "
                    f"Причина: {str(error)}" if error else "Неизвестная ошибка"
                )

            instance.received_units.set(units)

        if commit:
            instance.save()
        return instance


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
        try:
            super().save_related(request, form, formsets, change)
            total = sum(
                item.quantity_received * item.price_per_unit
                for item in form.instance.items.all()
                if item.quantity_received and item.price_per_unit
            )
            form.instance.total_amount = total
            form.instance.save()
        except Exception as e:
            messages.error(request, f"Ошибка сохранения связанных данных: {str(e)}")
            raise

    def save_model(self, request, obj, form, change):
        try:
            super().save_model(request, obj, form, change)
        except Exception as e:
            messages.error(request, f"Ошибка сохранения поставки: {str(e)}")
            raise


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
        'completion_status',
        'total_sum',
        'items_count'
    )
    list_filter = ('is_completed', 'created_at')
    search_fields = ('id', 'items__product__name')
    date_hierarchy = 'created_at'

    def id_formatted(self, obj):
        return format_html("<b>Z-{}</b>", f"{obj.id:03d}")

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

    def completion_status(self, obj):
        items_data = obj.items.aggregate(
            total_ordered=Sum('quantity_ordered'),
            total_received=Sum('delivery_items__quantity_received')
        )

        total_ordered = items_data['total_ordered'] or 0
        total_received = items_data['total_received'] or 0

        if total_ordered == 0:
            return "Нет данных"

        if total_received >= total_ordered:
            return format_html(
                '<span style="color: green;">✓ Полностью поставлено</span>'
            )
        elif total_received > 0:
            return format_html(
                '<span style="color: orange;">↻ {}/{} (поставлено частично)</span>',
                total_received, total_ordered
            )
        else:
            return format_html(
                '<span style="color: gray;">⌛ Не поставлено</span>'
            )

    completion_status.short_description = 'Статус выполнения'
    completion_status.admin_order_field = 'is_completed'