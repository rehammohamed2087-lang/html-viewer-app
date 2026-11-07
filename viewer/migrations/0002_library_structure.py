import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("viewer", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="AccessCode",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=40, unique=True)),
                ("label", models.CharField(blank=True, max_length=100)),
                ("is_active", models.BooleanField(default=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("last_used_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="SiteSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("site_name", models.CharField(default="مكتبة الدروس", max_length=80)),
                ("whatsapp_number", models.CharField(blank=True, max_length=30)),
                ("whatsapp_message", models.CharField(default="السلام عليكم، أريد كود الدخول لمشاهدة الملفات.", max_length=200)),
            ],
        ),
        migrations.CreateModel(
            name="Stage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, unique=True)),
                ("order", models.PositiveIntegerField(default=0)),
            ],
            options={"ordering": ["order", "id"]},
        ),
        migrations.CreateModel(
            name="Subject",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("order", models.PositiveIntegerField(default=0)),
                ("stage", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="subjects", to="viewer.stage")),
            ],
            options={"ordering": ["order", "id"]},
        ),
        migrations.AddConstraint(
            model_name="subject",
            constraint=models.UniqueConstraint(fields=("stage", "name"), name="uniq_subject_per_stage"),
        ),
        migrations.AddField(
            model_name="htmlpage",
            name="is_free",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="htmlpage",
            name="subject",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="pages", to="viewer.subject"),
        ),
    ]
