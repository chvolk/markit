# Generated by Django 5.0.7 on 2024-09-27 04:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stocks', '0005_portfoliostock_purchase_price'),
    ]

    operations = [
        migrations.AddField(
            model_name='portfolio',
            name='initial_investment',
            field=models.DecimalField(decimal_places=2, default=50000.0, max_digits=10),
        ),
        migrations.AddField(
            model_name='portfolio',
            name='total_gain_loss',
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=10),
        ),
        migrations.AddField(
            model_name='portfolio',
            name='total_value',
            field=models.DecimalField(decimal_places=2, default=50000.0, max_digits=10),
        ),
    ]
