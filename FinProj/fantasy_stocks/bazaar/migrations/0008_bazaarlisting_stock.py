# Generated by Django 5.1.1 on 2024-09-30 17:22

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bazaar', '0007_remove_bazaarlisting_stock'),
    ]

    operations = [
        migrations.AddField(
            model_name='bazaarlisting',
            name='stock',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='bazaar.inventorystock'),
        ),
    ]
