from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import viewsets
from .models import Stock, Portfolio, PortfolioStock
from .serializers import StockSerializer, PortfolioSerializer, UserSerializer
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Stock
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from django.contrib.auth.models import AnonymousUser
import logging
from django.utils import timezone
from django.db import transaction
from django.db.models import F, Sum, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce
from django.contrib.auth.models import User
from decimal import Decimal

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

    @transaction.atomic
    def post(self, request):
        stock_symbol = request.data.get('symbol')
        quantity = int(request.data.get('quantity', 1))

        try:
            stock = Stock.objects.get(symbol=stock_symbol)
            portfolio = Portfolio.objects.get(user=request.user)
            
            total_cost = stock.current_price * quantity
            if portfolio.balance < total_cost:
                return Response({
                    'error': 'Insufficient funds to complete this draft.'
                }, status=status.HTTP_400_BAD_REQUEST)

            portfolio_stock, created = PortfolioStock.objects.get_or_create(
                portfolio=portfolio, 
                stock=stock,
                defaults={'purchase_price': stock.current_price}
            )
            if not created:
                # If not created, update the purchase price as an average
                total_quantity = portfolio_stock.quantity + quantity
                total_cost = (portfolio_stock.purchase_price * portfolio_stock.quantity) + (stock.current_price * quantity)
                portfolio_stock.purchase_price = total_cost / total_quantity

            portfolio_stock.quantity += quantity
            portfolio_stock.save()

            portfolio.balance -= total_cost
            portfolio.save()

            return Response({
                'message': f'Successfully drafted {quantity} shares of {stock.name}',
                'new_quantity': portfolio_stock.quantity,
                'remaining_balance': float(portfolio.balance),
                'user': request.user.username
            }, status=status.HTTP_200_OK)
        except Stock.DoesNotExist:
            return Response({'error': 'Stock not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class PortfolioView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        portfolio, created = Portfolio.objects.get_or_create(user=request.user)
        portfolio.update_total_value_and_gain_loss()  # Update the total value and gain/loss
        portfolio_stocks = PortfolioStock.objects.filter(portfolio=portfolio)
        data = {
            'balance': str(portfolio.balance),
            'total_value': str(portfolio.total_value),
            'total_gain_loss': str(portfolio.total_gain_loss),
            'user': request.user.username,
            'stocks': [{
                'stock': {
                    'symbol': ps.stock.symbol,
                    'name': ps.stock.name,
                    'current_price': str(ps.stock.current_price),
                    'purchase_price': str(ps.purchase_price) if ps.purchase_price is not None else str(ps.stock.current_price)
                },
                'quantity': ps.quantity
            } for ps in portfolio_stocks]
        }
        return Response(data)

class LeaderboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        users = User.objects.annotate(
            portfolio_value=Coalesce(Sum(
                ExpressionWrapper(
                    F('portfolio__portfoliostock__quantity') * F('portfolio__portfoliostock__stock__current_price'),
                    output_field=DecimalField(max_digits=10, decimal_places=2)
                )
            ), 0),
            total_value=ExpressionWrapper(
                F('portfolio_value') + F('portfolio__balance'),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            ),
            gain_loss=ExpressionWrapper(
                F('total_value') - F('portfolio__initial_investment'),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        ).values('username', 'total_value', 'gain_loss').order_by('-gain_loss')

        return Response(list(users))

class SellStockView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        stock_symbol = request.data.get('symbol')
        quantity = int(request.data.get('quantity', 1))

        try:
            stock = Stock.objects.get(symbol=stock_symbol)
            portfolio = Portfolio.objects.get(user=request.user)
            portfolio_stock = PortfolioStock.objects.get(portfolio=portfolio, stock=stock)

            if portfolio_stock.quantity < quantity:
                return Response({
                    'error': 'Not enough shares to complete this sale.'
                }, status=status.HTTP_400_BAD_REQUEST)

            total_sale = stock.current_price * quantity
            portfolio_stock.quantity -= quantity
            
            if portfolio_stock.quantity == 0:
                portfolio_stock.delete()
            else:
                portfolio_stock.save()

            portfolio.balance += total_sale
            portfolio.save()

            portfolio.update_total_value_and_gain_loss()

            return Response({
                'message': f'Successfully sold {quantity} shares of {stock.name}',
                'new_quantity': portfolio_stock.quantity if portfolio_stock.quantity > 0 else 0,
                'remaining_balance': float(portfolio.balance)
            }, status=status.HTTP_200_OK)
        except Stock.DoesNotExist:
            return Response({'error': 'Stock not found'}, status=status.HTTP_404_NOT_FOUND)
        except PortfolioStock.DoesNotExist:
            return Response({'error': 'You do not own this stock'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)