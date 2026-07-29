from django.utils.timesince import timesince


def serialize_job_ad(ad):
    role = ad.project_role
    project = ad.project

    required_skills = [
        {
            'skill_id': rs.skill_id,
            'skill_name': rs.skill.name,
            'min_required_level': rs.min_required_level,
        }
        for rs in role.projectroleskill_set.select_related('skill').all()
    ]

    return {
        'id': ad.id,
        'role_title': role.role_title,
        'role_description': role.role_description,
        'project_title': project.title,
        'project_short_description': project.short_description,
        'duration_days': project.duration_days,
        'required_skills': required_skills,
        'posted': timesince(ad.created_at) + ' ago',
    }


def serialize_user_result(user, public_fields, skills_qs):
    return {
        'id': user.id,
        'username': public_fields['username'],
        'first_name': public_fields['first_name'],
        'last_name': public_fields['last_name'],
        'location': public_fields['location'],
        'is_open_to_work': public_fields['is_open_to_work'],
        'avatar_icon_name': user.avatar_icon.icon_name if user.avatar_icon_id else None,
        'skills': [
            {'skill_name': s.skill.name, 'mastery_level': s.mastery_level}
            for s in skills_qs
        ],
    }