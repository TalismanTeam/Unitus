"""
Roles (Project Manager / Team Member) are dynamic per-project, not static
Django Groups. These helpers answer "does this user have this relationship
to this project" and are used across projects/collaboration/reviews views.
"""
from .models import ProjectMember


def is_project_pm(user, project):
    return user.is_authenticated and project.pm_id == user.id


def is_active_member(user, project):
    if not user.is_authenticated:
        return False
    return ProjectMember.objects.filter(
        project=project, user=user, member_status=ProjectMember.MemberStatus.ACTIVE
    ).exists()


def can_view_workspace(user, project):
    """Full project details are only visible to the PM and active members (SRS 3.4)."""
    return is_project_pm(user, project) or is_active_member(user, project)
