from django.db import models
from accounts.models import Person


class Following(models.Model):
    followed = models.ForeignKey(Person)
    follower = models.ForeignKey(Person)
