from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import League
from .serializers import LeagueSerializer
from stocks.models import Portfolio

# Create your views here.

class LeagueViewSet(viewsets.ModelViewSet):
    serializer_class = LeagueSerializer

    def get_queryset(self):
        return League.objects.filter(members=self.request.user)

    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        league = self.get_object()
        if request.user in league.members.all():
            return Response({'status': 'Already a member'}, status=status.HTTP_400_BAD_REQUEST)
        if league.members.count() >= league.max_members:
            return Response({'status': 'League is full'}, status=status.HTTP_400_BAD_REQUEST)
        league.members.add(request.user)
        return Response({'status': 'Joined league'})

    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        league = self.get_object()
        if request.user not in league.members.all():
            return Response({'status': 'Not a member'}, status=status.HTTP_400_BAD_REQUEST)
        league.members.remove(request.user)
        return Response({'status': 'Left league'})

    @action(detail=True, methods=['get'])
    def leaderboard(self, request, pk=None):
        league = self.get_object()
        leaderboard = []
        for member in league.members.all():
            portfolio = Portfolio.objects.get(user=member)
            leaderboard.append({
                'user': member.username,
                'portfolio_value': portfolio.calculate_value()
            })
        leaderboard.sort(key=lambda x: x['portfolio_value'], reverse=True)
        return Response(leaderboard)
