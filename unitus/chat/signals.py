from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from projects.models import Project, ProjectMember

from . import services


@receiver(pre_save, sender=Project)
def _capture_old_project_state(sender, instance, **kwargs):
    """Stashes the state BEFORE this save, so post_save can detect a transition."""
    if instance.pk:
        try:
            instance._old_state = Project.objects.only('state').get(pk=instance.pk).state
        except Project.DoesNotExist:
            instance._old_state = None
    else:
        instance._old_state = None


@receiver(post_save, sender=Project)
def _handle_project_state_change(sender, instance, created, **kwargs):
    if created:
        return  # a brand-new project can't already be IN_PROGRESS/TERMINATED

    old_state = getattr(instance, '_old_state', None)

    if old_state != 'IN_PROGRESS' and instance.state == 'IN_PROGRESS':
        services.open_group_chat_for_project(instance)

    if old_state != 'TERMINATED' and instance.state == 'TERMINATED':
        services.close_group_chat_for_project(instance)


@receiver(post_save, sender=ProjectMember)
def _handle_project_member_change(sender, instance, **kwargs):
    services.sync_participant_for_membership_change(
        instance.project, instance.user_id, instance.member_status
    )