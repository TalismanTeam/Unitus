from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User, UserPrivacySettings

@receiver(post_save, sender=User)
def create_user_privacy_settings(sender, instance, created, **kwargs):
# Creates a default privacy settings record whenever a new user is created.
    if created:
        UserPrivacySettings.objects.get_or_create(user=instance)