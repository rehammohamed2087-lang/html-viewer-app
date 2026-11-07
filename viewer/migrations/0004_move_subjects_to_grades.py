from django.db import migrations


def forwards(apps, schema_editor):
    """أي مادة موجودة قبل إضافة الصفوف تُنقل لصف اسمه «عام» داخل نفس المرحلة."""
    Subject = apps.get_model("viewer", "Subject")
    Grade = apps.get_model("viewer", "Grade")
    for s in Subject.objects.all():
        grade, _ = Grade.objects.get_or_create(stage_id=s.stage_id, name="عام", defaults={"order": 0})
        s.grade_id = grade.pk
        s.save(update_fields=["grade"])


class Migration(migrations.Migration):

    dependencies = [
        ("viewer", "0003_grade"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
