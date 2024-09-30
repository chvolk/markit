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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def bazaar_data(request):
    user = request.user
    profile, created = BazaarUserProfile.objects.get_or_create(user=user, defaults={'moqs': 1000})
    portfolio = get_object_or_404(Portfolio, user=user)
    
    available_gains = max(0, portfolio.balance - 50000)  # Assuming starting balance is 50000
    
    inventory = InventoryStock.objects.filter(user=user)
    market_listings = BazaarListing.objects.exclude(seller=user)
    user_listings = BazaarListing.objects.filter(seller=user)
    
    return Response({
        'available_gains': available_gains,
        'total_moqs': profile.moqs,
        'inventory': InventoryStockSerializer(inventory, many=True).data,
        'market_listings': BazaarListingSerializer(market_listings, many=True).data,
        'user_listings': BazaarListingSerializer(user_listings, many=True).data,
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
        
        portfolio.save()
        
        return Response({"message": f"{quantity} shares of {symbol} sold successfully"})

class AddToInventoryView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        symbol = request.data.get('symbol')
        stock = get_object_or_404(Stock, symbol=symbol)
        
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
        
        # Add to persistent portfolio
        persistent_portfolio, _ = PersistentPortfolio.objects.get_or_create(user=request.user)
        portfolio_stock, created = PersistentPortfolioStock.objects.get_or_create(
            portfolio=persistent_portfolio,
            stock=stock,
            defaults={'quantity': 1, 'purchase_price': 0}
        )
        
        if not created:
            portfolio_stock.quantity += 1
            portfolio_stock.save()
        
        serializer = InventoryStockSerializer(inventory_stock)
        return Response({
            'inventory_stock': serializer.data,
            'persistent_portfolio_stock': {
                'symbol': stock.symbol,
                'quantity': portfolio_stock.quantity,
                'purchase_price': float(portfolio_stock.purchase_price)
            }
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

class BuyPackView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        currency = request.data.get('currency')
        if currency not in ['gains', 'moqs']:
            return Response({"error": "Invalid currency"}, status=status.HTTP_400_BAD_REQUEST)
        
        profile = get_object_or_404(BazaarUserProfile, user=request.user)
        portfolio = get_object_or_404(Portfolio, user=request.user)
        
        pack_price = 1000 if currency == 'gains' else 100  # Example prices
        
        if currency == 'gains' and portfolio.balance < pack_price:
            return Response({"error": "Insufficient gains"}, status=status.HTTP_400_BAD_REQUEST)
        elif currency == 'moqs' and profile.moqs < pack_price:
            return Response({"error": "Insufficient moqs"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get all industries that have at least 5 stocks
        industries = Stock.objects.values('industry').annotate(
            count=Count('industry')
        ).filter(count__gte=5)
        
        if not industries:
            return Response({"error": "No industries with enough stocks available"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Randomly select an industry
        selected_industry = choice(industries)['industry']
        
        # Get 5 random stocks from the selected industry
        industry_stocks = list(Stock.objects.filter(industry=selected_industry))
        selected_pack_stocks = random.sample(industry_stocks, min(5, len(industry_stocks)))
        print("Pack stocks picked:")
        for stock in selected_pack_stocks:
            print(f"Symbol: {stock.symbol}, Name: {stock.name}, Industry: {stock.industry}")
        persistent_portfolio, _ = PersistentPortfolio.objects.get_or_create(user=request.user)
        
        pack_stocks = []
        for stock in selected_pack_stocks:
            pack_stocks.append({
                'symbol': stock.symbol,
                'name': stock.name,
                'industry': stock.industry,
                'current_price': stock.current_price
            })
        print("Pack stocks before sending to frontend:")
        print(pack_stocks)
        if currency == 'gains':
            portfolio.balance -= pack_price
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

    def post(self, request):
        stock_id = request.data.get('stock_id')
        price = request.data.get('price')
        
        inventory_stock = get_object_or_404(InventoryStock, id=stock_id, user=request.user)
        
        listing = BazaarListing.objects.create(
            seller=request.user,
            stock=inventory_stock,
            price=price
        )
        
        serializer = BazaarListingSerializer(listing)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

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
        
        buyer_profile = get_object_or_404(BazaarUserProfile, user=request.user)
        
        if buyer_profile.moqs < listing.price:
            return Response({"error": "Insufficient moqs"}, status=status.HTTP_400_BAD_REQUEST)
        
        buyer_profile.moqs -= listing.price
        buyer_profile.save()
        
        seller_profile = get_object_or_404(BazaarUserProfile, user=listing.seller)
        seller_profile.moqs += listing.price
        seller_profile.save()
        
        # Transfer the stock to the buyer's inventory
        InventoryStock.objects.create(
            user=request.user,
            symbol=listing.stock.symbol,
            name=listing.stock.name,
            industry=listing.stock.industry,
            current_price=listing.stock.current_price
        )
        
        # Remove the stock from the seller's inventory and delete the listing
        listing.stock.delete()
        listing.delete()
        
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
    for stock in stocks:
        print(f"Stock: {stock.stock.symbol}, Quantity: {stock.quantity}, Purchase Price: {stock.purchase_price}")
    
    serialized_data = PersistentPortfolioStockSerializer(stocks, many=True).data
    print("Serialized Data:", serialized_data)
    
    return Response({
        'available_moqs': profile.moqs,
        'stocks': serialized_data,
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def buy_persistent_stock(request):
    user = request.user
    symbol = request.data.get('symbol')
    quantity = int(request.data.get('quantity', 0))
    
    if not symbol or quantity <= 0:
        return Response({'error': 'Invalid data'}, status=status.HTTP_400_BAD_REQUEST)
    
    profile = get_object_or_404(BazaarUserProfile, user=user)
    stock = get_object_or_404(Stock, symbol=symbol)
    persistent_portfolio, created = PersistentPortfolio.objects.get_or_create(user=user)
    
    total_cost = stock.current_price * quantity
    
    if profile.moqs < total_cost:
        return Response({'error': 'Not enough Moqs'}, status=status.HTTP_400_BAD_REQUEST)
    
    portfolio_stock, created = PersistentPortfolioStock.objects.get_or_create(
        portfolio=persistent_portfolio,
        stock=stock,
        defaults={'quantity': 0, 'purchase_price': stock.current_price}
    )
    
    portfolio_stock.quantity += quantity
    portfolio_stock.save()
    
    profile.moqs -= total_cost
    profile.save()
    
    return Response({'success': 'Stock purchased successfully'}, status=status.HTTP_200_OK)

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