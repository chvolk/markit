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
from .models import BazaarUserProfile, InventoryStock, BazaarListing, PersistentPortfolio, PersistentPortfolioStock, Tag
# from .models import Tag
import random
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

    inventory_data = []
    for item in inventory:
        item_data = {
            'symbol': item.symbol,
            'name': item.name,
            'industry': item.industry,
            'current_price': item.current_price,
            'tags': ", ".join([f"{tag.tag_type}: {str(round(float(tag.value), 2))}" for tag in item.tags.all()])
        }
        inventory_data.append(item_data)
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
            'current_price': ps.stock.current_price,
            'tags': ", ".join([f"{tag.tag_type}: {str(round(float(tag.value), 2))}" for tag in ps.tags.all()])
        }
        persistent_stock_data.append(stock_data)
    
    market_listings_data = []
    for listing in market_listings:
        serialized_listing = BazaarListingSerializer(listing).data
        stock_current_price = listing.stock.current_price
        serialized_listing['current_price'] = stock_current_price
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
        'inventory': inventory_data,
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
        tag = request.data.get('tags')
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
                'current_price': stock.current_price,
            }
        )
        if tag == 'COMMISSION':
            value = random.uniform(1.1, 2.0)
        elif tag == 'TENACIOUS':
            value = random.uniform(0.1, 0.6)
        elif tag == 'SUBSIDIZED':
            value = random.randint(1, 100)
        elif tag == 'INSIDER':
            value = random.uniform(0.1, 0.6)
        elif tag == 'GLITCHED':
            value = 1
        elif tag == 'SHORTSQUEEZE':
            value = 1
        if tag and tag != "Neutral":
            try:
                tag, _ = Tag.objects.get_or_create(tag_type=tag, value=value)
                inventory_stock.tags.add(tag)
            except Exception as e:
                print(f"Error adding tag: {str(e)}")
        
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
        user = request.user
        profile = BazaarUserProfile.objects.get(user=request.user)
    
        if BazaarListing.objects.filter(seller=user).count() >= profile.inventory_limit:
            return Response({'error': 'Inventory limit reached'}, status=status.HTTP_400_BAD_REQUEST)
        
        currency = request.data.get('currency')
        if currency not in ['gains', 'moqs']:
            return Response({"error": "Invalid currency"}, status=status.HTTP_400_BAD_REQUEST)
        
        profile = get_object_or_404(BazaarUserProfile, user=request.user)
        portfolio = get_object_or_404(Portfolio, user=request.user)
        
        pack_price = 500 if currency == 'gains' else 250  # Example prices
        
        available_gains = portfolio.available_gains
        if currency == 'gains' and available_gains < pack_price:
            return Response({"error": "Insufficient gains"}, status=status.HTTP_400_BAD_REQUEST)
        elif currency == 'moqs' and profile.moqs < pack_price:
            return Response({"error": "Insufficient moqs"}, status=status.HTTP_400_BAD_REQUEST)
        
        industries = Stock.objects.values('industry').annotate(
            count=Count('industry')
        ).filter(count__gte=5)
        
        if not industries:
            return Response({"error": "No industries with enough stocks available"}, status=status.HTTP_400_BAD_REQUEST)
        
        selected_industry = choice(industries)['industry']
        
        industry_stocks = list(Stock.objects.filter(industry=selected_industry))
        selected_pack_stocks = random.sample(industry_stocks, min(5, len(industry_stocks)))
        
        pack_stocks = []
        for stock in selected_pack_stocks:
            if random.random() < 0.23:
                tag = random.choice(Tag.TAG_TYPES)[0]
            else:
                tag = "Neutral"
            pack_stocks.append({
                'symbol': stock.symbol,
                'name': stock.name,
                'industry': stock.industry,
                'current_price': stock.current_price,
                'tags': tag
            })
            
        if currency == 'gains':
            portfolio.available_gains -= pack_price
            portfolio.total_spent += pack_price
            portfolio.save()
        else:
            profile.moqs -= pack_price
            profile.save()
        
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
            tags = inventory_stock.tags.all()
            stock = get_object_or_404(Stock, symbol=symbol)
            listing = BazaarListing.objects.create(
                seller=request.user,
                stock=stock,
                price=price,
                symbol=inventory_stock.symbol,
                name=inventory_stock.name
            )
            listing.tags.set(tags)
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
        tags = listing.tags.all()
        # Transfer the stock to the buyer's inventory
        inventory_stock = InventoryStock.objects.create(
            user=request.user,
            symbol=listing.stock.symbol,

            name=listing.stock.name,
            industry=listing.stock.industry,
            current_price=listing.stock.current_price
        )
        inventory_stock.tags.set(tags)
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
    portfolio = get_object_or_404(Portfolio, user=user)
    spent = portfolio.total_spent
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
        'total_spent': spent,
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
    quantity = int(request.data.get('quantity')) 
    
    if not symbol or quantity <= 0:
        return Response({'error': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)
    
    profile = get_object_or_404(BazaarUserProfile, user=user)
    stock = get_object_or_404(Stock, symbol=symbol)
    persistent_portfolio, created = PersistentPortfolio.objects.get_or_create(user=user)
    bazaar_user_profile = get_object_or_404(BazaarUserProfile, user=user)
    user_portfolio = get_object_or_404(Portfolio, user=user)

    gain = user_portfolio.available_gains
    total_cost = stock.current_price * quantity
    
    if gain < total_cost:
        return Response({'error': 'Insufficient gains'}, status=status.HTTP_400_BAD_REQUEST)
    else:
        user_portfolio.available_gains -= total_cost
        user_portfolio.total_spent += total_cost
        user_portfolio.save()

    # Check if the stock is already in the portfolio
    portfolio_stock, created = PersistentPortfolioStock.objects.get_or_create(
        portfolio=persistent_portfolio,
        stock=stock,
        defaults={'quantity': 0, 'purchase_price': stock.current_price}
    )

    #get the first tag from the portfolio stock
    tag = portfolio_stock.tags.first()
    if tag:
        tag_value = tag.value
        tag_type = tag.tag_type
    else:
        tag_value = 1
        tag_type = "Neutral"
    
    proc = False
    if tag_type == "INSIDER":
        if random.random() < .4:
            quantity = quantity + (quantity * tag_value)
            portfolio_stock.quantity += quantity
            portfolio_stock.save()
            proc = True
        else:
            portfolio_stock.quantity += quantity
            portfolio_stock.save()
            proc = False
    elif tag_type == "GLITCHED":
        if random.random() < .1:
            with transaction.atomic():
                print("GLITCHED effect triggered!")
                # Store the old stock's information
                old_quantity = portfolio_stock.quantity
                new_quantity = old_quantity + quantity
                old_purchase_price = portfolio_stock.purchase_price
                old_stock = portfolio_stock.stock
                print(f"Old stock: {old_stock.symbol}, Quantity: {old_quantity}, New Quantity: {new_quantity}")

                # Randomly select a new stock from the same industry
                new_stock = Stock.objects.filter(industry=old_stock.industry).exclude(id=old_stock.id).order_by('?').first()

                if new_stock:
                    print(f"New stock selected: {new_stock.symbol}")
                    # Create the new portfolio stock
                    new_portfolio_stock = PersistentPortfolioStock.objects.create(
                        portfolio=persistent_portfolio,
                        stock=new_stock,
                        quantity=new_quantity,
                        purchase_price=old_purchase_price
                    )
                    print(f"New portfolio stock created: {new_portfolio_stock}")

                    # Give new stock the glitched tag
                    tag, _ = Tag.objects.get_or_create(tag_type="GLITCHED", value=1)
                    new_portfolio_stock.tags.add(tag)
                    print(f"GLITCHED tag added to new stock")

                    # Delete the old portfolio stock
                    portfolio_stock.delete()
                    print(f"Old portfolio stock deleted")

                    # Update the portfolio_stock reference to the new one
                    portfolio_stock = new_portfolio_stock
                    proc = True
                    print(f"GLITCHED effect successful: {old_stock.symbol} -> {new_stock.symbol}")
                else:
                    # If no new stock is found, keep the old one
                    portfolio_stock.quantity = new_quantity
                    portfolio_stock.save()
                    proc = False
                    print(f"No new stock found. Keeping old stock: {old_stock.symbol}")
        else:
            print("GLITCHED effect failed")
            portfolio_stock.quantity += quantity
            portfolio_stock.save()
            proc = False
    else:
        portfolio_stock.quantity += quantity
        portfolio_stock.save()
        proc = False
    return Response({'success': 'Stock locked in successfully', 'proc': proc}, status=status.HTTP_200_OK)

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
    
    # portfolio_stock.quantity -= quantity
    # if portfolio_stock.quantity == 0:
    #     portfolio_stock.delete()
    # else:
    #     portfolio_stock.save()
    
    # profile.moqs += total_value
    # profile.save()
    tag = portfolio_stock.tags.first()
    if tag:
        tag_value = tag.value
        tag_type = tag.tag_type
    else:
        tag_value = 1
        tag_type = "Neutral"
    proc = False
    if tag_type == "COMMISSION":
        if random.random() < .2:
            total_value = total_value * tag_value
            proc = True
        portfolio_stock.quantity -= quantity
    elif tag_type == "TENACIOUS":
        if random.random() < .3:
            quantity = round(quantity * tag_value, 0)
            portfolio_stock.quantity -= quantity
            proc = True
        else:
            portfolio_stock.quantity -= quantity
            proc = False
    elif tag_type == "SUBSIDIZED":
        if random.random() < .2:
            total_value = total_value + tag_value
            proc = True
        else:
            portfolio_stock.quantity -= quantity
            proc = False
    elif tag_type == "GLITCHED":
        print("Entering GLITCHED tag logic")
        if random.random() < 0.1:
            print("GLITCHED effect triggered")
            with transaction.atomic():
                old_quantity = portfolio_stock.quantity
                new_quantity = old_quantity - quantity
                old_purchase_price = portfolio_stock.purchase_price
                old_stock = portfolio_stock.stock
                print(f"Old quantity: {old_quantity}, New quantity: {new_quantity}")

                new_stock = Stock.objects.filter(industry=old_stock.industry).exclude(id=old_stock.id).order_by('?').first()
                if new_stock:
                    print(f"Replacing with glitched stock: {new_stock.symbol}")
                    # Delete the old stock entirely
                    print(f"Deleting original stock: {portfolio_stock.stock.symbol}")
                    portfolio_stock.delete()

                    # Create new stock with the new quantity
                    glitched_stock = PersistentPortfolioStock.objects.create(
                        portfolio=persistent_portfolio,
                        stock=new_stock,
                        quantity=new_quantity,
                        purchase_price=old_purchase_price
                    )
                    tag, _ = Tag.objects.get_or_create(tag_type="GLITCHED", value=1)
                    glitched_stock.tags.add(tag)
                    proc = True
                    
                    # Update portfolio_stock reference for the rest of the function
                    portfolio_stock = glitched_stock
                else:
                    print("No new stock found, keeping original stock")
                    portfolio_stock.quantity = new_quantity
                    portfolio_stock.save()
                    proc = False
        else:
            print("GLITCHED effect not triggered")
            portfolio_stock.quantity -= quantity
            portfolio_stock.save()
            proc = False
        print(f"GLITCHED logic completed. Proc: {proc}")

    else:
        portfolio_stock.quantity -= quantity

    profile.moqs += total_value
    if portfolio_stock.quantity == 0:
        portfolio_stock.delete()
    else:
        portfolio_stock.save()
    profile.save()
    return Response({'success': 'Stock sold successfully', 'proc': proc}, status=status.HTTP_200_OK)

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
    
    # Get the tags from the inventory stock
    tags = inventory_stock.tags.all()
    
    # Add to persistent portfolio without deducting MOQs
    portfolio_stock, created = PersistentPortfolioStock.objects.get_or_create(
        portfolio=persistent_portfolio,
        stock=stock,
        defaults={
            'quantity': quantity,
            'purchase_price': stock.current_price,
        }
    )
    
    if not created:
        portfolio_stock.quantity += quantity
        portfolio_stock.save()
    
    # Set the tags for the persistent portfolio stock
    portfolio_stock.tags.set(tags)
    
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
        inventory_stock = InventoryStock.objects.create(
            user=request.user,
            symbol=listing.stock.symbol,
            name=listing.stock.name,
            industry=listing.stock.industry,
            current_price=listing.stock.current_price,
        )
        
        # Copy tags from listing to inventory_stock
        inventory_stock.tags.set(listing.tags.all())

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