from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import viewsets
from .models import Stock, Portfolio, PortfolioStock
from .serializers import StockSerializer, PortfolioSerializer
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Stock

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def available_stocks(request):
    stocks = Stock.objects.all()
    data = [{'symbol': stock.symbol, 'name': stock.name, 'current_price': stock.current_price} for stock in stocks]
    return Response(data)

class AvailableStocksView(generics.ListAPIView):
    queryset = Stock.objects.all()
    serializer_class = StockSerializer

class PortfolioViewSet(viewsets.ModelViewSet):
    serializer_class = PortfolioSerializer

    def get_queryset(self):
        return Portfolio.objects.filter(user=self.request.user)

class DraftStockView(APIView):
    def post(self, request):
        stock_symbol = request.data.get('symbol')
        try:
            stock = Stock.objects.get(symbol=stock_symbol)
            portfolio, created = Portfolio.objects.get_or_create(user=request.user)
            portfolio_stock, created = PortfolioStock.objects.get_or_create(portfolio=portfolio, stock=stock)
            if not created:
                portfolio_stock.quantity += 1
            else:
                portfolio_stock.quantity = 1
            portfolio_stock.save()
            return Response({'message': f'Successfully drafted {stock.name}'}, status=status.HTTP_200_OK)
        except Stock.DoesNotExist:
            return Response({'error': 'Stock not found'}, status=status.HTTP_404_NOT_FOUND)