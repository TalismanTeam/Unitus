"""
Manual JSON serialization helpers for the skills app - no DRF, matches the
pattern established in accounts/serialization.py.
"""


def serialize_skill_category(category):
    return {
        "id": category.id,
        "category_name": category.category_name,
    }


def serialize_skill(skill):
    return {
        "id": skill.id,
        "name": skill.name,
        "category": skill.category_id,
        "category_name": skill.category.category_name,
        "is_custom": skill.is_custom,
        "is_approved": skill.is_approved,
        "created_by": skill.created_by_id,
    }
