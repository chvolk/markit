from django.db import models
from django.contrib.auth.models import User
from stocks.models import Stock

import random
class BazaarUserProfile(models.Model):  # Changed name from UserProfile to BazaarUserProfile
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='bazaar_profile')
    moqs = models.IntegerField(default=0)
    inventory_limit = models.IntegerField(default=10)
    market_listing_limit = models.IntegerField(default=8)
    persistent_portfolio_limit = models.IntegerField(default=6)



class PersistentPortfolio(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='persistent_portfolio')

# class PersistentPortfolioStock(models.Model):
#     portfolio = models.ForeignKey(PersistentPortfolio, on_delete=models.CASCADE, related_name='stocks')
#     stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
#     quantity = models.IntegerField(default=0)
#     purchase_price = models.DecimalField(max_digits=10, decimal_places=2)


class Tag(models.Model):
    TAG_TYPES = [
        ('COMMISSION', 'Sell Value Multiplier'),
        ('TENACIOUS', 'Chance to Keep Shares'),
        ('SUBSIDIZED', 'Bonus Sell Value'),
        ('INSIDER', 'Chance to Buy Bonus Shares'),
        ('GLITCHED', 'Chance to Change into Random Stock when shares are bought or sold'),
    ]

    tag_type = models.CharField(max_length=20, choices=TAG_TYPES)
    value = models.FloatField()  # This will store the multiplier or percentage

    def __str__(self):
        return f"{self.get_tag_type_display()}: {self.value}"
    
class InventoryStock(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    symbol = models.CharField(max_length=10)
    name = models.CharField(max_length=100)
    industry = models.CharField(max_length=100)
    current_price = models.DecimalField(max_digits=10, decimal_places=2)
    tags = models.ManyToManyField(Tag)

class BazaarListing(models.Model):
    id = models.AutoField(primary_key=True)
    seller = models.ForeignKey(User, on_delete=models.CASCADE)
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, default=1)  # Set a default Stock ID
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Use DecimalField for price
    symbol = models.CharField(max_length=10)  # Optional, can be derived from stock
    name = models.CharField(max_length=100)   # Optional, can be derived from stock
    tags = models.ManyToManyField(Tag)
    

    def __str__(self):
        return f"{self.symbol} listed by {self.seller.username} for {self.price} MOQs"
    
class PersistentPortfolioStock(models.Model):
    portfolio = models.ForeignKey(PersistentPortfolio, on_delete=models.CASCADE)
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=0)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2)
    tags = models.ManyToManyField(Tag)

    @classmethod
    def add_random_tag(cls, instance):
        tag_type = random.choice(Tag.TAG_TYPES)[0]
        value = 0
        if tag_type == 'COMMISSION':
            value = random.uniform(1.1, 2.0)
        elif tag_type == 'TENACIOUS':
            value = random.uniform(0.05, 0.4)
        elif tag_type == 'SUBSIDIZED':
            value = random.randint(1, 35)
        elif tag_type == 'INSIDER':
            value = random.uniform(0.05, 0.4)
        elif tag_type == 'GLITCHED':
            value = 1
        elif tag_type == 'SHORTSQUEEZE':
            value = 1
        new_tag = Tag.objects.create(tag_type=tag_type, value=value)
        instance.tags.add(new_tag)
    

