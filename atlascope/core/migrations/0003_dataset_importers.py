# Generated by Django 4.0 on 2021-12-07 20:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_base_models'),
    ]

    operations = [
        migrations.AddField(
            model_name='dataset',
            name='importer',
            field=models.CharField(choices=[('vandy', 'vandy')], max_length=100, null=True),
        ),
    ]
