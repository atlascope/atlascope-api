from django.db import models
from django.contrib import admin

from uuid import uuid4


class ContextMap(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    datasets = models.ManyToManyField('Dataset', related_name='context_datasets')


@admin.register(ContextMap)
class ContextMapAdmin(admin.ModelAdmin):
    pass
