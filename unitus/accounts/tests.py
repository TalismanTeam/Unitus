"""
Tests for the User & Profile module (accounts app), plain Django, no DRF.

Run with:
    python manage.py test accounts

If accounts/tests.py already exists in your project, merge this in rather
than overwriting it (or rename this to e.g. accounts/tests_api.py and turn
accounts/tests.py + this file into an accounts/tests/ package with an
__init__.py — Django's test runner picks up any test*.py module either way).
"""

import json

from django.test import TestCase
from django.urls import reverse

from accounts.models import User, Avatar, UserPrivacySettings
from skills.models import SkillCategory, Skill, UserSkill
from skills.choices import MasteryLevel
from moderation.models import Report
from projects.models import Project, ProjectMember
from reviews.models import Review


def make_user(username, email, **extra):
    defaults = {"birth_year": 2000}
    defaults.update(extra)
    return User.objects.create_user(username=username, email=email, password="pass1234", **defaults)


class MeViewTests(TestCase):
    def setUp(self):
        self.user = make_user("alice", "alice@example.com", first_name="Alice", last_name="A")
        self.url = reverse("accounts:me")

    def test_requires_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)  # redirected to login

    def test_get_returns_own_profile(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["username"], "alice")
        self.assertEqual(data["email"], "alice@example.com")
        self.assertIn("privacy_settings", data)
        self.assertIn("skills", data)
        self.assertIn("about_me", data)

    def test_patch_updates_allowed_fields(self):
        self.client.force_login(self.user)
        response = self.client.patch(
            self.url,
            data=json.dumps({"first_name": "Alicia", "about_me": "Hello world"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Alicia")
        self.assertEqual(self.user.about_me, "Hello world")

    def test_patch_rejects_invalid_gender(self):
        self.client.force_login(self.user)
        response = self.client.patch(
            self.url,
            data=json.dumps({"gender": "NOT_A_REAL_CHOICE"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_patch_rejects_non_integer_birth_year(self):
        self.client.force_login(self.user)
        response = self.client.patch(
            self.url,
            data=json.dumps({"birth_year": "not-a-year"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_patch_rejects_invalid_json(self):
        self.client.force_login(self.user)
        response = self.client.patch(
            self.url, data="{not json", content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_patch_cannot_change_username_or_email(self):
        # username/email aren't in ME_PATCHABLE_FIELDS, so sending them
        # should just be silently ignored, not applied.
        self.client.force_login(self.user)
        self.client.patch(
            self.url,
            data=json.dumps({"username": "hacker", "email": "new@example.com"}),
            content_type="application/json",
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "alice")
        self.assertEqual(self.user.email, "alice@example.com")


class OpenToWorkViewTests(TestCase):
    def setUp(self):
        self.user = make_user("bob", "bob@example.com")
        self.url = reverse("accounts:open-to-work")

    def test_toggle_on(self):
        self.client.force_login(self.user)
        response = self.client.patch(
            self.url, data=json.dumps({"is_open_to_work": True}), content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"is_open_to_work": True})
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_open_to_work)

    def test_rejects_non_boolean(self):
        self.client.force_login(self.user)
        response = self.client.patch(
            self.url, data=json.dumps({"is_open_to_work": "yes"}), content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_rejects_missing_field(self):
        self.client.force_login(self.user)
        response = self.client.patch(self.url, data=json.dumps({}), content_type="application/json")
        self.assertEqual(response.status_code, 400)


class AvatarViewsTests(TestCase):
    def setUp(self):
        self.user = make_user("carol", "carol@example.com")
        self.avatar1 = Avatar.objects.create(icon_name="fox", image_url_path="/icons/fox.png")
        self.avatar2 = Avatar.objects.create(icon_name="owl", image_url_path="/icons/owl.png")
        self.client.force_login(self.user)

    def test_avatar_options_lists_all(self):
        response = self.client.get(reverse("accounts:avatar-options"))
        self.assertEqual(response.status_code, 200)
        names = {a["icon_name"] for a in response.json()}
        self.assertEqual(names, {"fox", "owl"})

    def test_select_avatar(self):
        response = self.client.patch(
            reverse("accounts:avatar-select"),
            data=json.dumps({"avatar_icon": self.avatar1.id}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.avatar_icon_id, self.avatar1.id)

    def test_clear_avatar_with_null(self):
        self.user.avatar_icon = self.avatar1
        self.user.save(update_fields=["avatar_icon"])
        response = self.client.patch(
            reverse("accounts:avatar-select"),
            data=json.dumps({"avatar_icon": None}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertIsNone(self.user.avatar_icon)

    def test_select_nonexistent_avatar_404s(self):
        response = self.client.patch(
            reverse("accounts:avatar-select"),
            data=json.dumps({"avatar_icon": 9999}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)


class SkillsViewsTests(TestCase):
    def setUp(self):
        self.user = make_user("dave", "dave@example.com")
        self.other_user = make_user("erin", "erin@example.com")
        category = SkillCategory.objects.create(category_name="Programming")
        self.skill = Skill.objects.create(category=category, name="Python")
        self.other_skill = Skill.objects.create(category=category, name="Django")
        # Grab two real, valid choice values instead of guessing exact strings.
        self.level_a = MasteryLevel.choices[0][0]
        self.level_b = MasteryLevel.choices[1][0]
        self.client.force_login(self.user)

    def test_list_empty_initially(self):
        response = self.client.get(reverse("accounts:my-skills"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_add_skill(self):
        response = self.client.post(
            reverse("accounts:my-skills"),
            data=json.dumps({"skill": self.skill.id, "mastery_level": self.level_a}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["skill_name"], "Python")
        self.assertEqual(data["mastery_level"], self.level_a)
        self.assertTrue(UserSkill.objects.filter(user=self.user, skill=self.skill).exists())

    def test_cannot_add_duplicate_skill(self):
        UserSkill.objects.create(user=self.user, skill=self.skill, mastery_level=self.level_a)
        response = self.client.post(
            reverse("accounts:my-skills"),
            data=json.dumps({"skill": self.skill.id, "mastery_level": self.level_b}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_rejects_invalid_mastery_level(self):
        response = self.client.post(
            reverse("accounts:my-skills"),
            data=json.dumps({"skill": self.skill.id, "mastery_level": "NOT_REAL"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_update_mastery_level(self):
        user_skill = UserSkill.objects.create(user=self.user, skill=self.skill, mastery_level=self.level_a)
        url = reverse("accounts:my-skill-detail", kwargs={"skill_id": user_skill.id})
        response = self.client.patch(
            url, data=json.dumps({"mastery_level": self.level_b}), content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        user_skill.refresh_from_db()
        self.assertEqual(user_skill.mastery_level, self.level_b)

    def test_delete_skill(self):
        user_skill = UserSkill.objects.create(user=self.user, skill=self.skill, mastery_level=self.level_a)
        url = reverse("accounts:my-skill-detail", kwargs={"skill_id": user_skill.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(UserSkill.objects.filter(pk=user_skill.id).exists())

    def test_cannot_edit_other_users_skill(self):
        other_users_skill = UserSkill.objects.create(
            user=self.other_user, skill=self.skill, mastery_level=self.level_a
        )
        url = reverse("accounts:my-skill-detail", kwargs={"skill_id": other_users_skill.id})
        response = self.client.patch(
            url, data=json.dumps({"mastery_level": self.level_b}), content_type="application/json"
        )
        self.assertEqual(response.status_code, 404)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 404)
        self.assertTrue(UserSkill.objects.filter(pk=other_users_skill.id).exists())


class WorkPreferencesViewTests(TestCase):
    def test_returns_501_stub(self):
        user = make_user("frank", "frank@example.com")
        self.client.force_login(user)
        response = self.client.patch(
            reverse("accounts:work-preferences"),
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 501)


class PublicProfileViewTests(TestCase):
    def setUp(self):
        self.viewer = make_user("viewer", "viewer@example.com")
        self.target = make_user(
            "target", "target@example.com",
            phone_number="+19995550000", location="Berlin",
            gender=User.Gender.MALE, first_name="Target", last_name="User",
        )
        self.client.force_login(self.viewer)

    def test_404_for_nonexistent_user(self):
        response = self.client.get(reverse("accounts:public-profile", kwargs={"id": 999999}))
        self.assertEqual(response.status_code, 404)

    def test_privacy_defaults_hide_phone_and_email_show_location(self):
        # UserPrivacySettings model defaults: show_phone/show_email = False,
        # show_location/show_birth_year/show_education_background/show_gender = True.
        UserPrivacySettings.objects.create(user=self.target)
        response = self.client.get(reverse("accounts:public-profile", kwargs={"id": self.target.id}))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsNone(data["phone_number"])
        self.assertIsNone(data["email"])
        self.assertEqual(data["location"], "Berlin")
        self.assertEqual(data["gender"], User.Gender.MALE)

    def test_no_privacy_settings_row_hides_everything_gated(self):
        # No UserPrivacySettings row at all -> _get_privacy_settings returns
        # None -> every gated() field falls back to None.
        response = self.client.get(reverse("accounts:public-profile", kwargs={"id": self.target.id}))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        for field in ("phone_number", "email", "location", "birth_year", "education_background", "gender"):
            self.assertIsNone(data[field])
        # Always-public fields still show regardless of privacy settings.
        self.assertEqual(data["username"], "target")

    def test_show_phone_true_reveals_phone(self):
        UserPrivacySettings.objects.create(user=self.target, show_phone=True)
        response = self.client.get(reverse("accounts:public-profile", kwargs={"id": self.target.id}))
        self.assertEqual(response.json()["phone_number"], "+19995550000")

    def test_active_projects_count_and_avg_rating_present(self):
        response = self.client.get(reverse("accounts:public-profile", kwargs={"id": self.target.id}))
        data = response.json()
        self.assertEqual(data["active_projects_count"], 0)
        self.assertIsNone(data["avg_rating"])


class ActiveProjectsCountViewTests(TestCase):
    def setUp(self):
        self.viewer = make_user("viewer2", "viewer2@example.com")
        self.target = make_user("target2", "target2@example.com")
        self.pm = make_user("pm1", "pm1@example.com")
        self.client.force_login(self.viewer)

    def _make_project(self, state=Project.State.IN_PROGRESS):
        return Project.objects.create(
            pm=self.pm, title="P", short_description="short", full_description="full",
            duration_days=30, state=state,
            termination_reason=(Project.TerminationReason.SUCCESS if state == Project.State.TERMINATED else None),
        )

    def test_zero_when_no_memberships(self):
        response = self.client.get(
            reverse("accounts:active-projects-count", kwargs={"id": self.target.id})
        )
        self.assertEqual(response.json(), {"active_projects_count": 0})

    def test_counts_active_membership_on_non_terminated_project(self):
        project = self._make_project(state=Project.State.IN_PROGRESS)
        ProjectMember.objects.create(project=project, user=self.target, member_status=ProjectMember.MemberStatus.ACTIVE)
        response = self.client.get(
            reverse("accounts:active-projects-count", kwargs={"id": self.target.id})
        )
        self.assertEqual(response.json(), {"active_projects_count": 1})

    def test_excludes_terminated_project(self):
        project = self._make_project(state=Project.State.TERMINATED)
        ProjectMember.objects.create(project=project, user=self.target, member_status=ProjectMember.MemberStatus.ACTIVE)
        response = self.client.get(
            reverse("accounts:active-projects-count", kwargs={"id": self.target.id})
        )
        self.assertEqual(response.json(), {"active_projects_count": 0})

    def test_excludes_resigned_membership(self):
        project = self._make_project(state=Project.State.IN_PROGRESS)
        ProjectMember.objects.create(project=project, user=self.target, member_status=ProjectMember.MemberStatus.RESIGNED)
        response = self.client.get(
            reverse("accounts:active-projects-count", kwargs={"id": self.target.id})
        )
        self.assertEqual(response.json(), {"active_projects_count": 0})


class DashboardProjectsViewTests(TestCase):
    def setUp(self):
        self.user = make_user("pmuser", "pmuser@example.com")
        self.other_pm = make_user("otherpm", "otherpm@example.com")
        self.client.force_login(self.user)
        self.url = reverse("accounts:dashboard-projects")

    def _project(self, pm, state, **kw):
        return Project.objects.create(
            pm=pm, title="P", short_description="s", full_description="f",
            duration_days=10, state=state,
            termination_reason=(Project.TerminationReason.SUCCESS if state == Project.State.TERMINATED else None),
            **kw,
        )

    def test_invalid_tab_400(self):
        response = self.client.get(self.url, {"tab": "not_a_real_tab"})
        self.assertEqual(response.status_code, 400)

    def test_managed_excludes_terminated(self):
        active_managed = self._project(self.user, Project.State.IN_PROGRESS)
        self._project(self.user, Project.State.TERMINATED)
        response = self.client.get(self.url, {"tab": "managed"})
        ids = {p["id"] for p in response.json()}
        self.assertEqual(ids, {active_managed.id})

    def test_managed_excludes_other_pms_projects(self):
        self._project(self.other_pm, Project.State.IN_PROGRESS)
        response = self.client.get(self.url, {"tab": "managed"})
        self.assertEqual(response.json(), [])

    def test_in_progress_tab_includes_managed_and_member_projects(self):
        managed = self._project(self.user, Project.State.IN_PROGRESS)
        member_project = self._project(self.other_pm, Project.State.IN_PROGRESS)
        ProjectMember.objects.create(
            project=member_project, user=self.user, member_status=ProjectMember.MemberStatus.ACTIVE
        )
        # a project the user is neither PM nor active member of
        self._project(self.other_pm, Project.State.IN_PROGRESS)

        response = self.client.get(self.url, {"tab": "in_progress"})
        ids = {p["id"] for p in response.json()}
        self.assertEqual(ids, {managed.id, member_project.id})

    def test_completed_tab_maps_to_terminated_state(self):
        terminated = self._project(self.user, Project.State.TERMINATED)
        self._project(self.user, Project.State.IN_PROGRESS)
        response = self.client.get(self.url, {"tab": "completed"})
        ids = {p["id"] for p in response.json()}
        self.assertEqual(ids, {terminated.id})

    def test_all_tab_includes_everything_even_terminated(self):
        managed_active = self._project(self.user, Project.State.IN_PROGRESS)
        managed_terminated = self._project(self.user, Project.State.TERMINATED)
        response = self.client.get(self.url, {"tab": "all"})
        ids = {p["id"] for p in response.json()}
        self.assertEqual(ids, {managed_active.id, managed_terminated.id})

    def test_is_pm_flag_set_correctly(self):
        managed = self._project(self.user, Project.State.IN_PROGRESS)
        member_project = self._project(self.other_pm, Project.State.IN_PROGRESS)
        ProjectMember.objects.create(
            project=member_project, user=self.user, member_status=ProjectMember.MemberStatus.ACTIVE
        )
        response = self.client.get(self.url, {"tab": "all"})
        by_id = {p["id"]: p for p in response.json()}
        self.assertTrue(by_id[managed.id]["is_pm"])
        self.assertFalse(by_id[member_project.id]["is_pm"])


class ReportUserViewTests(TestCase):
    def setUp(self):
        self.reporter = make_user("reporter", "reporter@example.com")
        self.target = make_user("reported", "reported@example.com")
        self.client.force_login(self.reporter)

    def _url(self, user_id):
        return reverse("accounts:report-user", kwargs={"id": user_id})

    def test_create_report(self):
        response = self.client.post(
            self._url(self.target.id),
            data=json.dumps({"reason": Report.Reason.INSULTING, "description": "was rude"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["reason"], Report.Reason.INSULTING)
        self.assertEqual(data["status"], Report.Status.PENDING_REVIEW)
        report = Report.objects.get(pk=data["id"])
        self.assertEqual(report.reporter_id, self.reporter.id)
        self.assertEqual(report.reported_user_id, self.target.id)

    def test_cannot_report_self(self):
        response = self.client.post(
            self._url(self.reporter.id),
            data=json.dumps({"reason": Report.Reason.OTHER}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Report.objects.exists())

    def test_rejects_invalid_reason(self):
        response = self.client.post(
            self._url(self.target.id),
            data=json.dumps({"reason": "NOT_A_REAL_REASON"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_404_for_nonexistent_target(self):
        response = self.client.post(
            self._url(999999),
            data=json.dumps({"reason": Report.Reason.OTHER}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)
