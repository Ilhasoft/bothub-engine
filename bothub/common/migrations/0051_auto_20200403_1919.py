# Generated by Django 2.1.11 on 2020-04-03 22:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("common", "0050_auto_20200320_2314")]

    operations = [
        migrations.AlterField(
            model_name="repositoryauthorization",
            name="role",
            field=models.PositiveIntegerField(
                choices=[
                    (0, "not set"),
                    (1, "user"),
                    (2, "contributor"),
                    (3, "admin"),
                    (4, "translate"),
                ],
                default=0,
                verbose_name="role",
            ),
        )
    ]
