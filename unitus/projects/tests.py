from django.test import TestCase, Client
from django.urls import reverse

from accounts.models import User
from skills.models import SkillCategory, Skill
from skills.choices import MasteryLevel
from .models import Project, ProjectRole, JobAd, ProjectMember


class ProjectCreationFlowTests(TestCase):
    def setUp(self):
        self.category = SkillCategory.objects.create(category_name='Programming Languages')
        self.skill = Skill.objects.create(category=self.category, name='Python')
        self.pm = User.objects.create_user(
            username='alice', email='alice@example.com', password='pass12345', birth_year=1995
        )
        self.client = Client()
        self.client.login(username='alice', password='pass12345')

    def _create_project(self):
        return self.client.post(reverse('project_create'), {
            'title': 'Unitus Platform',
            'short_description': 'A collab platform',
            'full_description': 'Full description here',
            'duration_days': 90,
        }, follow=True)

    def _formset_data(self, skill_id=None, level='INTERMEDIATE'):
        data = {
            'form-TOTAL_FORMS': 3, 'form-INITIAL_FORMS': 0,
            'form-MIN_NUM_FORMS': 0, 'form-MAX_NUM_FORMS': 1000,
        }
        for i in range(3):
            data[f'form-{i}-skill'] = skill_id if i == 0 and skill_id else ''
            data[f'form-{i}-min_required_level'] = level if i == 0 and skill_id else ''
        return data

    def test_project_create_sets_pm_from_request_user(self):
        self._create_project()
        project = Project.objects.get(title='Unitus Platform')
        self.assertEqual(project.pm, self.pm)
        self.assertEqual(project.state, Project.State.RECRUITING)

    def test_only_pm_can_add_roles(self):
        self._create_project()
        project = Project.objects.get(title='Unitus Platform')
        other = User.objects.create_user(
            username='bob', email='bob@example.com', password='pass12345', birth_year=1996
        )
        other_client = Client()
        other_client.login(username='bob', password='pass12345')
        response = other_client.get(reverse('project_add_role', args=[project.pk]))
        self.assertEqual(response.status_code, 403)

    def test_adding_role_auto_publishes_job_ad(self):
        self._create_project()
        project = Project.objects.get(title='Unitus Platform')
        data = {
            'role_title': 'Backend Developer',
            'role_description': 'Build APIs',
            'capacity': 2,
            **self._formset_data(self.skill.pk, MasteryLevel.INTERMEDIATE),
        }
        self.client.post(reverse('project_add_role', args=[project.pk]), data)

        role = ProjectRole.objects.get(project=project)
        self.assertEqual(role.capacity, 2)
        self.assertTrue(role.projectroleskill_set.filter(skill=self.skill).exists())
        self.assertEqual(role.jobad.status, JobAd.Status.OPEN)

    def test_terminating_project_cancels_open_job_ads(self):
        self._create_project()
        project = Project.objects.get(title='Unitus Platform')
        data = {
            'role_title': 'Backend Developer', 'role_description': 'Build APIs', 'capacity': 2,
            **self._formset_data(self.skill.pk),
        }
        self.client.post(reverse('project_add_role', args=[project.pk]), data)
        role = ProjectRole.objects.get(project=project)

        self.client.post(reverse('project_state_change', args=[project.pk]), {
            'state': Project.State.TERMINATED,
            'termination_reason': Project.TerminationReason.SUCCESS,
        })

        role.refresh_from_db()
        self.assertEqual(role.jobad.status, JobAd.Status.CANCELLED)

    def test_terminating_without_reason_is_rejected(self):
        self._create_project()
        project = Project.objects.get(title='Unitus Platform')
        response = self.client.post(reverse('project_state_change', args=[project.pk]), {
            'state': Project.State.TERMINATED,
            'termination_reason': '',
        })
        project.refresh_from_db()
        self.assertNotEqual(project.state, Project.State.TERMINATED)
        self.assertContains(response, 'termination reason')

    def test_workspace_hidden_from_outsiders(self):
        self._create_project()
        project = Project.objects.get(title='Unitus Platform')
        outsider = User.objects.create_user(
            username='carol', email='carol@example.com', password='pass12345', birth_year=1997
        )
        outsider_client = Client()
        outsider_client.login(username='carol', password='pass12345')
        response = outsider_client.get(reverse('project_workspace', args=[project.pk]))
        self.assertEqual(response.status_code, 403)

    def test_workspace_visible_to_active_member(self):
        self._create_project()
        project = Project.objects.get(title='Unitus Platform')
        member = User.objects.create_user(
            username='dave', email='dave@example.com', password='pass12345', birth_year=1998
        )
        ProjectMember.objects.create(project=project, user=member, member_status=ProjectMember.MemberStatus.ACTIVE)
        member_client = Client()
        member_client.login(username='dave', password='pass12345')
        response = member_client.get(reverse('project_workspace', args=[project.pk]))
        self.assertEqual(response.status_code, 200)

    def test_home_page_loads_for_anonymous_user(self):
        anon_client = Client()
        response = anon_client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)

    def test_skill_based_suggestions_on_home_page(self):
        from skills.models import UserSkill
        UserSkill.objects.create(user=self.pm, skill=self.skill, mastery_level=MasteryLevel.ADVANCED)
        self._create_project()
        project = Project.objects.get(title='Unitus Platform')
        data = {
            'role_title': 'Backend Developer', 'role_description': 'Build APIs', 'capacity': 2,
            **self._formset_data(self.skill.pk),
        }
        self.client.post(reverse('project_add_role', args=[project.pk]), data)

        response = self.client.get(reverse('home'))
        self.assertContains(response, 'Backend Developer')

    def _create_project_with_role(self, capacity=1):
        self._create_project()
        project = Project.objects.get(title='Unitus Platform')
        data = {
            'role_title': 'Backend Developer', 'role_description': 'Build APIs', 'capacity': capacity,
            **self._formset_data(self.skill.pk),
        }
        self.client.post(reverse('project_add_role', args=[project.pk]), data)
        role = ProjectRole.objects.get(project=project)
        return project, role

    def test_pm_can_remove_member_and_job_ad_reopens(self):
        project, role = self._create_project_with_role(capacity=1)
        member_user = User.objects.create_user(
            username='erin', email='erin@example.com', password='pass12345', birth_year=1999
        )
        member = ProjectMember.objects.create(
            project=project, user=member_user, project_role=role,
            member_status=ProjectMember.MemberStatus.ACTIVE,
        )
        role.jobad.status = JobAd.Status.FILLED
        role.jobad.save(update_fields=['status'])

        response = self.client.post(reverse('project_remove_member', args=[project.pk, member.pk]), follow=True)
        self.assertEqual(response.status_code, 200)

        member.refresh_from_db()
        role.jobad.refresh_from_db()
        self.assertEqual(member.member_status, ProjectMember.MemberStatus.REMOVED)
        self.assertEqual(role.jobad.status, JobAd.Status.OPEN)

    def test_non_pm_cannot_remove_member(self):
        project, role = self._create_project_with_role()
        member_user = User.objects.create_user(
            username='erin', email='erin@example.com', password='pass12345', birth_year=1999
        )
        member = ProjectMember.objects.create(
            project=project, user=member_user, member_status=ProjectMember.MemberStatus.ACTIVE,
        )
        outsider = User.objects.create_user(
            username='frank', email='frank@example.com', password='pass12345', birth_year=2000
        )
        outsider_client = Client()
        outsider_client.login(username='frank', password='pass12345')
        response = outsider_client.post(reverse('project_remove_member', args=[project.pk, member.pk]))
        self.assertEqual(response.status_code, 403)

    def test_transfer_ownership_requires_confirmation(self):
        project, role = self._create_project_with_role()
        new_pm_user = User.objects.create_user(
            username='grace', email='grace@example.com', password='pass12345', birth_year=1999
        )
        ProjectMember.objects.create(
            project=project, user=new_pm_user, member_status=ProjectMember.MemberStatus.ACTIVE,
        )
        response = self.client.post(reverse('project_transfer_ownership', args=[project.pk]), {
            'new_owner': new_pm_user.pk,
            # 'confirm' omitted on purpose
        })
        project.refresh_from_db()
        self.assertEqual(project.pm, self.pm)
        self.assertEqual(response.status_code, 200)

    def test_transfer_ownership_success(self):
        project, role = self._create_project_with_role()
        new_pm_user = User.objects.create_user(
            username='grace', email='grace@example.com', password='pass12345', birth_year=1999
        )
        ProjectMember.objects.create(
            project=project, user=new_pm_user, member_status=ProjectMember.MemberStatus.ACTIVE,
        )
        response = self.client.post(reverse('project_transfer_ownership', args=[project.pk]), {
            'new_owner': new_pm_user.pk,
            'confirm': 'on',
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        project.refresh_from_db()
        self.assertEqual(project.pm, new_pm_user)
        # old PM should now have a plain membership row so they aren't locked out
        self.assertTrue(ProjectMember.objects.filter(project=project, user=self.pm).exists())


        
def make_user(username, email, **extra):
    defaults = {"birth_year": 2000}
    defaults.update(extra)
    return User.objects.create_user(username=username, email=email, password="pass1234", **defaults)
 
 
class PmAutoMembershipSignalTests(TestCase):
    def setUp(self):
        self.pm = make_user("pm", "pm@example.com")
 
    def test_pm_gets_active_membership_on_project_creation(self):
        project = Project.objects.create(
            pm=self.pm, title="T", short_description="s", full_description="f", duration_days=10,
        )
        membership = ProjectMember.objects.get(project=project, user=self.pm)
        self.assertEqual(membership.member_status, ProjectMember.MemberStatus.ACTIVE)
        self.assertIsNone(membership.project_role)
 
    def test_no_duplicate_membership_on_subsequent_saves(self):
        project = Project.objects.create(
            pm=self.pm, title="T", short_description="s", full_description="f", duration_days=10,
        )
        project.title = "Updated title"
        project.save()
        self.assertEqual(ProjectMember.objects.filter(project=project, user=self.pm).count(), 1)
 
    def test_does_not_overwrite_membership_if_already_resigned(self):
        # If the PM's row was somehow changed (e.g. RESIGNED) and the
        # project is saved again for an unrelated reason, get_or_create
        # should NOT flip it back to ACTIVE — that would be surprising and
        # could undo a legitimate state change.
        project = Project.objects.create(
            pm=self.pm, title="T", short_description="s", full_description="f", duration_days=10,
        )
        membership = ProjectMember.objects.get(project=project, user=self.pm)
        membership.member_status = ProjectMember.MemberStatus.RESIGNED
        membership.save(update_fields=["member_status"])
 
        project.title = "Updated again"
        project.save()
 
        membership.refresh_from_db()
        self.assertEqual(membership.member_status, ProjectMember.MemberStatus.RESIGNED)
