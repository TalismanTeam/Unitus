from django.db import migrations

# Standard, generic behavioral tags — kept short (Tag.name max_length=50) and
# professional, not project-specific. POSITIVE tags are the ones that count
# toward badge unlocking (reviews/views.py::_maybe_award_badge, threshold=5).
POSITIVE_TAGS = [
    'Great Communicator',
    'Reliable',
    'Fast Learner',
    'Strong Team Player',
    'Proactive',
    'Meets Deadlines',
    'High Quality Work',
    'Great Problem Solver',
    'Respectful',
    'Responsive',
    'Went Above and Beyond',
    'Good Leader',
]

NEGATIVE_TAGS = [
    'Poor Communication',
    'Missed Deadlines',
    'Unresponsive',
    'Low Quality Work',
    'Unprofessional Conduct',
    'Difficult to Collaborate With',
    'Disengaged / Inactive',
    'Did Not Follow Instructions',
    'Frequently Absent',
    'Took Credit for Others\' Work',
]


def seed_tags(apps, schema_editor):
    Tag = apps.get_model('reviews', 'Tag')
    for name in POSITIVE_TAGS:
        Tag.objects.get_or_create(name=name, defaults={'tag_type': 'POSITIVE'})
    for name in NEGATIVE_TAGS:
        Tag.objects.get_or_create(name=name, defaults={'tag_type': 'NEGATIVE'})


def reverse_seed(apps, schema_editor):
    Tag = apps.get_model('reviews', 'Tag')
    Tag.objects.filter(name__in=POSITIVE_TAGS + NEGATIVE_TAGS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('reviews', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_tags, reverse_seed),
    ]