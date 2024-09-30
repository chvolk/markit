from rest_framework import serializers
from .models import InventoryStock, BazaarListing, PersistentPortfolioStock
from stocks.serializers import StockSerializer

class InventoryStockSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryStock
        fields = ['symbol', 'name', 'industry', 'current_price']

class BazaarListingSerializer(serializers.ModelSerializer):
    seller = serializers.CharField(source='seller.username')
    symbol = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    industry = serializers.SerializerMethodField()

    class Meta:
        model = BazaarListing
        fields = ['id', 'seller', 'symbol', 'name', 'industry', 'price']

    def get_symbol(self, obj):
        return obj.symbol if obj.symbol else (obj.stock.symbol if obj.stock else None)

    def get_name(self, obj):
        return obj.name if obj.name else (obj.stock.name if obj.stock else None)

    def get_industry(self, obj):
        return obj.stock.industry if obj.stock else None

class PersistentPortfolioStockSerializer(serializers.ModelSerializer):
    symbol = serializers.CharField(source='stock.symbol')
    name = serializers.CharField(source='stock.name')
    industry = serializers.CharField(source='stock.industry')
    current_price = serializers.DecimalField(source='stock.current_price', max_digits=10, decimal_places=2)

    class Meta:
        model = PersistentPortfolioStock
        fields = ['symbol', 'name', 'industry', 'quantity', 'purchase_price', 'current_price']