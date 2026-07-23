"""
Manual JSON serialization helpers — no DRF. Each function returns a plain
dict (or None), ready to hand to JsonResponse.
"""

from accounts.models import UserPrivacySettings


def serialize_avatar(avatar):
    if avatar is None:
        return None
    return {
        "id": avatar.id,
        "icon_name": avatar.icon_name,
        "image_url_path": avatar.image_url_path,
    }


def serialize_privacy_settings(settings_obj):
    if settings_obj is None:
        return None
    return {
        "show_phone": settings_obj.show_phone,
        "show_email": settings_obj.show_email,
        "show_location": settings_obj.show_location,
        "show_birth_year": settings_obj.show_birth_year,
        "show_education_background": settings_obj.show_education_background,
        "show_gender": settings_obj.show_gender,
    }


def serialize_user_skill(user_skill):
    return {
        "id": user_skill.id,
        "skill": user_skill.skill_id,
        "skill_name": user_skill.skill.name,
        "category_name": user_skill.skill.category.category_name,
        "mastery_level": user_skill.mastery_level,
    }


def _get_privacy_settings(user):
    try:
        return user.userprivacysettings
    except UserPrivacySettings.DoesNotExist:
        return None


def serialize_me(user):
    """Full private profile — only ever returned to the user themselves."""
    skills = user.userskill_set.select_related("skill", "skill__category").all()
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "gender": user.gender,
        "birth_year": user.birth_year,
        "phone_number": user.phone_number,
        "location": user.location,
        "education_background": user.education_background,
        "is_open_to_work": user.is_open_to_work,
        "account_status": user.account_status,
        "created_at": user.created_at.isoformat(),
        "avatar": serialize_avatar(user.avatar_icon),
        "privacy_settings": serialize_privacy_settings(_get_privacy_settings(user)),
        "skills": [serialize_user_skill(s) for s in skills],
    }


def serialize_public_profile(user):
    """Restricted profile for GET /users/:id — gated by UserPrivacySettings."""
    from django.db.models import Avg
    from projects.models import ProjectMember
    from reviews.models import Review

    privacy = _get_privacy_settings(user)

    def gated(flag_name, field_name):
        if privacy and getattr(privacy, flag_name):
            return getattr(user, field_name)
        return None

    active_projects_count = ProjectMember.objects.filter(
        user=user, member_status="ACTIVE"
    ).exclude(project__state="TERMINATED").count()

    avg = Review.objects.filter(reviewee=user).aggregate(avg=Avg("rating"))["avg"]

    skills = user.userskill_set.select_related("skill", "skill__category").all()

    return {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "avatar": serialize_avatar(user.avatar_icon),
        "gender": gated("show_gender", "gender"),
        "birth_year": gated("show_birth_year", "birth_year"),
        "phone_number": gated("show_phone", "phone_number"),
        "email": gated("show_email", "email"),
        "location": gated("show_location", "location"),
        "education_background": gated("show_education_background", "education_background"),
        "is_open_to_work": user.is_open_to_work,
        "skills": [serialize_user_skill(s) for s in skills],
        "active_projects_count": active_projects_count,
        "avg_rating": round(avg, 2) if avg is not None else None,
    }


def serialize_project_summary(project, viewer):
    return {
        "id": project.id,
        "title": project.title,
        "short_description": project.short_description,
        "state": project.state,
        "duration_days": project.duration_days,
        "created_at": project.created_at.isoformat(),
        "is_pm": project.pm_id == viewer.id,
    }


def serialize_report(report):
    return {
        "id": report.id,
        "reason": report.reason,
        "description": report.description,
        "status": report.status,
        "created_at": report.created_at.isoformat(),
    }
