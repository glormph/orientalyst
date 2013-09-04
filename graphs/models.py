from django.db import models
from accounts.models import Person

class Event(models.Model):
    name = models.CharField(max_length=100)
    startdate = models.DateField(null=True)
    eventor_id = models.IntegerField(null=True)


class EventRace(models.Model):
    event = models.ForeignKey(Event)
    eventor_id = models.IntegerField(null=True)
    startdate = models.DateField(null=True)
    lightcondition = models.CharField(max_length=40)
    name = models.CharField(max_length=200)
    

class Classrace(models.Model):
    eventrace = models.ForeignKey(EventRace)
    classname = models.CharField(max_length=20)
    racetype = models.CharField(max_length=40)
    

class PersonRun(models.Model):
    person = models.ForeignKey(Person)
    # I removed SI from table since I'm not sure it can be retrieved from
    # results xml
    classrace = models.ForeignKey(Classrace)


class Result(models.Model):
    classrace = models.ForeignKey(Classrace)
    person_eventor_id = models.CharField(max_length=20)
    firstname = models.CharField(max_length=100, null=True)
    lastname = models.CharField(max_length=100, null=True)
    position = models.IntegerField(null=True)
    time = models.CharField(max_length=20)
    status = models.CharField(max_length=40)
    diff = models.CharField(max_length=20)


class Split(models.Model):
    result = models.ForeignKey(Result)
    split_n = models.IntegerField()
    splittime = models.CharField(max_length=20)

