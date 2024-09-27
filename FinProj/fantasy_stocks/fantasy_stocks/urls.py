"""
URL configuration for fantasy_stocks project.

The `urlpatterns` list routes URLs to views. For more information please see:
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
from stocks.views import AvailableStocksView
from stocks.views import DraftStockView
from stocks.views import PortfolioView
from leagues.views import LeagueViewSet
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.urls import path
from stocks.views import LeaderboardView

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
    path('api/leaderboard/', LeaderboardView.as_view()),
    # ... other urls ...
]
