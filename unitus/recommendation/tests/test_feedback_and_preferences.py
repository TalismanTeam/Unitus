import json

from django.test import Client, TestCase
from django.urls import reverse

from accounts.models import User
from projects.models import JobAd, Project, ProjectRole
from recommendation.models import RecommendationFeedback, RecommendationPreference
from skills.models import SkillCategory


class RecommendationFeedbackViewTests(TestCase):
    def setUp(self):
        self.pm = User.objects.create_user(
            username='pm_user', email='pm@example.com', password='pass12345', birth_year=1990,
        )
        self.candidate = User.objects.create_user(
            username='candidate', email='candidate@example.com', password='pass12345',
            birth_year=1998, is_open_to_work=True,
        )
        self.project = Project.objects.create(
            pm=self.pm, title='Team Match Platform', short_description='desc',
            full_description='full desc', duration_days=30,
        )
        self.role = ProjectRole.objects.create(
            project=self.project, role_title='Backend Developer', role_description='desc', capacity=1,
        )
        self.job_ad = JobAd.objects.create(project=self.project, project_role=self.role)

        self.client = Client()
        self.client.login(username='pm_user', password='pass12345')

    def _post_feedback(self, target_id, recommendation_type, vote):
        return self.client.post(
            reverse('recommendation:recommend-feedback', kwargs={'id': target_id}),
            data=json.dumps({'recommendation_type': recommendation_type, 'vote': vote}),
            content_type='application/json',
        )

    def test_requires_authentication(self):
        anonymous_client = Client()
        response = anonymous_client.post(
            reverse('recommendation:recommend-feedback', kwargs={'id': self.job_ad.id}),
            data=json.dumps({'recommendation_type': 'AD', 'vote': 'UP'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)

    def test_upvote_ad_creates_feedback(self):
        response = self._post_feedback(self.job_ad.id, 'AD', 'UP')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(RecommendationFeedback.objects.count(), 1)
        feedback = RecommendationFeedback.objects.get()
        self.assertEqual(feedback.vote, 'UP')
        self.assertEqual(feedback.recommendation_type, 'AD')
        self.assertEqual(feedback.target_id, self.job_ad.id)

    def test_resending_feedback_updates_instead_of_duplicating(self):
        self._post_feedback(self.job_ad.id, 'AD', 'UP')
        self._post_feedback(self.job_ad.id, 'AD', 'DOWN')
        self.assertEqual(RecommendationFeedback.objects.count(), 1)
        self.assertEqual(RecommendationFeedback.objects.get().vote, 'DOWN')

    def test_candidate_feedback_target_is_a_user_id(self):
        response = self._post_feedback(self.candidate.id, 'CANDIDATE', 'DOWN')
        self.assertEqual(response.status_code, 200)
        feedback = RecommendationFeedback.objects.get()
        self.assertEqual(feedback.recommendation_type, 'CANDIDATE')
        self.assertEqual(feedback.target_id, self.candidate.id)

    def test_invalid_recommendation_type_rejected(self):
        response = self._post_feedback(self.job_ad.id, 'PROJECT', 'UP')
        self.assertEqual(response.status_code, 400)

    def test_invalid_vote_rejected(self):
        response = self._post_feedback(self.job_ad.id, 'AD', 'MAYBE')
        self.assertEqual(response.status_code, 400)

    def test_unknown_target_returns_404(self):
        response = self._post_feedback(999999, 'AD', 'UP')
        self.assertEqual(response.status_code, 404)


class RecommendationPreferencesViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='alice', email='alice@example.com', password='pass12345', birth_year=1995,
        )
        self.category, _ = SkillCategory.objects.get_or_create(category_name='Design')
        self.client = Client()
        self.client.login(username='alice', password='pass12345')

    def test_get_creates_default_preferences_on_first_call(self):
        self.assertFalse(RecommendationPreference.objects.filter(user=self.user).exists())
        response = self.client.get(reverse('recommendation:recommend-preferences'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['min_match_score'], 0.0)
        self.assertEqual(data['excluded_category_ids'], [])
        self.assertTrue(RecommendationPreference.objects.filter(user=self.user).exists())

    def test_patch_updates_min_match_score(self):
        response = self.client.patch(
            reverse('recommendation:recommend-preferences'),
            data=json.dumps({'min_match_score': 0.5}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['min_match_score'], 0.5)

    def test_patch_rejects_out_of_range_score(self):
        response = self.client.patch(
            reverse('recommendation:recommend-preferences'),
            data=json.dumps({'min_match_score': 1.5}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_patch_updates_excluded_categories(self):
        response = self.client.patch(
            reverse('recommendation:recommend-preferences'),
            data=json.dumps({'excluded_category_ids': [self.category.id]}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['excluded_category_ids'], [self.category.id])

    def test_preferences_are_isolated_per_user(self):
        other_user = User.objects.create_user(
            username='bob', email='bob@example.com', password='pass12345', birth_year=1995,
        )
        self.client.patch(
            reverse('recommendation:recommend-preferences'),
            data=json.dumps({'min_match_score': 0.9}),
            content_type='application/json',
        )
        other_client = Client()
        other_client.login(username='bob', password='pass12345')
        response = other_client.get(reverse('recommendation:recommend-preferences'))
        self.assertEqual(response.json()['min_match_score'], 0.0)
