from django.db import models
from accounts.models import User
from .choices import MasteryLevel  


class SkillCategory(models.Model):
    category_name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.category_name


class Skill(models.Model):
    category = models.ForeignKey(SkillCategory, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    is_custom = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    is_approved = models.BooleanField(
        default=True,
        help_text='Custom skill suggestions start unapproved and are hidden from the public catalog until an admin approves them.',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['category', 'name'], name='unique_skill_per_category')
        ]

    def __str__(self):
        return self.name


class UserSkill(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    mastery_level = models.CharField(max_length=15, choices=MasteryLevel.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'skill'], name='unique_user_skill_pk')
        ]

    def __str__(self):
        return f'{self.user.username} - {self.skill.name} ({self.get_mastery_level_display()})'