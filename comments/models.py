from django.db import models
from accounts.models import Person
from graphs.models import Classrace


class Comment(models.Model):
    commenttext = models.TextField()
    author = models.ForeignKey(Person)
    classrace = models.ForeignKey(Classrace)
    created = models.DateTimeField(auto_add_now=True)
