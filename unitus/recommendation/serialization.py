def serialize_feedback(feedback):
    return {
        "id": feedback.id,
        "recommendation_type": feedback.recommendation_type,
        "target_id": feedback.target_id,
        "vote": feedback.vote,
        "updated_at": feedback.updated_at,
    }


def serialize_preferences(preferences):
    return {
        "min_match_score": preferences.min_match_score,
        "excluded_category_ids": list(
            preferences.excluded_categories.values_list("id", flat=True)
        ),
        "updated_at": preferences.updated_at,
    }
