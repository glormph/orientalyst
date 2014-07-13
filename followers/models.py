from django.db import models
from accounts.models import Person


class FollowRelation(models.Model):
    followed = models.ForeignKey(Person)
    follower = models.ForeignKey(Person)
