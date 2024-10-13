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
from django.db import transaction
from django.db.models import F, Sum, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce
from django.contrib.auth.models import User
from decimal import Decimal
from .models import PortfolioHistory
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
    
class PortfolioHistoryView(APIView):
    def get(self, request):
        history = PortfolioHistory.objects.filter(user=request.user).order_by('timestamp')
        data = [
            {
                'timestamp': entry.timestamp.isoformat(),
                'total_value': float(entry.total_value)
            }
            for entry in history
        ]
        return Response(data)

class DraftStockView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        stock_symbol = request.data.get('symbol')
        quantity = int(request.data.get('quantity', 1))

        try:
            stock = Stock.objects.get(symbol=stock_symbol)
            portfolio = Portfolio.objects.get(user=request.user)
            
            total_cost = Decimal(stock.current_price) * Decimal(quantity)
            print(f"Total cost: {total_cost}")
            print(f"Current balance: {portfolio.balance}")

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
                total_quantity = Decimal(portfolio_stock.quantity) + Decimal(quantity)
                total_cost_for_average = (Decimal(portfolio_stock.purchase_price) * Decimal(portfolio_stock.quantity)) + (Decimal(stock.current_price) * Decimal(quantity))
                portfolio_stock.purchase_price = total_cost_for_average / total_quantity

            portfolio_stock.quantity += quantity
            portfolio_stock.save()

            # Update the balance using Decimal arithmetic
            new_balance = portfolio.balance - total_cost
            print(f"Calculated new balance: {new_balance}")
            portfolio.balance = new_balance
            portfolio.save()

            # Update total value and gain/loss
            portfolio.update_total_value_and_gain_loss()
            print(f"Total value after update: {portfolio.total_value}")
            print(f"Total gain/loss after update: {portfolio.total_gain_loss}")

            return Response({
                'message': f'Successfully drafted {quantity} shares of {stock.name}',
                'new_quantity': portfolio_stock.quantity,
                'remaining_balance': float(portfolio.balance),
                'total_value': float(portfolio.total_value),
                'total_gain_loss': float(portfolio.total_gain_loss)
            }, status=status.HTTP_200_OK)
        except Stock.DoesNotExist:
            return Response({'error': 'Stock not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error in DraftStockView: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class PortfolioView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        portfolio, created = Portfolio.objects.get_or_create(user=request.user)
        portfolio.update_total_value_and_gain_loss()  # Update the total value and gain/loss
        portfolio_stocks = PortfolioStock.objects.filter(portfolio=portfolio)
        if portfolio.available_gains is None or portfolio.available_gains == 0:
            available_gains = portfolio.total_gain_loss - portfolio.total_spent
        else:
            available_gains = portfolio.available_gains
        data = {
            'balance': str(portfolio.balance),
            'total_value': str(portfolio.total_value),
            'total_gain_loss': str(portfolio.total_gain_loss),
            'initial_investment': str(portfolio.initial_investment),
            'total_spent': str(portfolio.total_spent),
            'available_gains': str(available_gains),
            'user': request.user.username,  # Changed from request.user to request.user.username
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

        # Filter out users with total_value not equal to 50000.00
        try:
            users = users.exclude(total_value=50000.00)
        except Exception as e:
            print(f"Well, butter my biscuit! Error filtering users: {str(e)}")

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
        

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_gains(request):
    user = request.user
    new_gains = request.data.get('available_gains', False)

    if new_gains is None:
        return Response({'error': 'Gains value is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        new_gains = float(new_gains)
    except ValueError:
        return Response({'error': 'Invalid gains value'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        profile = Portfolio.objects.get(user=user)
        if new_gains:
            profile.available_gains = new_gains
        profile.save()
        return Response({'message': 'Gains updated successfully'}, status=status.HTTP_200_OK)
    except Portfolio.DoesNotExist:
        return Response({'error': 'User profile not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_spent(request):
    user = request.user
    spent_amount = request.data.get('spent')

    print(f"Updating spent for user: {user.username}")
    print(f"Received spent amount: {spent_amount}")

    if spent_amount is None:
        print("Error: spent value is required")
        return Response({'error': 'spent value is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        spent_amount = float(spent_amount)
        print(f"Converted spent amount to float: {spent_amount}")
    except ValueError:
        print("Error: Invalid spent value")
        return Response({'error': 'Invalid spent value'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        profile = Portfolio.objects.get(user=user)
        print(f"Found profile for user: {user.username}")
        print(f"Current total spent: {profile.total_spent}")
        profile.total_spent = profile.total_spent + Decimal(str(spent_amount))
        print(f"Updated total spent: {profile.total_spent}")
        profile.save()
        print("Profile saved successfully")
        return Response({'message': 'spent updated successfully'}, status=status.HTTP_200_OK)
    except Portfolio.DoesNotExist:
        print(f"Error: User profile not found for {user.username}")
        return Response({'error': 'User profile not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

