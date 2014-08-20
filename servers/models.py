from django.db import models


class Compute(models.Model):
    name = models.CharField(max_length=255)
    hostname = models.CharField(max_length=255)
    login = models.CharField(max_length=255)
    password = models.CharField(max_length=255, blank=True, null=True)
    type = models.IntegerField()

    def __unicode__(self):
        return self.hostname
