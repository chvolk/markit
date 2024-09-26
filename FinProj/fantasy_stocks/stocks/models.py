from django.db import models
from django.contrib.auth.models import User

class Stock(models.Model):
    symbol = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    industry = models.CharField(max_length=100, blank=True, null=True)
    current_price = models.DecimalField(max_digits=10, decimal_places=2)
    last_updated = models.DateTimeField(auto_now=True)

class Portfolio(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    stocks = models.ManyToManyField('Stock', through='PortfolioStock')

    def calculate_value(self):
        return sum(ps.stock.current_price * ps.quantity for ps in self.portfoliostock_set.all())

class PortfolioStock(models.Model):
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE)
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=0)