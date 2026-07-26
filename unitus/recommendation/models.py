from django.db import models

from accounts.models import User
from skills.models import SkillCategory


class RecommendationFeedback(models.Model):
    """
    Thumbs up/down on a suggestion (SRS/backend-modules §6:
    POST /recommendations/:id/feedback).

    `target_id` is the JobAd id when recommendation_type=AD, or the User id
    (the candidate) when recommendation_type=CANDIDATE. Kept as a plain int
    + enum column, rather than a GenericForeignKey, since there are only ever
    two possible target tables and the ticket/status pattern elsewhere in
    this codebase already prefers a small enum column over polymorphism.

    One row per (user, recommendation_type, target_id): sending feedback
    again on the same suggestion updates the existing vote instead of
    piling up duplicates.
    """

    class RecommendationType(models.TextChoices):
        AD = 'AD'
        CANDIDATE = 'CANDIDATE'

    class Vote(models.TextChoices):
        UP = 'UP'
        DOWN = 'DOWN'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recommendation_feedback')
    recommendation_type = models.CharField(max_length=10, choices=RecommendationType.choices)
    target_id = models.PositiveIntegerField()
    vote = models.CharField(max_length=4, choices=Vote.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recommendation_type', 'target_id'],
                name='unique_feedback_per_user_target',
            )
        ]
        indexes = [
            models.Index(fields=['recommendation_type', 'target_id']),
        ]

    def __str__(self):
        return f'{self.user.username} {self.get_vote_display()} {self.recommendation_type}#{self.target_id}'


class RecommendationPreference(models.Model):
    """
    Per-user tuning of their own recommendation feed
    (SRS/backend-modules §6: GET/PATCH /recommendations/preferences).

    - min_match_score hides suggestions below a cosine-similarity floor.
    - excluded_categories lets a user say "never suggest me ads asking for
      skills in this category" (e.g. hide Design ads for a backend-only dev).
    """

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, primary_key=True, related_name='recommendation_preference',
    )
    min_match_score = models.FloatField(default=0.0)
    excluded_categories = models.ManyToManyField(
        SkillCategory, blank=True, related_name='excluded_by_recommendation_preferences',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(min_match_score__gte=0.0) & models.Q(min_match_score__lte=1.0),
                name='chk_min_match_score_range',
            )
        ]

    def __str__(self):
        return f'Recommendation preferences for {self.user.username}'


class EmbeddingCache(models.Model):
    """
    Caches the embedding vector for a User/JobAd so MatchScoreService doesn't
    re-run the sentence-transformer model on every single request. A row is
    reused as long as `text_hash` (sha256 of the exact text that was fed to
    the model) still matches what get_embedding_text() produces now - so it
    self-invalidates the moment a profile or job ad actually changes, with no
    separate signal wiring needed.

    is_query is part of the identity because the same object is embedded
    differently depending on direction: a User is a "query" when matching
    against ads, but a "passage" when being matched as a candidate - the E5
    model prefix changes the vector, so both must be cached separately.
    """

    class ObjectType(models.TextChoices):
        USER = 'USER'
        PROJECT = 'PROJECT'
        JOB_AD = 'JOB_AD'

    object_type = models.CharField(max_length=10, choices=ObjectType.choices)
    object_id = models.PositiveIntegerField()
    is_query = models.BooleanField()
    text_hash = models.CharField(max_length=64)
    vector = models.JSONField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['object_type', 'object_id', 'is_query'],
                name='unique_embedding_per_object_direction',
            )
        ]
        indexes = [
            models.Index(fields=['object_type', 'object_id']),
        ]

    def __str__(self):
        direction = 'query' if self.is_query else 'passage'
        return f'{self.object_type}#{self.object_id} ({direction})'
