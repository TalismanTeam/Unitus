from django.db import models
from accounts.models import User
from skills.models import Skill
from skills.choices import MasteryLevel   


class Project(models.Model):
    class State(models.TextChoices):
        RECRUITING = 'RECRUITING'
        IN_PROGRESS = 'IN_PROGRESS'
        SUSPENDED = 'SUSPENDED'
        TERMINATED = 'TERMINATED'

    class TerminationReason(models.TextChoices):
        SUCCESS = 'SUCCESS'
        TEAM_ISSUES = 'TEAM_ISSUES'
        TEAM_FAILURE = 'TEAM_FAILURE'
        PM_CANCELED = 'PM_CANCELED'
        OTHER = 'OTHER'

    pm = models.ForeignKey(User, on_delete=models.PROTECT, related_name='managed_projects')
    title = models.CharField(max_length=100)
    short_description = models.CharField(max_length=255)
    full_description = models.TextField()
    duration_days = models.IntegerField()
    state = models.CharField(max_length=15, choices=State.choices, default=State.RECRUITING, db_index=True)
    termination_reason = models.CharField(max_length=15, choices=TerminationReason.choices, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(state='TERMINATED', termination_reason__isnull=False) |
                    (~models.Q(state='TERMINATED') & models.Q(termination_reason__isnull=True))
                ),
                name='chk_termination_reason'
            )
        ]

    def __str__(self):
        return self.title


class ProjectRole(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    role_title = models.CharField(max_length=50)
    role_description = models.TextField()
    capacity = models.SmallIntegerField()

    def __str__(self):
        return f'{self.role_title} ({self.project.title})'


class ProjectRoleSkill(models.Model):
    role = models.ForeignKey(ProjectRole, on_delete=models.CASCADE)
    skill = models.ForeignKey(Skill, on_delete=models.RESTRICT)
    min_required_level = models.CharField(max_length=15, choices=MasteryLevel.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['role', 'skill'], name='unique_role_skill_pk')
        ]

    def __str__(self):
        return f'{self.role.role_title} needs {self.skill.name} ({self.get_min_required_level_display()})'


class JobAd(models.Model):
    class Status(models.TextChoices):
        OPEN = 'OPEN'
        FILLED = 'FILLED'
        CANCELLED = 'CANCELLED'

    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    project_role = models.OneToOneField(ProjectRole, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Job Ad: {self.project_role.role_title} - {self.project.title} ({self.get_status_display()})'


class ProjectMember(models.Model):
    class MemberStatus(models.TextChoices):
        ACTIVE = 'ACTIVE'
        RESIGNED = 'RESIGNED'
        REMOVED = 'REMOVED'

    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.RESTRICT)
    project_role = models.ForeignKey(ProjectRole, on_delete=models.SET_NULL, null=True, blank=True)
    member_status = models.CharField(max_length=10, choices=MemberStatus.choices, default=MemberStatus.ACTIVE)
    joined_at = models.DateTimeField(auto_now_add=True)
    # Lets a user hide an individual role/job-ad from their *public* profile
    # (GET /users/:id) without affecting their own view (GET /users/me) or
    # the project/team itself. Defaults to visible so existing rows aren't
    # silently hidden after migration.
    visible_on_profile = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['project', 'user'], name='unique_project_member_pk')
        ]
        indexes = [
            models.Index(fields=['project_role', 'member_status'])
        ]

    def __str__(self):
        return f'{self.user.username} @ {self.project.title} ({self.get_member_status_display()})'
