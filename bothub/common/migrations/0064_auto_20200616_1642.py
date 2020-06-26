# Generated by Django 2.2.12 on 2020-06-16 19:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("common", "0063_repositoryqueuetask")]

    operations = [
        migrations.AlterField(
            model_name="repositoryqueuetask",
            name="status",
            field=models.PositiveIntegerField(
                choices=[
                    (0, "Pending"),
                    (2, "Success"),
                    (1, "Training"),
                    (3, "Failed"),
                ],
                default=0,
                verbose_name="Status Queue NLP",
            ),
        )
    ]
