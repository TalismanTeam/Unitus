def serialize_user_summary(user):
    return {
        'id': user.id,
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
    }


def serialize_project_summary(project):
    return {
        'id': project.id,
        'title': project.title,
        'state': project.state,
    }


def serialize_tag(tag):
    return {
        'id': tag.id,
        'name': tag.name,
        'tag_type': tag.tag_type,
    }


def serialize_review(review, tags):
    """
    tags: iterable of Tag instances already attached to this review (pass
    them in explicitly rather than re-querying per review — callers listing
    many reviews should batch-fetch ReviewTag rows once and group them).
    """
    return {
        'id': review.id,
        'rating': review.rating,
        'reviewer': serialize_user_summary(review.reviewer),
        'reviewee': serialize_user_summary(review.reviewee),
        'project': serialize_project_summary(review.project),
        'tags': [serialize_tag(t) for t in tags],
        'created_at': review.created_at.isoformat(),
    }


def serialize_badge(user_honor):
    return {
        'id': user_honor.id,
        'tag': serialize_tag(user_honor.tag),
        'earned_at': user_honor.earned_at.isoformat(),
    }
