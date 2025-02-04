from django.contrib import admin
from django.contrib.gis.db import models as gis_models
from django.db import models


class Waypoint(models.Model):
    location = gis_models.PointField(null=True)
    zoom = models.IntegerField(null=True)
    description = models.TextField(max_length=5000, blank=True, null=True)


admin.site.register(Waypoint)
