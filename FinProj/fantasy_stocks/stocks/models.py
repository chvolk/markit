from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal

class Stock(models.Model):
    symbol = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    industry = models.CharField(max_length=100, blank=True, null=True)
    current_price = models.DecimalField(max_digits=10, decimal_places=2)
    last_updated = models.DateTimeField(auto_now=True)

class Portfolio(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('50000.00'))
    stocks = models.ManyToManyField('Stock', through='PortfolioStock')
    last_reset = models.DateTimeField(auto_now_add=True)
    initial_investment = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('50000.00'))
    total_value = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('50000.00'))
    total_gain_loss = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    def calculate_value(self):
        stock_value = sum(ps.stock.current_price * ps.quantity for ps in self.portfoliostock_set.all())
        return stock_value + self.balance

    def update_total_value_and_gain_loss(self):
        self.total_value = self.calculate_value()
        self.total_gain_loss = self.total_value - self.initial_investment
        self.save()

    def reset_balance(self):
        self.balance = 50000.00
        self.save()

class PortfolioStock(models.Model):
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE)
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=0)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    initial_balance = models.DecimalField(max_digits=10, decimal_places=2, default=10000.00)
    total_gain_loss = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return self.user.username

class PortfolioHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    total_value = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ['-timestamp']