from django.db import models
from accounts.models import Person


class Following(models.Model):
    followed = models.ForeignKey(Person, related_name='folllowing_followed')
    follower = models.ForeignKey(Person, related_name='following_follower')
