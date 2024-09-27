from rest_framework import serializers
from .models import Stock, Portfolio, PortfolioStock

class StockSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stock
        fields = ['id', 'symbol', 'name', 'current_price', 'industry', 'last_updated']

class PortfolioStockSerializer(serializers.ModelSerializer):
    stock = StockSerializer()

    class Meta:
        model = PortfolioStock
        fields = ['stock', 'quantity']

class PortfolioSerializer(serializers.ModelSerializer):
    stocks = PortfolioStockSerializer(source='portfoliostock_set', many=True, read_only=True)

    class Meta:
        model = Portfolio
        fields = ['id', 'user', 'stocks']