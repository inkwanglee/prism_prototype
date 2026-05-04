import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("schemas", "0002_schemaauditlog"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SchemaSnapshot",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "content",
                    models.TextField(
                        help_text="Raw JSON text of Schema.json at this point in time"
                    ),
                ),
                ("saved_at", models.DateTimeField(auto_now_add=True)),
                (
                    "saved_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Schema Snapshot",
                "verbose_name_plural": "Schema Snapshots",
                "ordering": ["-saved_at"],
            },
        ),
    ]
