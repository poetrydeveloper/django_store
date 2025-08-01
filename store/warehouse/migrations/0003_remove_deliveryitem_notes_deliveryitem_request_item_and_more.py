# Generated by Django 5.2.4 on 2025-07-20 10:01

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('unit', '0004_alter_productunit_sale_date_and_more'),
        ('warehouse', '0002_alter_deliveryitem_price_per_unit_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='deliveryitem',
            name='notes',
        ),
        migrations.AddField(
            model_name='deliveryitem',
            name='request_item',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='delivery_items', to='warehouse.requestitem', verbose_name='Связанная заявка'),
        ),
        migrations.AddField(
            model_name='requestitem',
            name='quantity_received',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='requestitem',
            name='supplier',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='warehouse.supplier'),
        ),
        migrations.AlterField(
            model_name='deliveryitem',
            name='price_per_unit',
            field=models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Цена за единицу'),
        ),
        migrations.AlterField(
            model_name='deliveryitem',
            name='received_units',
            field=models.ManyToManyField(blank=True, related_name='delivery_items_received', to='unit.productunit', verbose_name='Полученные единицы'),
        ),
    ]
