from django.db import models

class FetchresultsRunning(models.Model):
    pid = models.IntegerField()


class FetchRecentResultsTickets(models.Model):
    is_download_time = models.BooleanField()


class FetchPersonResultsTickets(models.Model):
    eventor_id = models.IntegerField()

