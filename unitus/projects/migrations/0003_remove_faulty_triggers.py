from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0002_add_project_triggers'), # نام مایگریشن قبلی
    ]

    operations = [
        migrations.RunSQL("DROP TRIGGER IF EXISTS trg_project_members_after_insert;"),
        migrations.RunSQL("DROP TRIGGER IF EXISTS trg_project_members_after_update;"),
        migrations.RunSQL("DROP TRIGGER IF EXISTS trg_projects_after_update;"),
    ]