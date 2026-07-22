from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from accounts.models import User
from projects.models import Project


class Review(models.Model):
    reviewer = models.ForeignKey(User, on_delete=models.RESTRICT, related_name='reviews_given')
    reviewee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_received')
    project = models.ForeignKey(Project, on_delete=models.RESTRICT)
    rating = models.SmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['reviewer', 'reviewee', 'project'], name='unique_review_per_project'),
            models.CheckConstraint(check=models.Q(rating__gte=1) & models.Q(rating__lte=5), name='chk_rating_range'),
        ]


class Tag(models.Model):
    class TagType(models.TextChoices):
        POSITIVE = 'POSITIVE'
        NEGATIVE = 'NEGATIVE'

    name = models.CharField(max_length=50, unique=True)
    tag_type = models.CharField(max_length=10, choices=TagType.choices)


class ReviewTag(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.RESTRICT)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['review', 'tag'], name='unique_review_tag_pk')
        ]


class UserHonor(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.RESTRICT)
    earned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'tag'], name='unique_honor_per_user')
        ]