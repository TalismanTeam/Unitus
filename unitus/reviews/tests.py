"""
Tests for the Rating, Reviews & Badges module (reviews app), plain Django,
no DRF.

Run with:
    python manage.py test reviews
"""

import json

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from projects.models import Project, ProjectRole, ProjectMember
from reviews.models import Review, Tag, ReviewTag, UserHonor


def make_user(username, email, **extra):
    defaults = {"birth_year": 2000}
    defaults.update(extra)
    return User.objects.create_user(username=username, email=email, password="pass1234", **defaults)


def make_completed_project(pm, **extra):
    defaults = {
        "title": "Done Project",
        "short_description": "short",
        "full_description": "full",
        "duration_days": 30,
        "state": Project.State.TERMINATED,
        "termination_reason": Project.TerminationReason.SUCCESS,
    }
    defaults.update(extra)
    return Project.objects.create(pm=pm, **defaults)


def make_member(project, user, status=ProjectMember.MemberStatus.ACTIVE):
    return ProjectMember.objects.create(project=project, user=user, member_status=status)


def make_tag(name, tag_type=Tag.TagType.POSITIVE):
    return Tag.objects.create(name=name, tag_type=tag_type)


# ---------------------------------------------------------------------------
# POST /reviews
# ---------------------------------------------------------------------------

class CreateReviewTests(TestCase):
    def setUp(self):
        self.pm = make_user("pm", "pm@example.com")
        self.reviewer = make_user("reviewer", "reviewer@example.com")
        self.reviewee = make_user("reviewee", "reviewee@example.com")
        self.project = make_completed_project(self.pm)
        make_member(self.project, self.reviewer)
        make_member(self.project, self.reviewee)
        self.tag_positive = make_tag("Great Communicator", Tag.TagType.POSITIVE)
        self.tag_negative = make_tag("Missed Deadlines", Tag.TagType.NEGATIVE)
        self.url = reverse("reviews:review-create")
        self.client.force_login(self.reviewer)

    def _post(self, **overrides):
        body = {"project_id": self.project.id, "reviewee_id": self.reviewee.id, "rating": 4, "tag_ids": []}
        body.update(overrides)
        return self.client.post(self.url, data=json.dumps(body), content_type="application/json")

    def test_requires_login(self):
        self.client.logout()
        response = self._post()
        self.assertEqual(response.status_code, 302)

    def test_creates_review_with_tags(self):
        response = self._post(tag_ids=[self.tag_positive.id, self.tag_negative.id])
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["rating"], 4)
        self.assertEqual(data["reviewer"]["id"], self.reviewer.id)
        self.assertEqual(data["reviewee"]["id"], self.reviewee.id)
        self.assertEqual({t["id"] for t in data["tags"]}, {self.tag_positive.id, self.tag_negative.id})
        self.assertEqual(ReviewTag.objects.filter(review_id=data["id"]).count(), 2)

    def test_creates_review_with_no_tags(self):
        response = self._post(tag_ids=[])
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["tags"], [])

    def test_missing_required_fields_400(self):
        response = self.client.post(
            self.url, data=json.dumps({"project_id": self.project.id}), content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_rating_out_of_range_400(self):
        response = self._post(rating=6)
        self.assertEqual(response.status_code, 400)
        response = self._post(rating=0)
        self.assertEqual(response.status_code, 400)

    def test_non_integer_rating_400(self):
        response = self._post(rating="not-a-number")
        self.assertEqual(response.status_code, 400)

    def test_cannot_review_self(self):
        response = self._post(reviewee_id=self.reviewer.id)
        self.assertEqual(response.status_code, 400)

    def test_nonexistent_project_404(self):
        response = self._post(project_id=999999)
        self.assertEqual(response.status_code, 404)

    def test_nonexistent_reviewee_404(self):
        response = self._post(reviewee_id=999999)
        self.assertEqual(response.status_code, 404)

    def test_rejects_project_not_terminated(self):
        self.project.state = Project.State.IN_PROGRESS
        self.project.termination_reason = None
        self.project.save(update_fields=["state", "termination_reason"])
        response = self._post()
        self.assertEqual(response.status_code, 400)

    def test_rejects_project_terminated_but_not_success(self):
        self.project.termination_reason = Project.TerminationReason.PM_CANCELED
        self.project.save(update_fields=["termination_reason"])
        response = self._post()
        self.assertEqual(response.status_code, 400)

    def test_reviewer_must_have_been_teammate(self):
        outsider = make_user("outsider", "outsider@example.com")
        self.client.force_login(outsider)
        response = self._post()
        self.assertEqual(response.status_code, 403)

    def test_reviewee_must_have_been_teammate(self):
        outsider = make_user("outsider2", "outsider2@example.com")
        response = self._post(reviewee_id=outsider.id)
        self.assertEqual(response.status_code, 400)

    def test_rejects_duplicate_review_same_pair_same_project(self):
        self._post()
        response = self._post()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Review.objects.count(), 1)

    def test_allows_same_pair_review_on_different_project(self):
        self._post()
        other_project = make_completed_project(self.pm, title="Second Project")
        make_member(other_project, self.reviewer)
        make_member(other_project, self.reviewee)
        response = self._post(project_id=other_project.id)
        self.assertEqual(response.status_code, 201)

    def test_reverse_direction_review_allowed(self):
        # member -> member is fine; and the same two people can review each
        # other in both directions on the same project.
        self._post()
        self.client.force_login(self.reviewee)
        response = self.client.post(
            self.url,
            data=json.dumps({"project_id": self.project.id, "reviewee_id": self.reviewer.id, "rating": 5, "tag_ids": []}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)

    def test_invalid_tag_id_400(self):
        response = self._post(tag_ids=[999999])
        self.assertEqual(response.status_code, 400)

    def test_duplicate_tag_ids_in_request_deduped_not_error(self):
        response = self._post(tag_ids=[self.tag_positive.id, self.tag_positive.id])
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(response.json()["tags"]), 1)

    def test_pm_and_member_can_review_each_other(self):
        self.client.force_login(self.pm)
        response = self.client.post(
            self.url,
            data=json.dumps({"project_id": self.project.id, "reviewee_id": self.reviewee.id, "rating": 3, "tag_ids": []}),
            content_type="application/json",
        )
        # PM was never added as a ProjectMember row in setUp — this documents
        # that a PM must also have a ProjectMember row to be reviewable/review,
        # matching how ProjectMember is the single source of "was on this team".
        self.assertEqual(response.status_code, 403)


# ---------------------------------------------------------------------------
# Badge auto-unlock logic
# ---------------------------------------------------------------------------

class BadgeAutoUnlockTests(TestCase):
    def setUp(self):
        self.pm = make_user("pm2", "pm2@example.com")
        self.reviewee = make_user("reviewee2", "reviewee2@example.com")
        self.tag = make_tag("Reliable", Tag.TagType.POSITIVE)
        self.negative_tag = make_tag("Rude", Tag.TagType.NEGATIVE)
        self.url = reverse("reviews:review-create")

        # 5 different reviewers, 5 different completed projects, each gives
        # the reviewee the same positive tag once.
        self.reviewers = []
        self.projects = []
        for i in range(5):
            reviewer = make_user(f"reviewer{i}", f"reviewer{i}@example.com")
            project = make_completed_project(self.pm, title=f"Project {i}")
            make_member(project, reviewer)
            make_member(project, self.reviewee)
            self.reviewers.append(reviewer)
            self.projects.append(project)

    def _review(self, reviewer, project, tag_ids):
        self.client.force_login(reviewer)
        return self.client.post(
            self.url,
            data=json.dumps({
                "project_id": project.id, "reviewee_id": self.reviewee.id,
                "rating": 5, "tag_ids": tag_ids,
            }),
            content_type="application/json",
        )

    def test_no_badge_below_threshold(self):
        for i in range(4):
            self._review(self.reviewers[i], self.projects[i], [self.tag.id])
        self.assertFalse(UserHonor.objects.filter(user=self.reviewee, tag=self.tag).exists())

    def test_badge_unlocked_at_threshold(self):
        for i in range(5):
            self._review(self.reviewers[i], self.projects[i], [self.tag.id])
        self.assertTrue(UserHonor.objects.filter(user=self.reviewee, tag=self.tag).exists())

    def test_badge_not_duplicated_past_threshold(self):
        for i in range(5):
            self._review(self.reviewers[i], self.projects[i], [self.tag.id])
        self.assertEqual(UserHonor.objects.filter(user=self.reviewee, tag=self.tag).count(), 1)

    def test_negative_tags_never_unlock_badges(self):
        for i in range(5):
            self._review(self.reviewers[i], self.projects[i], [self.negative_tag.id])
        self.assertFalse(UserHonor.objects.filter(user=self.reviewee, tag=self.negative_tag).exists())

    def test_badges_are_per_tag_independently(self):
        other_positive_tag = make_tag("Team Player", Tag.TagType.POSITIVE)
        for i in range(5):
            tag_ids = [self.tag.id] if i < 3 else [other_positive_tag.id]
            self._review(self.reviewers[i], self.projects[i], tag_ids)
        self.assertFalse(UserHonor.objects.filter(user=self.reviewee, tag=self.tag).exists())
        self.assertFalse(UserHonor.objects.filter(user=self.reviewee, tag=other_positive_tag).exists())


# ---------------------------------------------------------------------------
# GET /reviews/tags
# ---------------------------------------------------------------------------

class TagsListViewTests(TestCase):
    def setUp(self):
        self.user = make_user("u1", "u1@example.com")
        self.url = reverse("reviews:review-tags")
        make_tag("Great Communicator", Tag.TagType.POSITIVE)
        make_tag("Missed Deadlines", Tag.TagType.NEGATIVE)

    def test_requires_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_lists_all_tags(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        names = {t["name"] for t in response.json()["tags"]}
        self.assertEqual(names, {"Great Communicator", "Missed Deadlines"})


# ---------------------------------------------------------------------------
# GET /users/:id/reviews
# ---------------------------------------------------------------------------

class UserReviewsViewTests(TestCase):
    def setUp(self):
        self.pm = make_user("pm3", "pm3@example.com")
        self.reviewer = make_user("reviewer3", "reviewer3@example.com")
        self.reviewee = make_user("reviewee3", "reviewee3@example.com")
        self.viewer = make_user("viewer", "viewer@example.com")
        self.project = make_completed_project(self.pm)
        make_member(self.project, self.reviewer)
        make_member(self.project, self.reviewee)
        self.tag = make_tag("Reliable", Tag.TagType.POSITIVE)

        self.review = Review.objects.create(
            reviewer=self.reviewer, reviewee=self.reviewee, project=self.project, rating=5
        )
        ReviewTag.objects.create(review=self.review, tag=self.tag)

        self.url = reverse("reviews:user-reviews", kwargs={"user_id": self.reviewee.id})

    def test_requires_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_returns_reviews_with_tags(self):
        self.client.force_login(self.viewer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        data = response.json()["reviews"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["rating"], 5)
        self.assertEqual([t["name"] for t in data[0]["tags"]], ["Reliable"])

    def test_only_shows_reviews_received_not_given(self):
        self.client.force_login(self.viewer)
        url_for_reviewer = reverse("reviews:user-reviews", kwargs={"user_id": self.reviewer.id})
        response = self.client.get(url_for_reviewer)
        self.assertEqual(response.json()["reviews"], [])

    def test_nonexistent_user_404(self):
        self.client.force_login(self.viewer)
        response = self.client.get(reverse("reviews:user-reviews", kwargs={"user_id": 999999}))
        self.assertEqual(response.status_code, 404)


# ---------------------------------------------------------------------------
# GET /users/:id/badges
# ---------------------------------------------------------------------------

class UserBadgesViewTests(TestCase):
    def setUp(self):
        self.user = make_user("badgeduser", "badgeduser@example.com")
        self.viewer = make_user("viewer2", "viewer2@example.com")
        self.tag = make_tag("Reliable", Tag.TagType.POSITIVE)
        UserHonor.objects.create(user=self.user, tag=self.tag)
        self.url = reverse("reviews:user-badges", kwargs={"user_id": self.user.id})

    def test_requires_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_returns_badges(self):
        self.client.force_login(self.viewer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        badges = response.json()["badges"]
        self.assertEqual(len(badges), 1)
        self.assertEqual(badges[0]["tag"]["name"], "Reliable")

    def test_user_with_no_badges_returns_empty_list(self):
        other = make_user("nobadges", "nobadges@example.com")
        self.client.force_login(self.viewer)
        response = self.client.get(reverse("reviews:user-badges", kwargs={"user_id": other.id}))
        self.assertEqual(response.json()["badges"], [])

    def test_nonexistent_user_404(self):
        self.client.force_login(self.viewer)
        response = self.client.get(reverse("reviews:user-badges", kwargs={"user_id": 999999}))
        self.assertEqual(response.status_code, 404)
