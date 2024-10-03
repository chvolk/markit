from django.db.models import Count  # Add this line at the top with other imports
from django.shortcuts import render, get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from .models import BazaarUserProfile, InventoryStock, BazaarListing, PersistentPortfolio, PersistentPortfolioStock
from django.db import transaction
from .serializers import InventoryStockSerializer, BazaarListingSerializer, PersistentPortfolioStockSerializer
from stocks.models import Stock, Portfolio

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from random import choice
import random
import traceback
from django.db import transaction, models
import logging
from django.db.models import F, Sum, OuterRef, Subquery, FloatField
from django.db.models.functions import Coalesce
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import BazaarUserProfile, InventoryStock, BazaarListing, PersistentPortfolio, PersistentPortfolioStock
from stocks.models import Portfolio, Stock

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def bazaar_data(request):
    user = request.user
    profile, created = BazaarUserProfile.objects.get_or_create(user=user, defaults={'moqs': 1000})
    portfolio = get_object_or_404(Portfolio, user=user)
    persistent_portfolio, created = PersistentPortfolio.objects.get_or_create(user=user)
    
    available_gains = portfolio.total_gain_loss
    
    inventory = InventoryStock.objects.filter(user=user)
    market_listings = BazaarListing.objects.all()
    user_listings = BazaarListing.objects.filter(seller=user)
    persistent_stocks = PersistentPortfolioStock.objects.filter(portfolio=persistent_portfolio)
    
    # Fetch current prices for persistent stocks
    persistent_stock_data = []
    for ps in persistent_stocks:
        stock_data = {
            'symbol': ps.stock.symbol,
            'name': ps.stock.name,
            'industry': ps.stock.industry,
            'quantity': ps.quantity,
            'purchase_price': ps.purchase_price,
            'current_price': ps.stock.current_price
        }
        persistent_stock_data.append(stock_data)
    
    market_listings_data = []
    for listing in market_listings:
        serialized_listing = BazaarListingSerializer(listing).data
        market_listings_data.append(serialized_listing)
    
    user_listings_data = []
    for listing in user_listings:
        user_listings_data.append(BazaarListingSerializer(listing).data)
    

    inventory_count = InventoryStock.objects.filter(user=user).count()
    market_listing_count = BazaarListing.objects.filter(seller=user).count()
    persistent_portfolio_count = PersistentPortfolioStock.objects.filter(portfolio__user=user).count()

    return Response({
        'available_gains': available_gains,
        'total_moqs': profile.moqs,
        'inventory': InventoryStockSerializer(inventory, many=True).data,
        'market_listings': market_listings_data,
        'user_listings': user_listings_data,
        'persistent_portfolio': persistent_stock_data,
        'inventory_limit': profile.inventory_limit,
        'market_listing_limit': profile.market_listing_limit,
        'persistent_portfolio_limit': profile.persistent_portfolio_limit,
        'inventory_count': inventory_count,
        'market_listing_count': market_listing_count,
        'persistent_portfolio_count': persistent_portfolio_count,
    })


# Implement other endpoints (add_to_inventory, buy_stock, sell_stock, list_stock, buy_listed_stock) similarly

class BuyStockView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        symbol = request.data.get('symbol')
        quantity = int(request.data.get('quantity', 1))
        
        stock = get_object_or_404(Stock, symbol=symbol)
        portfolio = get_object_or_404(Portfolio, user=request.user)
        
        total_cost = stock.current_price * quantity
        if portfolio.balance < total_cost:
            return Response({"error": "Insufficient funds"}, status=status.HTTP_400_BAD_REQUEST)
        
        portfolio.balance -= total_cost
        portfolio.stocks.add(stock, through_defaults={'quantity': quantity})
        portfolio.save()
        
        return Response({"message": f"{quantity} shares of {symbol} bought successfully"})

class SellStockView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        symbol = request.data.get('symbol')
        quantity = int(request.data.get('quantity', 1))
        
        portfolio = get_object_or_404(Portfolio, user=request.user)
        stock = get_object_or_404(portfolio.stocks, symbol=symbol)
        
        if stock.quantity < quantity:
            return Response({"error": "Insufficient shares"}, status=status.HTTP_400_BAD_REQUEST)
        
        total_value = stock.current_price * quantity
        portfolio.balance += total_value
        
        if stock.quantity == quantity:
            portfolio.stocks.remove(stock)
        else:
            stock.quantity -= quantity
            stock.save()
        
        portfolio.balance += total_value
        portfolio.save()

        # Update total value and gain/loss
        portfolio.update_total_value_and_gain_loss()

        return Response({
            'message': f'Successfully sold {quantity} shares of {stock.name}',
            'new_quantity': stock.quantity if stock.quantity > 0 else 0,
            'remaining_balance': float(portfolio.balance),
            'total_value': float(portfolio.total_value),
            'total_gain_loss': float(portfolio.total_gain_loss)
        }, status=status.HTTP_200_OK)

class AddToInventoryView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        symbol = request.data.get('symbol')
        stock = get_object_or_404(Stock, symbol=symbol)
        user = request.user
        profile = BazaarUserProfile.objects.get(user=user)
        
        if InventoryStock.objects.filter(user=user).count() >= profile.inventory_limit:
            return Response({'error': 'Inventory limit reached'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Add to inventory
        inventory_stock, created = InventoryStock.objects.get_or_create(
            user=request.user,
            symbol=stock.symbol,
            defaults={
                'name': stock.name,
                'industry': stock.industry,
                'current_price': stock.current_price
            }
        )
        
        if not created:
            inventory_stock.current_price = stock.current_price
            inventory_stock.save()
        

        
        serializer = InventoryStockSerializer(inventory_stock)
        return Response({
            'inventory_stock': serializer.data,
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

class BuyPackView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        print("Howdy, partner! We're fixin' to buy a pack of stocks!")
        user = request.user
        profile = BazaarUserProfile.objects.get(user=request.user)
    
        print(f"Checkin' if {user.username} has room in their inventory...")
        if BazaarListing.objects.filter(seller=user).count() >= profile.inventory_limit:
            print("Dagnabit! Inventory's full as a tick!")
            return Response({'error': 'Inventory limit reached'}, status=status.HTTP_400_BAD_REQUEST)
    
        currency = request.data.get('currency')
        print(f"Usin' {currency} to buy this here pack")
        if currency not in ['gains', 'moqs']:
            print("Well, butter my biscuit! That ain't a valid currency!")
            return Response({"error": "Invalid currency"}, status=status.HTTP_400_BAD_REQUEST)
        
        profile = get_object_or_404(BazaarUserProfile, user=request.user)
        portfolio = get_object_or_404(Portfolio, user=request.user)
        
        pack_price = 500 if currency == 'gains' else 250  # Example prices
        print(f"This pack's gonna cost ya {pack_price} {currency}")
        
        available_gains = portfolio.total_gain_loss - portfolio.total_spent
        if currency == 'gains' and available_gains < pack_price:
            print("You're broker than a cowboy after a night in Tombstone!")
            return Response({"error": "Insufficient gains"}, status=status.HTTP_400_BAD_REQUEST)
        elif currency == 'moqs' and profile.moqs < pack_price:
            print("You're outta moqs, pardner!")
            return Response({"error": "Insufficient moqs"}, status=status.HTTP_400_BAD_REQUEST)
        
        print("Roundin' up all them industries with at least 5 stocks...")
        industries = Stock.objects.values('industry').annotate(
            count=Count('industry')
        ).filter(count__gte=5)
        
        if not industries:
            print("Well, I'll be! There ain't no industries with enough stocks!")
            return Response({"error": "No industries with enough stocks available"}, status=status.HTTP_400_BAD_REQUEST)
        
        print("Pickin' an industry at random, like drawin' from a hat...")
        selected_industry = choice(industries)['industry']
        print(f"And the winner is... {selected_industry}!")
        
        print(f"Now, let's rustle up 5 random stocks from {selected_industry}")
        industry_stocks = list(Stock.objects.filter(industry=selected_industry))
        selected_pack_stocks = random.sample(industry_stocks, min(5, len(industry_stocks)))
        print("Here's what we lassoed:")
        for stock in selected_pack_stocks:
            print(f"Symbol: {stock.symbol}, Name: {stock.name}, Industry: {stock.industry}")
        
        pack_stocks = []
        for stock in selected_pack_stocks:
            pack_stocks.append({
                'symbol': stock.symbol,
                'name': stock.name,
                'industry': stock.industry,
                'current_price': stock.current_price
            })
        print("Fixin' to send these stocks to the frontend:")
        print(pack_stocks)
        if currency == 'gains':
            print(f"Takin' {pack_price} gains from your portfolio")
            portfolio.available_gains -= pack_price
            portfolio.total_spent += pack_price
            portfolio.save()
        else:
            print(f"Takin' {pack_price} moqs from your profile")
            profile.moqs -= pack_price
            profile.save()
        
        print("Well, hot dog! You've got yourself a new pack of stocks!")
        return Response({
            "message": "Pack bought successfully",
            "industry": selected_industry,
            "stocks": pack_stocks
        })


class ListStockView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        logger.info(f"Listing request received for user {request.user.username}")
        user = request.user
        profile = BazaarUserProfile.objects.get(user=user)
        if BazaarListing.objects.filter(seller=user).count() >= profile.market_listing_limit:
            return Response({'error': 'Market listing limit reached'}, status=status.HTTP_400_BAD_REQUEST)
        
        symbol = request.data.get('symbol')
        price = request.data.get('price')

        try:
            inventory_stock = InventoryStock.objects.get(user=request.user, symbol=symbol)
            stock = get_object_or_404(Stock, symbol=symbol)
            listing = BazaarListing.objects.create(
                seller=request.user,
                stock=stock,
                price=price,
                symbol=inventory_stock.symbol,
                name=inventory_stock.name
            )
            logger.info(f"BazaarListing created with ID: {listing.id}")

            # Remove the stock from the user's inventory
            listing.save()
            inventory_stock.delete()
            logger.info(f"InventoryStock {inventory_stock.id} deleted and removed from BazaarListing")

            return Response({'Listing response': 'Stock listed successfully', 'listing_id': listing.id}, status=status.HTTP_201_CREATED)

        except InventoryStock.DoesNotExist:
            logger.error(f"InventoryStock not found for user {request.user.username} and symbol {symbol}")
            return Response({'error': 'Stock not found in inventory'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            logger.error(f"Error creating listing: {str(e)}")
            logger.error(traceback.format_exc())
            return Response({'error': 'Listing creation failed', 'details': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)    
        
class EditListingView(APIView):
    permission_classes = [IsAuthenticated]
 
    def put(self, request, listing_id):
        listing = get_object_or_404(BazaarListing, id=listing_id, seller=request.user)
        
        new_price = request.data.get('price')
        if new_price:
            listing.price = new_price
            listing.save()
        
        serializer = BazaarListingSerializer(listing)
        return Response(serializer.data)

class BuyListedStockView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        listing_id = request.data.get('listing_id')
        listing = get_object_or_404(BazaarListing, id=listing_id)
        try:    
            print(f"Buying listing {listing_id} with price {listing.price}")
            buyer_profile = get_object_or_404(BazaarUserProfile, user=request.user)
        
            if buyer_profile.moqs < listing.price:
                return Response({"error": "Insufficient moqs"}, status=status.HTTP_400_BAD_REQUEST)
            print("got past moqs check")
        except Exception as e:
            print(f"Error getting buyer profile: {str(e)}")
        buyer_profile.moqs -= listing.price
        buyer_profile.save()
        print("deducted moqs from buyer")
        seller_profile = get_object_or_404(BazaarUserProfile, user=listing.seller)
        seller_profile.moqs += listing.price
        seller_profile.save()
        print("added moqs to seller")
        # Transfer the stock to the buyer's inventory
        InventoryStock.objects.create(
            user=request.user,
            symbol=listing.stock.symbol,
            name=listing.stock.name,
            industry=listing.stock.industry,
            current_price=listing.stock.current_price
        )
        print("created inventory stock")
        # Remove the listing
        listing.delete()
        print("deleted listing")
        print(f"Listing {listing_id} bought and removed")
        
        return Response({"message": "Listed stock bought successfully"})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def persistent_portfolio_data(request):
    user = request.user
    profile, created = BazaarUserProfile.objects.get_or_create(user=user, defaults={'moqs': 1000})
    persistent_portfolio, created = PersistentPortfolio.objects.get_or_create(user=user)
    
    stocks = PersistentPortfolioStock.objects.filter(portfolio=persistent_portfolio)
    
    # Let's add some logging here
    print("Persistent Portfolio Stocks:", stocks)
    total_value = 0
    for stock in stocks:
        current_price = Stock.objects.get(symbol=stock.stock.symbol).current_price
        stock.current_price = current_price
        total_value += current_price * stock.quantity
    
    gain_loss = total_value
    serialized_data = PersistentPortfolioStockSerializer(stocks, many=True).data
    print("Serialized Data:", serialized_data)
    
    return Response({
        'available_moqs': profile.moqs,
        'stocks': serialized_data,
        'gain_loss': gain_loss,
        'total_value': total_value
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def moq_leaderboard(request):
    leaderboard = BazaarUserProfile.objects.all().order_by('-moqs')[:100]
    # Get total value of persistent portfolio for each user
    data = []
    for profile in leaderboard:
        try:
            persistent_portfolio = PersistentPortfolio.objects.get(user=profile.user)
            stocks = PersistentPortfolioStock.objects.filter(portfolio=persistent_portfolio)
            total_value = 0
            for stock in stocks:
                total_value += stock.stock.current_price * stock.quantity
            total_moqs = profile.moqs + total_value
        except Exception as e:
            print(f"Error getting persistent portfolio for user {profile.user.username}: {str(e)}") 
            continue
        user_dict = {'username': profile.user.username, 'total_moqs': total_moqs}
        data.append(user_dict)

    # Filter out users with total_moqs of 600
    data = [user for user in data if user['total_moqs'] != 600]
    data.sort(key=lambda x: x['total_moqs'], reverse=True)
    return Response(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def buy_persistent_stock(request):
    user = request.user
    symbol = request.data.get('symbol')
    quantity = int(request.data.get('quantity'))  # Default to 1 for "Lock In"
    
    if not symbol or quantity <= 0:
        return Response({'error': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)
    
    profile = get_object_or_404(BazaarUserProfile, user=user)
    stock = get_object_or_404(Stock, symbol=symbol)
    persistent_portfolio, created = PersistentPortfolio.objects.get_or_create(user=user)
    bazaar_user_profile = get_object_or_404(BazaarUserProfile, user=user)
    user_portfolio = get_object_or_404(Portfolio, user=user)

    #check if they have enough gains. Gain is the difference between initial balance and current balance of the user
    gain = user_portfolio.balance - 50000
    if gain < stock.current_price * quantity:
        return Response({'error': 'Insufficient gains'}, status=status.HTTP_400_BAD_REQUEST)
    else:
        print("User has enough gains")
        user_portfolio.balance -= stock.current_price * quantity
        user_portfolio.save()

    print("Stock is in inventory")
    # For "Lock In", we don't deduct MOQs
    portfolio_stock, created = PersistentPortfolioStock.objects.get_or_create(
        portfolio=persistent_portfolio,
        stock=stock,
        defaults={'quantity': 0, 'purchase_price': stock.current_price}
    )
    
    portfolio_stock.quantity += quantity
    
    portfolio_stock.save()
    
    return Response({'success': 'Stock locked in successfully'}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sell_persistent_stock(request):
    user = request.user
    symbol = request.data.get('symbol')
    quantity = int(request.data.get('quantity', 0))
    
    if not symbol or quantity <= 0:
        return Response({'error': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)
    
    profile = get_object_or_404(BazaarUserProfile, user=user)
    stock = get_object_or_404(Stock, symbol=symbol)
    persistent_portfolio = get_object_or_404(PersistentPortfolio, user=user)
    
    try:
        portfolio_stock = PersistentPortfolioStock.objects.get(portfolio=persistent_portfolio, stock=stock)
    except PersistentPortfolioStock.DoesNotExist:
        return Response({'error': 'Stock not in portfolio'}, status=status.HTTP_400_BAD_REQUEST)
    
    if portfolio_stock.quantity < quantity:
        return Response({'error': 'Not enough shares to sell'}, status=status.HTTP_400_BAD_REQUEST)
    
    total_value = stock.current_price * quantity
    
    portfolio_stock.quantity -= quantity
    if portfolio_stock.quantity == 0:
        portfolio_stock.delete()
    else:
        portfolio_stock.save()
    
    profile.moqs += total_value
    profile.save()
    
    return Response({'success': 'Stock sold successfully'}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def lock_in_persistent_stock(request):
    user = request.user
    symbol = request.data.get('symbol')
    quantity = int(request.data.get('quantity', 1))  # Default to 1 for "Lock In"
    profile = BazaarUserProfile.objects.get(user=user)
    
    if PersistentPortfolioStock.objects.filter(portfolio__user=user).count() >= profile.persistent_portfolio_limit:
        return Response({'error': 'Persistent portfolio limit reached'}, status=status.HTTP_400_BAD_REQUEST)
    
    if not symbol or quantity <= 0:
        return Response({'error': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)
    
    profile = get_object_or_404(BazaarUserProfile, user=user)
    stock = get_object_or_404(Stock, symbol=symbol)
    persistent_portfolio, created = PersistentPortfolio.objects.get_or_create(user=user)
    
    # Check if the stock is in the user's inventory
    inventory_stock = InventoryStock.objects.filter(user=user, symbol=symbol).first()
    if not inventory_stock:
        return Response({'error': 'Stock not in inventory'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Add to persistent portfolio without deducting MOQs
    portfolio_stock, created = PersistentPortfolioStock.objects.get_or_create(
        portfolio=persistent_portfolio,
        stock=stock,
        defaults={'quantity': 0, 'purchase_price': stock.current_price}
    )
    
    portfolio_stock.quantity += quantity
    portfolio_stock.save()
    
    # Remove the stock from inventory
    inventory_stock.delete()
    
    return Response({'success': 'Stock locked in successfully'}, status=status.HTTP_200_OK)

class CancelListingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        listing_id = request.data.get('listing_id')
        if not listing_id:
            return Response({'error': 'Listing ID is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            listing = BazaarListing.objects.get(id=listing_id, seller=request.user)
        except BazaarListing.DoesNotExist:
            return Response({'error': 'Listing not found'}, status=status.HTTP_404_NOT_FOUND)

        # Return the stock to the user's inventory
        InventoryStock.objects.create(
            user=request.user,
            symbol=listing.stock.symbol,
            name=listing.stock.name,
            industry=listing.stock.industry,
            current_price=listing.stock.current_price
        )

        # Delete the listing
        listing.delete()

        return Response({'success': 'Listing cancelled successfully'}, status=status.HTTP_200_OK)
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upgrade_inventory_limit(request):
    user = request.user
    profile = BazaarUserProfile.objects.get(user=user)
    
    if profile.moqs < 500:
        return Response({'error': 'Insufficient funds'}, status=status.HTTP_400_BAD_REQUEST)
    
    profile.inventory_limit = F('inventory_limit') + 1

    
    profile.moqs = F('moqs') - 500
    profile.save()
    
    return Response({'success': 'Inventory limit upgraded successfully'}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upgrade_market_listing_limit(request):
    user = request.user
    profile = BazaarUserProfile.objects.get(user=user)
    
    if profile.moqs < 600:
        return Response({'error': 'Insufficient funds'}, status=status.HTTP_400_BAD_REQUEST)
    
    profile.market_listing_limit = F('market_listing_limit') + 1

    
    profile.moqs = F('moqs') - 600
    profile.save()
    
    return Response({'success': 'Market listing limit upgraded successfully'}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upgrade_persistent_portfolio_limit(request):
    user = request.user
    profile = BazaarUserProfile.objects.get(user=user)
    
    if profile.moqs < 700:
        return Response({'error': 'Insufficient funds'}, status=status.HTTP_400_BAD_REQUEST)
    
    profile.persistent_portfolio_limit = F('persistent_portfolio_limit') + 1
    
    profile.moqs = F('moqs') - 700
    profile.save()
    
    return Response({'success': 'Persistent portfolio limit upgraded successfully'}, status=status.HTTP_200_OK)