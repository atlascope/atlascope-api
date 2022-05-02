# Generated by Django 3.2.13 on 2022-04-26 17:01

from django.db import migrations, models
import django.db.models.expressions


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_base_models'),
    ]

    operations = [
        migrations.AddField(
            model_name='pin',
            name='maximum_zoom',
            field=models.PositiveIntegerField(default=40),
        ),
        migrations.AddField(
            model_name='pin',
            name='minimum_zoom',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddConstraint(
            model_name='pin',
            constraint=models.CheckConstraint(
                check=models.Q(
                    ('maximum_zoom__gte', django.db.models.expressions.F('minimum_zoom'))
                ),
                name='valid_zoom_range',
            ),
        ),
    ]
