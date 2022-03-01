# Generated by Django 3.2.11 on 2022-02-28 14:39

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_pin_modification'),
    ]

    operations = [
        migrations.RenameField(
            model_name='pin',
            old_name='child_dataset',
            new_name='child',
        ),
        migrations.RenameField(
            model_name='pin',
            old_name='location',
            new_name='child_location',
        ),
        migrations.RenameField(
            model_name='pin',
            old_name='parent_dataset',
            new_name='parent',
        ),
        migrations.RemoveField(
            model_name='datasetembedding',
            name='context',
        ),
        migrations.RemoveField(
            model_name='investigation',
            name='pins',
        ),
        migrations.AddField(
            model_name='datasetembedding',
            name='investigation',
            field=models.ForeignKey(
                default=None,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='embeddings',
                to='core.investigation',
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='job',
            name='investigation',
            field=models.ForeignKey(
                default=None,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='jobs',
                to='core.investigation',
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='job',
            name='resulting_datasets',
            field=models.ManyToManyField(related_name='origin', to='core.Dataset'),
        ),
        migrations.AddField(
            model_name='pin',
            name='investigation',
            field=models.ForeignKey(
                default=None,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='pins',
                to='core.investigation',
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='investigation',
            name='datasets',
            field=models.ManyToManyField(related_name='investigations', to='core.Dataset'),
        ),
        migrations.AlterField(
            model_name='job',
            name='original_dataset',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, related_name='jobs', to='core.dataset'
            ),
        ),
    ]
