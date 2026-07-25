import json

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from .models import Report


def _make_user(username, **kwargs):
    kwargs.setdefault('birth_year', 2000)
    kwargs.setdefault('email', f'{username}@example.com')
    return User.objects.create_user(username=username, password='pass1234', **kwargs)


class CreateReportTests(TestCase):
    def setUp(self):
        self.reporter = _make_user('reporter')
        self.target = _make_user('target')
        self.client.login(username='reporter', password='pass1234')

    def test_requires_login(self):
        self.client.logout()
        response = self.client.post(
            reverse('create_report'),
            data=json.dumps({'reported_user_id': self.target.id, 'reason': 'INSULTING'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 302)  # redirected to login

    def test_create_report_success(self):
        response = self.client.post(
            reverse('create_report'),
            data=json.dumps({
                'reported_user_id': self.target.id,
                'reason': 'INSULTING',
                'description': 'Was rude in chat.',
            }),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body['status'], Report.Status.PENDING_REVIEW)
        self.assertEqual(body['reported_user']['id'], self.target.id)
        report = Report.objects.get(pk=body['id'])
        self.assertEqual(report.reporter_id, self.reporter.id)

    def test_missing_reported_user_id(self):
        response = self.client.post(
            reverse('create_report'),
            data=json.dumps({'reason': 'INSULTING'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_invalid_reason_rejected(self):
        response = self.client.post(
            reverse('create_report'),
            data=json.dumps({'reported_user_id': self.target.id, 'reason': 'NOT_A_REASON'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_nonexistent_target_user(self):
        response = self.client.post(
            reverse('create_report'),
            data=json.dumps({'reported_user_id': 999999, 'reason': 'OTHER'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 404)

    def test_cannot_report_self(self):
        response = self.client.post(
            reverse('create_report'),
            data=json.dumps({'reported_user_id': self.reporter.id, 'reason': 'OTHER'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_description_optional(self):
        response = self.client.post(
            reverse('create_report'),
            data=json.dumps({'reported_user_id': self.target.id, 'reason': 'FAKE_PROJECT'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertIsNone(response.json()['description'])


class ListReportsTests(TestCase):
    def setUp(self):
        self.admin = _make_user('admin', system_role=User.SystemRole.ADMIN)
        self.regular = _make_user('regular')
        self.reporter = _make_user('reporter2')
        self.target = _make_user('target2')
        self.report = Report.objects.create(
            reporter=self.reporter, reported_user=self.target, reason='INSULTING',
        )

    def test_non_admin_forbidden(self):
        self.client.login(username='regular', password='pass1234')
        response = self.client.get(reverse('list_reports'))
        self.assertEqual(response.status_code, 403)

    def test_admin_can_list(self):
        self.client.login(username='admin', password='pass1234')
        response = self.client.get(reverse('list_reports'))
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body['reports']), 1)
        self.assertEqual(body['reports'][0]['reporter']['id'], self.reporter.id)

    def test_filter_by_status(self):
        self.client.login(username='admin', password='pass1234')
        Report.objects.create(
            reporter=self.reporter, reported_user=self.target, reason='OTHER',
            status=Report.Status.DISMISSED,
        )
        response = self.client.get(reverse('list_reports'), {'status': 'DISMISSED'})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body['reports']), 1)
        self.assertEqual(body['reports'][0]['status'], 'DISMISSED')

    def test_invalid_status_filter(self):
        self.client.login(username='admin', password='pass1234')
        response = self.client.get(reverse('list_reports'), {'status': 'NOT_REAL'})
        self.assertEqual(response.status_code, 400)


class ResolveReportTests(TestCase):
    def setUp(self):
        self.admin = _make_user('admin2', system_role=User.SystemRole.ADMIN)
        self.regular = _make_user('regular2')
        self.reporter = _make_user('reporter3')
        self.target = _make_user('target3')
        self.report = Report.objects.create(
            reporter=self.reporter, reported_user=self.target, reason='INSULTING',
        )

    def test_non_admin_forbidden(self):
        self.client.login(username='regular2', password='pass1234')
        response = self.client.patch(
            reverse('resolve_report', args=[self.report.id]),
            data=json.dumps({'action': 'resolve'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)

    def test_resolve_success(self):
        self.client.login(username='admin2', password='pass1234')
        response = self.client.patch(
            reverse('resolve_report', args=[self.report.id]),
            data=json.dumps({'action': 'resolve'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, Report.Status.RESOLVED)
        self.assertEqual(self.report.reviewed_by_admin_id, self.admin.id)

    def test_dismiss_success(self):
        self.client.login(username='admin2', password='pass1234')
        response = self.client.patch(
            reverse('resolve_report', args=[self.report.id]),
            data=json.dumps({'action': 'dismiss'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, Report.Status.DISMISSED)

    def test_invalid_action(self):
        self.client.login(username='admin2', password='pass1234')
        response = self.client.patch(
            reverse('resolve_report', args=[self.report.id]),
            data=json.dumps({'action': 'delete'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_cannot_review_twice(self):
        self.client.login(username='admin2', password='pass1234')
        self.report.status = Report.Status.RESOLVED
        self.report.save(update_fields=['status'])
        response = self.client.patch(
            reverse('resolve_report', args=[self.report.id]),
            data=json.dumps({'action': 'dismiss'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)

    def test_nonexistent_report(self):
        self.client.login(username='admin2', password='pass1234')
        response = self.client.patch(
            reverse('resolve_report', args=[999999]),
            data=json.dumps({'action': 'resolve'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 404)
