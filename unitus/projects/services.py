"""
Application-level replacement for the reverted MySQL triggers
(see projects/migrations/0002_add_project_triggers.py, reverted in 0003).

Call sync_job_ad_status_for_role() any time a ProjectMember's status or role
changes for a project still in RECRUITING - e.g. after removing a member here,
or after a collaboration.Ticket gets accepted and creates a ProjectMember.
"""
from .models import JobAd, ProjectMember


def sync_job_ad_status_for_role(role):
    try:
        job_ad = role.jobad
    except JobAd.DoesNotExist:
        return

    # Once a job ad is cancelled (project left RECRUITING), never reopen it.
    if job_ad.status == JobAd.Status.CANCELLED:
        return

    active_count = ProjectMember.objects.filter(
        project_role=role, member_status=ProjectMember.MemberStatus.ACTIVE
    ).count()

    new_status = JobAd.Status.FILLED if active_count >= role.capacity else JobAd.Status.OPEN
    if job_ad.status != new_status:
        job_ad.status = new_status
        job_ad.save(update_fields=['status'])
