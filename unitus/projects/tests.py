from django.test import TestCase, Client
from django.urls import reverse

from accounts.models import User
from skills.models import SkillCategory, Skill
from skills.choices import MasteryLevel
from .models import Project, ProjectRole, JobAd, ProjectMember


class ProjectCreationFlowTests(TestCase):
    def setUp(self):
        self.category, _ = SkillCategory.objects.get_or_create(category_name='Programming Languages')
        self.skill, _ = Skill.objects.get_or_create(category=self.category, name='Python')
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


class ProjectEditDeleteTests(TestCase):
    """Covers PATCH /projects/:id, DELETE /projects/:id, and PATCH /projects/:id/status
    edge cases that weren't exercised by ProjectCreationFlowTests."""

    def setUp(self):
        self.category, _ = SkillCategory.objects.get_or_create(category_name='Programming Languages')
        self.skill, _ = Skill.objects.get_or_create(category=self.category, name='Python')
        self.pm = User.objects.create_user(
            username='alice', email='alice@example.com', password='pass12345', birth_year=1995
        )
        self.client = Client()
        self.client.login(username='alice', password='pass12345')
        self.project = Project.objects.create(
            pm=self.pm, title='Original Title', short_description='desc',
            full_description='full', duration_days=30,
        )

    def test_non_pm_cannot_edit_project(self):
        User.objects.create_user(username='bob', email='bob@example.com', password='pass12345', birth_year=1996)
        outsider_client = Client()
        outsider_client.login(username='bob', password='pass12345')
        response = outsider_client.get(reverse('project_edit', args=[self.project.pk]))
        self.assertEqual(response.status_code, 403)

    def test_pm_can_edit_project_details(self):
        self.client.post(reverse('project_edit', args=[self.project.pk]), {
            'title': 'Updated Title',
            'short_description': 'new short desc',
            'full_description': 'new full desc',
            'duration_days': 60,
        }, follow=True)
        self.project.refresh_from_db()
        self.assertEqual(self.project.title, 'Updated Title')
        self.assertEqual(self.project.duration_days, 60)

    def test_non_pm_cannot_delete_project(self):
        User.objects.create_user(username='bob', email='bob@example.com', password='pass12345', birth_year=1996)
        outsider_client = Client()
        outsider_client.login(username='bob', password='pass12345')
        response = outsider_client.post(reverse('project_delete', args=[self.project.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Project.objects.filter(pk=self.project.pk).exists())

    def test_pm_deleting_project_cascades_roles_ads_and_memberships(self):
        role = ProjectRole.objects.create(
            project=self.project, role_title='Dev', role_description='x', capacity=1
        )
        job_ad = JobAd.objects.create(project=self.project, project_role=role, status=JobAd.Status.OPEN)
        member_user = User.objects.create_user(
            username='dave', email='dave@example.com', password='pass12345', birth_year=1998
        )
        ProjectMember.objects.create(
            project=self.project, user=member_user, project_role=role,
            member_status=ProjectMember.MemberStatus.ACTIVE,
        )

        response = self.client.post(reverse('project_delete', args=[self.project.pk]), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Project.objects.filter(pk=self.project.pk).exists())
        self.assertFalse(ProjectRole.objects.filter(pk=role.pk).exists())
        self.assertFalse(JobAd.objects.filter(pk=job_ad.pk).exists())
        self.assertFalse(ProjectMember.objects.filter(project_id=self.project.pk).exists())

    def test_state_change_clears_termination_reason_when_not_terminating(self):
        """Form-level rule in ProjectStateChangeForm.clean(): any reason submitted
        alongside a non-TERMINATED state must be discarded, not just ignored client-side."""
        self.client.post(reverse('project_state_change', args=[self.project.pk]), {
            'state': Project.State.SUSPENDED,
            'termination_reason': Project.TerminationReason.SUCCESS,
        }, follow=True)
        self.project.refresh_from_db()
        self.assertEqual(self.project.state, Project.State.SUSPENDED)
        self.assertIsNone(self.project.termination_reason)


class ProjectRoleManagementTests(TestCase):
    """Covers POST/PATCH/DELETE /projects/:id/roles/:roleId and the JobAd
    side effects the projects module owns internally."""

    def setUp(self):
        self.category, _ = SkillCategory.objects.get_or_create(category_name='Programming Languages')
        self.skill, _ = Skill.objects.get_or_create(category=self.category, name='Python')
        self.pm = User.objects.create_user(
            username='alice', email='alice@example.com', password='pass12345', birth_year=1995
        )
        self.client = Client()
        self.client.login(username='alice', password='pass12345')
        self.project = Project.objects.create(
            pm=self.pm, title='P', short_description='s', full_description='f', duration_days=30
        )
        self.role = ProjectRole.objects.create(
            project=self.project, role_title='Backend Dev', role_description='x', capacity=2
        )
        self.job_ad = JobAd.objects.create(project=self.project, project_role=self.role, status=JobAd.Status.OPEN)

    def _formset_data(self):
        return {
            'form-TOTAL_FORMS': 0, 'form-INITIAL_FORMS': 0,
            'form-MIN_NUM_FORMS': 0, 'form-MAX_NUM_FORMS': 1000,
        }

    def test_non_pm_cannot_edit_role(self):
        User.objects.create_user(username='bob', email='bob@example.com', password='pass12345', birth_year=1996)
        outsider_client = Client()
        outsider_client.login(username='bob', password='pass12345')
        response = outsider_client.get(reverse('project_edit_role', args=[self.project.pk, self.role.pk]))
        self.assertEqual(response.status_code, 403)

    def test_non_pm_cannot_delete_role(self):
        User.objects.create_user(username='bob', email='bob@example.com', password='pass12345', birth_year=1996)
        outsider_client = Client()
        outsider_client.login(username='bob', password='pass12345')
        response = outsider_client.post(reverse('project_delete_role', args=[self.project.pk, self.role.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(ProjectRole.objects.filter(pk=self.role.pk).exists())

    def test_editing_role_capacity_down_to_member_count_fills_job_ad(self):
        member_user = User.objects.create_user(
            username='dave', email='dave@example.com', password='pass12345', birth_year=1998
        )
        ProjectMember.objects.create(
            project=self.project, user=member_user, project_role=self.role,
            member_status=ProjectMember.MemberStatus.ACTIVE,
        )
        data = {
            'role_title': 'Backend Dev', 'role_description': 'x', 'capacity': 1,
            **self._formset_data(),
        }
        self.client.post(reverse('project_edit_role', args=[self.project.pk, self.role.pk]), data, follow=True)
        self.job_ad.refresh_from_db()
        self.assertEqual(self.job_ad.status, JobAd.Status.FILLED)

    def test_edit_role_rejects_zero_capacity(self):
        data = {'role_title': 'Backend Dev', 'role_description': 'x', 'capacity': 0, **self._formset_data()}
        self.client.post(reverse('project_edit_role', args=[self.project.pk, self.role.pk]), data)
        self.role.refresh_from_db()
        self.assertEqual(self.role.capacity, 2)

    def test_deleting_role_removes_its_job_ad_entirely(self):
        """
        Documents current (likely unintended) behaviour: the view sets the ad
        to CANCELLED and then calls role.delete(), but JobAd.project_role is a
        CASCADE OneToOneField to ProjectRole, so the ad row is deleted along
        with the role in the same statement - the CANCELLED status is never
        actually persisted anywhere visible. If ad history is meant to survive
        role deletion (e.g. for admin audit / analytics), JobAd.project_role
        should not cascade-delete on role removal.
        """
        self.client.post(reverse('project_delete_role', args=[self.project.pk, self.role.pk]), follow=True)
        self.assertFalse(ProjectRole.objects.filter(pk=self.role.pk).exists())
        self.assertFalse(JobAd.objects.filter(pk=self.job_ad.pk).exists())

    def test_deleting_role_nulls_out_project_role_on_existing_members(self):
        member_user = User.objects.create_user(
            username='erin', email='erin@example.com', password='pass12345', birth_year=1999
        )
        member = ProjectMember.objects.create(
            project=self.project, user=member_user, project_role=self.role,
            member_status=ProjectMember.MemberStatus.ACTIVE,
        )
        self.client.post(reverse('project_delete_role', args=[self.project.pk, self.role.pk]), follow=True)
        member.refresh_from_db()
        self.assertIsNone(member.project_role)
        self.assertEqual(member.member_status, ProjectMember.MemberStatus.ACTIVE)


class ProjectResignationTests(TestCase):
    """Covers POST /projects/:id/members/:userId/resign."""

    def setUp(self):
        self.category, _ = SkillCategory.objects.get_or_create(category_name='Programming Languages')
        self.skill, _ = Skill.objects.get_or_create(category=self.category, name='Python')
        self.pm = User.objects.create_user(
            username='alice', email='alice@example.com', password='pass12345', birth_year=1995
        )
        self.project = Project.objects.create(
            pm=self.pm, title='P', short_description='s', full_description='f', duration_days=30
        )
        self.role = ProjectRole.objects.create(
            project=self.project, role_title='Dev', role_description='x', capacity=1
        )
        self.job_ad = JobAd.objects.create(project=self.project, project_role=self.role, status=JobAd.Status.FILLED)
        self.member_user = User.objects.create_user(
            username='erin', email='erin@example.com', password='pass12345', birth_year=1999
        )
        self.member = ProjectMember.objects.create(
            project=self.project, user=self.member_user, project_role=self.role,
            member_status=ProjectMember.MemberStatus.ACTIVE,
        )
        self.client = Client()
        self.client.login(username='erin', password='pass12345')

    def test_pm_cannot_resign(self):
        pm_client = Client()
        pm_client.login(username='alice', password='pass12345')
        pm_client.post(reverse('project_resign', args=[self.project.pk]), {'reason': 'leaving'}, follow=True)
        self.assertEqual(self.project.pm_id, self.pm.pk)

    def test_non_member_cannot_resign(self):
        User.objects.create_user(username='frank', email='frank@example.com', password='pass12345', birth_year=2000)
        outsider_client = Client()
        outsider_client.login(username='frank', password='pass12345')
        response = outsider_client.post(reverse('project_resign', args=[self.project.pk]), {'reason': 'leaving'})
        self.assertEqual(response.status_code, 403)

    def test_resign_requires_a_reason(self):
        self.client.post(reverse('project_resign', args=[self.project.pk]), {'reason': ''})
        self.member.refresh_from_db()
        self.assertEqual(self.member.member_status, ProjectMember.MemberStatus.ACTIVE)

    def test_active_member_can_resign_and_job_ad_reopens(self):
        self.client.post(
            reverse('project_resign', args=[self.project.pk]), {'reason': 'personal reasons'}, follow=True
        )
        self.member.refresh_from_db()
        self.job_ad.refresh_from_db()
        self.assertEqual(self.member.member_status, ProjectMember.MemberStatus.RESIGNED)
        self.assertEqual(self.job_ad.status, JobAd.Status.OPEN)

    def test_already_resigned_member_cannot_resign_again(self):
        self.member.member_status = ProjectMember.MemberStatus.RESIGNED
        self.member.save(update_fields=['member_status'])
        response = self.client.post(reverse('project_resign', args=[self.project.pk]), {'reason': 'again'})
        self.assertEqual(response.status_code, 403)

    def test_resignation_does_not_go_through_a_ticket(self):
        """
        backend-modules.pdf documents resignation as part of the unified Ticket
        module - a "resignation request flow" (TM-*) - and collaboration.Ticket
        even has a RESIGNATION type. This view instead resigns the member
        immediately with no PM-side approval step and never touches the Ticket
        table at all. This test pins today's (spec-deviating) behaviour so a
        future fix shows up as a deliberate, visible test change rather than a
        silent regression.
        """
        from collaboration.models import Ticket

        self.client.post(reverse('project_resign', args=[self.project.pk]), {'reason': 'personal reasons'})
        self.assertEqual(
            Ticket.objects.filter(project=self.project, ticket_type=Ticket.TicketType.RESIGNATION).count(), 0
        )


class PublicProjectAndJobAdViewsTests(TestCase):
    """Covers GET /ads/:id and the ad-facing parts of GET / (home), which live
    inside the projects app rather than a dedicated Advertisement module."""

    def setUp(self):
        self.category, _ = SkillCategory.objects.get_or_create(category_name='Programming Languages')
        self.skill, _ = Skill.objects.get_or_create(category=self.category, name='Python')
        self.pm = User.objects.create_user(
            username='alice', email='alice@example.com', password='pass12345', birth_year=1995
        )
        self.project = Project.objects.create(
            pm=self.pm, title='Secret Internal Project', short_description='Public teaser',
            full_description='CONFIDENTIAL FULL PLAN', duration_days=30,
        )
        self.role = ProjectRole.objects.create(
            project=self.project, role_title='Dev', role_description='Build things', capacity=1
        )
        self.job_ad = JobAd.objects.create(project=self.project, project_role=self.role, status=JobAd.Status.OPEN)

    def test_jobad_detail_is_public(self):
        response = Client().get(reverse('jobad_detail', args=[self.job_ad.pk]))
        self.assertEqual(response.status_code, 200)

    def test_jobad_detail_never_leaks_full_project_description(self):
        """Ads must stay a thin projection (short desc + one role's description)
        per the SRS privacy boundary - full_description must never reach the
        public ad page."""
        response = Client().get(reverse('jobad_detail', args=[self.job_ad.pk]))
        self.assertNotContains(response, self.project.full_description)

    def test_home_user_search_returns_matching_usernames(self):
        response = Client().get(reverse('home'), {'q': 'alice', 'type': 'users'})
        self.assertContains(response, 'alice')

    def test_home_ad_search_excludes_non_open_ads(self):
        self.job_ad.status = JobAd.Status.FILLED
        self.job_ad.save(update_fields=['status'])
        response = Client().get(reverse('home'), {'q': 'things', 'type': 'jobads'})
        self.assertNotContains(response, 'Build things')
