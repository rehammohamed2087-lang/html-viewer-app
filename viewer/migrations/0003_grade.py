import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("viewer", "0002_library_structure"),
    ]

    operations = [
        migrations.CreateModel(
            name="Grade",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("order", models.PositiveIntegerField(default=0)),
                ("stage", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="grades", to="viewer.stage")),
            ],
            options={"ordering": ["order", "id"]},
        ),
        migrations.AddConstraint(
            model_name="grade",
            constraint=models.UniqueConstraint(fields=("stage", "name"), name="uniq_grade_per_stage"),
        ),
        migrations.AddField(
            model_name="subject",
            name="grade",
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name="subjects", to="viewer.grade"),
        ),
    ]
