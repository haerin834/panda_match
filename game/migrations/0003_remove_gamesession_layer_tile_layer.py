# Generated by Django 4.2.7 on 2025-03-05 03:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("game", "0002_gamesession_layer"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="gamesession",
            name="layer",
        ),
        migrations.AddField(
            model_name="tile",
            name="layer",
            field=models.IntegerField(default=0),
        ),
    ]
