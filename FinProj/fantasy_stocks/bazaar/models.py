from django.db import models
from django.contrib.auth.models import User
from stocks.models import Stock

class BazaarUserProfile(models.Model):  # Changed name from UserProfile to BazaarUserProfile
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='bazaar_profile')
    moqs = models.IntegerField(default=0)

class InventoryStock(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    symbol = models.CharField(max_length=10)
    name = models.CharField(max_length=100)
    industry = models.CharField(max_length=100)
    current_price = models.DecimalField(max_digits=10, decimal_places=2)

class BazaarListing(models.Model):
    id = models.AutoField(primary_key=True)
    seller = models.ForeignKey(User, on_delete=models.CASCADE)
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, default=1)  # Set a default Stock ID
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Use DecimalField for price
    symbol = models.CharField(max_length=10)  # Optional, can be derived from stock
    name = models.CharField(max_length=100)   # Optional, can be derived from stock

    def __str__(self):
        return f"{self.symbol} listed by {self.seller.username} for {self.price} MOQs"

class PersistentPortfolio(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='persistent_portfolio')

class PersistentPortfolioStock(models.Model):
    portfolio = models.ForeignKey(PersistentPortfolio, on_delete=models.CASCADE, related_name='stocks')
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=0)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2)