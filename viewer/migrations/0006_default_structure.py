from django.db import migrations

from viewer.defaults import ensure_default_structure


def forwards(apps, schema_editor):
    Stage = apps.get_model("viewer", "Stage")
    Grade = apps.get_model("viewer", "Grade")
    ensure_default_structure(Stage, Grade)


class Migration(migrations.Migration):

    dependencies = [
        ("viewer", "0005_subject_grade_required"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
