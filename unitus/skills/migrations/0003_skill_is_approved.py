from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('skills', '0002_seed_categories_and_skills'),
    ]

    operations = [
        migrations.AddField(
            model_name='skill',
            name='is_approved',
            field=models.BooleanField(default=True, help_text='Custom skill suggestions start unapproved and are hidden from the public catalog until an admin approves them.'),
        ),
    ]
