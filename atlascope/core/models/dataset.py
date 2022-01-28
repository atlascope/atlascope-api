from uuid import uuid4

from django.conf import settings
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db import models
from guardian.admin import GuardedModelAdmin
from rest_framework import serializers
from s3_file_field import S3FileField

from .importer import importers


def validate_importer(value):
    if value in importers:
        return value
    else:
        raise ValidationError(
            f'Importer value must be '
            f'one of the following installed importers'
            f': {str(list(importers.keys()))}'
        )


class Dataset(models.Model):
    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(content__isnull=False) | models.Q(importer__isnull=False),
                name='has_no_source',
            )
        ]

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(max_length=5000, blank=True)
    public = models.BooleanField(default=True)
    importer = models.CharField(max_length=100, null=True, validators=[validate_importer])
    content = S3FileField(null=True)
    extension = models.CharField(max_length=20, default='file')
    metadata = models.JSONField(null=True)
    dataset_type = models.CharField(
        max_length=20,
        choices=[(choice, choice) for choice in settings.DATASET_TYPES],
        default=settings.DATASET_TYPES[0],
    )
    derived_datasets = models.ManyToManyField('Dataset', blank=True)
    # scale
    # applicable_heuristics

    def get_read_permission_groups():
        return ['view_dataset', 'change_dataset']

    def get_write_permission_groups():
        return ['change_dataset']

    def perform_import(self, **kwargs):
        importer = importers[self.importer]()
        importer.run(**kwargs)

        self.content.save(
            f'{self.name.replace(" ","_")}.{self.extension}',
            importer.content,
        )
        self.metadata = importer.metadata


class DatasetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dataset
        fields = '__all__'


class DatasetCreateUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dataset
        fields = [
            'name',
            'description',
            'public',
            'content',
            'metadata',
            'dataset_type',
        ]


class DatasetCreateImportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dataset
        fields = [
            'name',
            'description',
            'public',
            'importer',
            'importer_arguments',
            'extension',
            'dataset_type',
        ]

    importer_arguments = serializers.JSONField(
        help_text="Any arguments to supply to the selected importer function"
    )


@admin.register(Dataset)
class DatasetAdmin(GuardedModelAdmin):
    list_display = ('id', 'name')
