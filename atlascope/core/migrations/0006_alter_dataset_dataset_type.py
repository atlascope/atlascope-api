# Generated by Django 3.2.12 on 2022-02-24 22:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_embeddings'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dataset',
            name='dataset_type',
            field=models.CharField(choices=[('tile_source', 'tile_source'), ('tile_overlay', 'tile_overlay'), ('analytics', 'analytics'), ('sub_image', 'sub_image')], default='tile_source', max_length=20),
        ),
    ]
