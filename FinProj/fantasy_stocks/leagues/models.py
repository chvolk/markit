from django.db import models
from django.contrib.auth.models import User

class League(models.Model):
    name = models.CharField(max_length=100)
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_leagues')
    members = models.ManyToManyField(User, related_name='joined_leagues')
    start_date = models.DateField()
    end_date = models.DateField()
    max_members = models.IntegerField(default=10)

    def __str__(self):
        return self.name