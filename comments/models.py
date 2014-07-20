from django.db import models
from django.forms import ModelForm
from accounts.models import Person
from graphs.models import Classrace


class Comment(models.Model):
    commenttext = models.TextField(verbose_name='Din kommentar')
    author = models.ForeignKey(Person)
    classrace = models.ForeignKey(Classrace)
    created = models.DateTimeField(auto_now_add=True)


class CommentForm(ModelForm):
    class Meta:
        model = Comment
        fields = ['commenttext']
