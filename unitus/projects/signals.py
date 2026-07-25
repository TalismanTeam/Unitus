from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Project, ProjectMember


@receiver(post_save, sender=Project)
def ensure_pm_is_project_member(sender, instance, created, **kwargs):
    """
    A project's PM is a teammate too — every other part of the system
    (ticket approvals, review eligibility, dashboards) treats "was on this
    project" as "has a ProjectMember row". Rather than have every call site
    that creates a Project remember to also add this row, guarantee it here.

    get_or_create as a safety net: if instance.pm is ever reassigned via an
    update (not just initial creation), this keeps the new PM enrolled too
    without erroring on a second post_save if a row already exists.
    """
    ProjectMember.objects.get_or_create(
        project=instance,
        user=instance.pm,
        defaults={'member_status': ProjectMember.MemberStatus.ACTIVE},
    )
