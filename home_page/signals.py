# home_page/signals.py
from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from .models import StudentProfile

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """Create or update StudentProfile when User is saved"""
    if created:
        # Create new profile for new user
        StudentProfile.objects.create(user=instance)
    else:
        # Update existing profile when user is updated
        try:
            instance.profile.save()
        except StudentProfile.DoesNotExist:
            # In case profile was deleted, create it again
            StudentProfile.objects.create(user=instance)