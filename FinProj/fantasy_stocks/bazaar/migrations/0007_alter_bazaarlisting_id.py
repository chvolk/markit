# Generated by Django 5.1.1 on 2024-09-30 19:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bazaar', '0006_alter_bazaarlisting_price_alter_bazaarlisting_stock'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bazaarlisting',
            name='id',
            field=models.AutoField(primary_key=True, serialize=False),
        ),
    ]
