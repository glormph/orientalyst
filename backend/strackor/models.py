from django.db import models


class Club(models.Model):
    name = models.TextField()
    eventor_id = models.IntegerField()


class ApiKey(models.Model):
    apikey = models.TextField()
    club = models.ForeignKey(Club)


class Competitor(models.Model):
    name = models.TextField()
    eventor_id = models.IntegerField()
    club = models.ForeignKey(Club)


class Event(models.Model):
    # Can be multi day
    name = models.TextField()
    eventor_id = models.IntegerField()


class RaceType(models.Model):
    # e.g. longdistance, medel, night, relay, sprint, etc 
    # think about this, some races can have multiple types?
    # maybe hard to categorize?
    # FIXME need eventor id? exist?
    name = models.TextField()


class Race(models.Model):
    # One time race (can be part of multi-day)
    name = models.TextField()
    type = models.ForeignKey(RaceType)
    event = models.ForeignKey(Event)
    eventor_id = models.IntegerField()


class RaceClass(models.Model):
    # E.g H21, Motion, Nyborjare (classes)
    name = models.TextField()
    race = models.ForeignKey(Race)


class RaceResult(models.Model):
    raceclass = models.ForeignKey(RaceClass)
    competitor = models.ForeignKey(Competitor)
    race = models.ForeignKey(Race)
    position = models.IntegerField()
    starttime = models.TimeField()
    endtime = models.TimeField()


class Stracka(models.Model):
    race = models.ForeignKey(Race)
    number = models.IntegerField()
    startpost = models.IntegerField()
    endpost = models.IntegerField()


class StrackResult(models.Model):
    stracka = models.ForeignKey(Stracka)
    raceres = models.ForeignKey(RaceResult)
    starttime = models.TimeField()
    endtime = models.TimeField()
    time = models.IntegerField() # in seconds
    rank = models.IntegerField()


class OLSkill(models.Model):
    # vagval, plan, ut, visualize, readahead, etc
    name = models.TextField()


class StrackOverallComment(models.Model):
    strackres = models.ForeignKey(StrackResult)
    happy = models.IntegerField() # 1-3 no, hm, yes
    remark = models.TextField()
    posttypetags = models.JSONField() # maybe JSON field: [gront, detailed, from above, below, diffust, clear]


class StrackRating(models.Model):
    strackres = models.ForeignKey(StrackResult)
    skill = models.ForeignKey(OLSkill)
    rating = models.IntegerField() # 1-5 (shite, bad, not great, ok, good, awesome)


class StrackComment(models.Model):
    strackres = models.ForeignKey(StrackResult)
    skill = models.ForeignKey(OLSkill)
    text = models.TextField()
