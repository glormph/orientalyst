from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save

class UserProfile(models.Model):
    user = models.ForeignKey(User)
    eventor_id = models.IntegerField()

class UrlLogin(models.Model):
    user = models.ForeignKey(User)
    randomid = models.CharField(max_length=30)
    timestamp = models.DateTimeField()
    firsttime = models.BooleanField()

class Person(models.Model):
    eventor_id = models.IntegerField()
    firstname = models.CharField(max_length=40)
    lastname = models.CharField(max_length=40)
    user = models.ForeignKey(User)


class Si(models.Model):
    si = models.IntegerField(null=True)
    person = models.ForeignKey(Person)


class Event(models.Model):
    name = models.CharField(max_length=100)
    startdate = models.DateField(null=True)
    eventor_id = models.IntegerField(null=True)


class Classrace(models.Model):
    event = models.ForeignKey(Event)
    startdate = models.DateField(null=True)
    classname = models.CharField(max_length=20)
    racetype = models.CharField(max_length=40)
    lightcondition = models.CharField(max_length=40)
    name = models.CharField(max_length=200)


class PersonRun(models.Model):
    person = models.ForeignKey(Person)
    # I removed SI from table since I'm not sure it can be retrieved from
    # results xml
    classrace = models.ForeignKey(Classrace)


class Result(models.Model):
    classrace = models.ForeignKey(Classrace)
    person_eventor_id = models.CharField(max_length=20)
    firstname = models.CharField(max_length=100)
    lastname = models.CharField(max_length=100)
    position = models.IntegerField(null=True)
    time = models.CharField(max_length=20)
    status = models.CharField(max_length=40)
    diff = models.CharField(max_length=20)


class Split(models.Model):
    result = models.ForeignKey(Result)
    split_n = models.IntegerField()
    splittime = models.CharField(max_length=20)

