from django.contrib import admin
from .models import Stock, Portfolio, PortfolioStock, UserProfile

# Register your models here.

admin.site.register(Stock)
admin.site.register(Portfolio)
admin.site.register(PortfolioStock)
admin.site.register(UserProfile)
