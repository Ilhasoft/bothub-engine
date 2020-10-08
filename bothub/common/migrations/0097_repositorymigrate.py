# Generated by Django 2.2.16 on 2020-10-07 16:11

import bothub.common.languages
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("authentication", "0006_auto_20200729_1220"),
        ("common", "0096_auto_20201001_2005"),
    ]

    operations = [
        migrations.CreateModel(
            name="RepositoryMigrate",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "language",
                    models.CharField(
                        max_length=5,
                        validators=[bothub.common.languages.validate_language],
                        verbose_name="language",
                    ),
                ),
                ("auth_token", models.TextField()),
                ("created", models.DateTimeField(auto_now_add=True)),
                (
                    "repository_version",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="repository_migrate",
                        to="common.RepositoryVersion",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="authentication.RepositoryOwner",
                    ),
                ),
            ],
            options={
                "verbose_name": "repository migrate",
                "verbose_name_plural": "repository migrates",
            },
        )
    ]
