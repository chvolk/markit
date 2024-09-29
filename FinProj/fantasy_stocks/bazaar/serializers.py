from rest_framework import serializers
from .models import InventoryStock, BazaarListing, PersistentPortfolioStock
from stocks.serializers import StockSerializer

class InventoryStockSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryStock
        fields = ['id', 'symbol', 'name', 'industry', 'current_price']

class BazaarListingSerializer(serializers.ModelSerializer):
    class Meta:
        model = BazaarListing
        fields = ['id', 'seller', 'stock', 'price']

class PersistentPortfolioStockSerializer(serializers.ModelSerializer):
    stock = StockSerializer()

    class Meta:
        model = PersistentPortfolioStock
        fields = ['id', 'stock', 'quantity', 'purchase_price']
