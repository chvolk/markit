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
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from django.contrib.auth.models import AnonymousUser
import logging
from django.utils import timezone

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def available_stocks(request):
    stocks = Stock.objects.all()
    data = [{'symbol': stock.symbol, 'name': stock.name, 'current_price': stock.current_price} for stock in stocks]
    return Response(data)

class AvailableStocksView(generics.ListAPIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = Stock.objects.all()
    serializer_class = StockSerializer

class PortfolioViewSet(viewsets.ModelViewSet):
    serializer_class = PortfolioSerializer

    def get_queryset(self):
        return Portfolio.objects.filter(user=self.request.user)

class DraftStockView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        stock_symbol = request.data.get('symbol')
        quantity = int(request.data.get('quantity', 1))  # Default to 1 if not provided

        logger.info(f"Attempting to draft {quantity} shares of {stock_symbol}")

        try:
            stock = Stock.objects.get(symbol=stock_symbol)
            portfolio, created = Portfolio.objects.get_or_create(user=request.user)
            portfolio_stock, created = PortfolioStock.objects.get_or_create(portfolio=portfolio, stock=stock)
            
            # Update the quantity
            portfolio_stock.quantity += quantity
            portfolio_stock.save()

            logger.info(f"Successfully drafted {quantity} shares of {stock.name} for user {request.user.username}")
            return Response({
                'message': f'Successfully drafted {quantity} shares of {stock.name}',
                'new_quantity': portfolio_stock.quantity
            }, status=status.HTTP_200_OK)
        except Stock.DoesNotExist:
            logger.error(f"Stock not found: {stock_symbol}")
            return Response({'error': 'Stock not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.exception(f"Error drafting stock: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class PortfolioView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        portfolio, created = Portfolio.objects.get_or_create(user=request.user)
        
        # Check if a reset has occurred
        if created or timezone.now() - portfolio.last_reset > timezone.timedelta(days=7):
            PortfolioStock.objects.filter(portfolio=portfolio).delete()
            portfolio.last_reset = timezone.now()
            portfolio.save()

        portfolio_stocks = PortfolioStock.objects.filter(portfolio=portfolio)
        data = [{
            'stock': {
                'symbol': ps.stock.symbol,
                'name': ps.stock.name,
                'current_price': ps.stock.current_price
            },
            'quantity': ps.quantity
        } for ps in portfolio_stocks]
        return Response({'stocks': data})