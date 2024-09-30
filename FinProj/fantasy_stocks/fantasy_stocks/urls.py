"""
URL configuration for fantasy_stocks project.

The `urlpatterns` list routes URLs to  For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from rest_framework.routers import DefaultRouter
from django.urls import path, include
from accounts.views import CustomAuthToken, LogoutView, SignupView
from stocks.views import DraftStockView, AvailableStocksView, PortfolioView, PortfolioHistoryView, LeaderboardView, SellStockView
from leagues.views import LeagueViewSet
from bazaar.views import (
    BuyStockView, SellStockView, AddToInventoryView, BuyPackView, CancelListingView,
    ListStockView, EditListingView, BuyListedStockView, bazaar_data, buy_persistent_stock, persistent_portfolio_data, sell_persistent_stock, lock_in_persistent_stock, 
)
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

router = DefaultRouter()
router.register(r'leagues', LeagueViewSet, basename='league')

@csrf_exempt
def test_cors(request):
    return JsonResponse({"message": "CORS is working"})

urlpatterns = [
    path('api/', include(router.urls)),
    path('admin/', admin.site.urls),
    path('api/login/', CustomAuthToken.as_view()),
    path('api/logout/', LogoutView.as_view()),
    path('api/stocks/draft/', DraftStockView.as_view()),
    path('api/signup/', SignupView.as_view()),
    path('api/stocks/available/', AvailableStocksView.as_view()),
    path('api/test-cors/', test_cors),
    path('api/portfolio/', PortfolioView.as_view()),
    path('api/portfolio-history/', PortfolioHistoryView.as_view(), name='portfolio-history'),
    path('api/leaderboard/', LeaderboardView.as_view()),
    path('api/sell/', SellStockView.as_view()),
    
    # Bazaar URLs
    path('api/bazaar/', bazaar_data, name='bazaar-data'),
    path('api/bazaar/buy-stock/', BuyStockView.as_view(), name='buy-stock'),
    path('api/bazaar/sell-stock/', SellStockView.as_view(), name='sell-stock'),
    path('api/bazaar/add-to-inventory/', AddToInventoryView.as_view(), name='add-to-inventory'),
    path('api/bazaar/buy-pack/', BuyPackView.as_view(), name='buy-pack'),
    path('api/bazaar/list-stock/', ListStockView.as_view(), name='list-stock'),
    path('api/bazaar/edit-listing/<int:listing_id>/', EditListingView.as_view(), name='edit-listing'),
    path('api/bazaar/buy-listed-stock/', BuyListedStockView.as_view(), name='buy-listed-stock'),
    path('api/persistent-portfolio/', persistent_portfolio_data, name='persistent_portfolio_data'),
    path('api/persistent-portfolio/buy/', buy_persistent_stock, name='buy_persistent_stock'),
    path('api/persistent-portfolio/sell/', sell_persistent_stock, name='sell_persistent_stock'),
    path('api/persistent-portfolio/lock-in/', lock_in_persistent_stock, name='lock_in_persistent_stock'),
    path('api/bazaar/cancel-listing/', CancelListingView.as_view(), name='cancel-listing'),
]
