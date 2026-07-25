from django.db import migrations


def backfill_pm_membership(apps, schema_editor):
    Project = apps.get_model('projects', 'Project')
    ProjectMember = apps.get_model('projects', 'ProjectMember')

    for project in Project.objects.all():
        ProjectMember.objects.get_or_create(
            project=project,
            user=project.pm,
            defaults={'member_status': 'ACTIVE'},
        )


def noop_reverse(apps, schema_editor):
    # Deliberately not reversed: we don't want to delete a PM's membership
    # row on migrate-back, since by then it may be indistinguishable from a
    # legitimately-earned membership (e.g. if they also joined as a normal
    # team member some other way).
    pass


class Migration(migrations.Migration):

    # PLACEHOLDER — replace with your actual latest migration in the
    # projects app (check projects/migrations/ for the highest-numbered
    # file) before running this.
    dependencies = [
        ('projects', '0003_remove_faulty_triggers'),
    ]

    operations = [
        migrations.RunPython(backfill_pm_membership, noop_reverse),
    ]
