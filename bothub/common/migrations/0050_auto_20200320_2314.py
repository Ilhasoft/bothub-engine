# Generated by Django 2.1.11 on 2020-03-20 23:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("common", "0049_repositoryexample_is_corrected")]

    operations = [
        migrations.AlterField(
            model_name="repositoryevaluateresultscore",
            name="support",
            field=models.FloatField(null=True),
        )
    ]
