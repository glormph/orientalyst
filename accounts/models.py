from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.ForeignKey(User)
    eventor_id = models.IntegerField()


class Person(models.Model):
    eventor_id = models.IntegerField()
    firstname = models.CharField(max_length=40)
    lastname = models.CharField(max_length=40)
    email = models.EmailField(null=True)
    user = models.ForeignKey(User, null=True)
    account_status = models.CharField(max_length=20)
    # account status can be ['new', 'active', 'inactive', 'unregistered']


class Si(models.Model):
    si = models.IntegerField(null=True)
    person = models.ForeignKey(Person)
