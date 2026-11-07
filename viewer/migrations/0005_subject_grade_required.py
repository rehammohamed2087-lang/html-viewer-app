import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("viewer", "0004_move_subjects_to_grades"),
    ]

    operations = [
        migrations.RemoveConstraint(model_name="subject", name="uniq_subject_per_stage"),
        migrations.RemoveField(model_name="subject", name="stage"),
        migrations.AlterField(
            model_name="subject",
            name="grade",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="subjects", to="viewer.grade"),
        ),
        migrations.AddConstraint(
            model_name="subject",
            constraint=models.UniqueConstraint(fields=("grade", "name"), name="uniq_subject_per_grade"),
        ),
    ]
