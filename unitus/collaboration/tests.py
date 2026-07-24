"""
Tests for the Ticket module (collaboration app), plain Django, no DRF.

Run with:
    python manage.py test collaboration

Mirrors the conventions used in accounts/tests.py: a local make_user()
helper, django.test.TestCase + Client, reverse() for named URLs, and
json.dumps(...) bodies with content_type="application/json" for
POST/PATCH/DELETE.
"""

import json

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from projects.models import Project, ProjectRole, ProjectMember
from collaboration.models import Ticket


def make_user(username, email, **extra):
    defaults = {"birth_year": 2000}
    defaults.update(extra)
    return User.objects.create_user(username=username, email=email, password="pass1234", **defaults)


def make_project(pm, state=Project.State.RECRUITING, **extra):
    defaults = {
        "title": "Test Project",
        "short_description": "short",
        "full_description": "full",
        "duration_days": 30,
        "state": state,
    }
    if state == Project.State.TERMINATED:
        defaults["termination_reason"] = Project.TerminationReason.SUCCESS
    defaults.update(extra)
    return Project.objects.create(pm=pm, **defaults)


def make_role(project, capacity=1, **extra):
    defaults = {"role_title": "Backend Dev", "role_description": "desc", "capacity": capacity}
    defaults.update(extra)
    return ProjectRole.objects.create(project=project, **defaults)


# ---------------------------------------------------------------------------
# POST /collaboration/tickets  (creation: application / invitation / resignation)
# ---------------------------------------------------------------------------

class CreateApplicationTicketTests(TestCase):
    def setUp(self):
        self.pm = make_user("pm", "pm@example.com")
        self.applicant = make_user("applicant", "applicant@example.com")
        self.project = make_project(self.pm)
        self.role = make_role(self.project)
        self.url = reverse("collaboration:ticket-list-create")
        self.client.force_login(self.applicant)

    def _post(self, **overrides):
        body = {"type": "application", "project_id": self.project.id, "project_role_id": self.role.id}
        body.update(overrides)
        return self.client.post(self.url, data=json.dumps(body), content_type="application/json")

    def test_requires_login(self):
        self.client.logout()
        response = self._post()
        self.assertEqual(response.status_code, 302)

    def test_creates_application_addressed_to_pm(self):
        response = self._post(message_text="Let me in!")
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["ticket_type"], Ticket.TicketType.COLLAB_REQUEST)
        self.assertEqual(data["status"], Ticket.Status.PENDING_FEEDBACK)
        self.assertEqual(data["sender"]["id"], self.applicant.id)
        self.assertEqual(data["receiver"]["id"], self.pm.id)
        self.assertEqual(data["project_role"]["id"], self.role.id)
        self.assertEqual(data["direction"], "sent")

    def test_accepts_raw_model_value_as_type(self):
        response = self._post(type=Ticket.TicketType.COLLAB_REQUEST)
        self.assertEqual(response.status_code, 201)

    def test_missing_project_role_id_400(self):
        response = self._post(project_role_id=None)
        self.assertEqual(response.status_code, 400)

    def test_unknown_type_400(self):
        response = self._post(type="not_a_real_type")
        self.assertEqual(response.status_code, 400)

    def test_nonexistent_project_404(self):
        response = self._post(project_id=999999)
        self.assertEqual(response.status_code, 404)

    def test_role_from_another_project_404(self):
        other_project = make_project(self.pm)
        other_role = make_role(other_project)
        response = self._post(project_role_id=other_role.id)
        self.assertEqual(response.status_code, 404)

    def test_rejects_when_project_not_recruiting(self):
        self.project.state = Project.State.IN_PROGRESS
        self.project.save(update_fields=["state"])
        response = self._post()
        self.assertEqual(response.status_code, 400)

    def test_rejects_when_already_active_member(self):
        ProjectMember.objects.create(
            project=self.project, user=self.applicant, member_status=ProjectMember.MemberStatus.ACTIVE
        )
        response = self._post()
        self.assertEqual(response.status_code, 400)

    def test_rejects_duplicate_pending_application(self):
        self._post()
        response = self._post()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Ticket.objects.count(), 1)

    def test_allows_reapplication_after_previous_was_rejected(self):
        first = self._post()
        ticket = Ticket.objects.get(id=first.json()["id"])
        ticket.status = Ticket.Status.CLOSED_REJECTED
        ticket.save(update_fields=["status"])
        response = self._post()
        self.assertEqual(response.status_code, 201)


class CreateInvitationTicketTests(TestCase):
    def setUp(self):
        self.pm = make_user("pm2", "pm2@example.com")
        self.other_user = make_user("otherpm", "otherpm@example.com")
        self.invitee = make_user("invitee", "invitee@example.com")
        self.project = make_project(self.pm)
        self.role = make_role(self.project)
        self.url = reverse("collaboration:ticket-list-create")

    def _post(self, as_user, **overrides):
        self.client.force_login(as_user)
        body = {
            "type": "invitation",
            "project_id": self.project.id,
            "project_role_id": self.role.id,
            "receiver_id": self.invitee.id,
        }
        body.update(overrides)
        return self.client.post(self.url, data=json.dumps(body), content_type="application/json")

    def test_pm_can_invite(self):
        response = self._post(self.pm)
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["ticket_type"], Ticket.TicketType.INVITATION)
        self.assertEqual(data["sender"]["id"], self.pm.id)
        self.assertEqual(data["receiver"]["id"], self.invitee.id)

    def test_non_pm_cannot_invite(self):
        response = self._post(self.other_user)
        self.assertEqual(response.status_code, 403)

    def test_nonexistent_invitee_404(self):
        response = self._post(self.pm, receiver_id=999999)
        self.assertEqual(response.status_code, 404)

    def test_cannot_invite_already_active_member(self):
        ProjectMember.objects.create(
            project=self.project, user=self.invitee, member_status=ProjectMember.MemberStatus.ACTIVE
        )
        response = self._post(self.pm)
        self.assertEqual(response.status_code, 400)

    def test_rejects_duplicate_pending_invitation(self):
        self._post(self.pm)
        response = self._post(self.pm)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Ticket.objects.count(), 1)


class CreateResignationTicketTests(TestCase):
    def setUp(self):
        self.pm = make_user("pm3", "pm3@example.com")
        self.member = make_user("member", "member@example.com")
        self.project = make_project(self.pm, state=Project.State.IN_PROGRESS)
        self.role = make_role(self.project)
        self.membership = ProjectMember.objects.create(
            project=self.project, user=self.member, project_role=self.role,
            member_status=ProjectMember.MemberStatus.ACTIVE,
        )
        self.url = reverse("collaboration:ticket-list-create")
        self.client.force_login(self.member)

    def _post(self, **overrides):
        body = {"type": "resignation", "project_id": self.project.id}
        body.update(overrides)
        return self.client.post(self.url, data=json.dumps(body), content_type="application/json")

    def test_resignation_with_explicit_role(self):
        response = self._post(project_role_id=self.role.id)
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["ticket_type"], Ticket.TicketType.RESIGNATION)
        self.assertEqual(data["receiver"]["id"], self.pm.id)
        self.assertEqual(data["project_role"]["id"], self.role.id)

    def test_resignation_falls_back_to_lookup_when_role_omitted(self):
        response = self._post()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["project_role"]["id"], self.role.id)

    def test_non_member_cannot_resign(self):
        outsider = make_user("outsider", "outsider@example.com")
        self.client.force_login(outsider)
        response = self._post()
        self.assertEqual(response.status_code, 400)

    def test_explicit_role_not_matching_active_membership_400(self):
        other_role = make_role(self.project, role_title="Other Role")
        response = self._post(project_role_id=other_role.id)
        self.assertEqual(response.status_code, 400)

    def test_schema_prevents_multiple_memberships_per_project(self):
        # unique_project_member_pk is on (project, user), so a user can only
        # ever have ONE ProjectMember row per project. This means the
        # "multiple active roles, specify project_role_id" branch in
        # _create_resignation is currently unreachable dead code — this test
        # documents that constraint so it's obvious if the schema ever
        # changes to allow multiple roles per user per project.
        from django.db import IntegrityError, transaction

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ProjectMember.objects.create(
                    project=self.project, user=self.member,
                    member_status=ProjectMember.MemberStatus.ACTIVE,
                )

    def test_rejects_duplicate_pending_resignation(self):
        self._post()
        response = self._post()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Ticket.objects.count(), 1)


# ---------------------------------------------------------------------------
# GET /collaboration/tickets/:id , DELETE /collaboration/tickets/:id
# ---------------------------------------------------------------------------

class TicketDetailViewTests(TestCase):
    def setUp(self):
        self.pm = make_user("pm4", "pm4@example.com")
        self.applicant = make_user("applicant2", "applicant2@example.com")
        self.outsider = make_user("outsider2", "outsider2@example.com")
        self.project = make_project(self.pm)
        self.role = make_role(self.project)
        self.ticket = Ticket.objects.create(
            sender=self.applicant, receiver=self.pm, project=self.project, project_role=self.role,
            ticket_type=Ticket.TicketType.COLLAB_REQUEST,
        )
        self.url = reverse("collaboration:ticket-detail", kwargs={"ticket_id": self.ticket.id})

    def test_requires_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_sender_can_view(self):
        self.client.force_login(self.applicant)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["direction"], "sent")

    def test_receiver_can_view(self):
        self.client.force_login(self.pm)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["direction"], "received")

    def test_uninvolved_user_gets_404(self):
        self.client.force_login(self.outsider)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    def test_nonexistent_ticket_404(self):
        self.client.force_login(self.pm)
        response = self.client.get(reverse("collaboration:ticket-detail", kwargs={"ticket_id": 999999}))
        self.assertEqual(response.status_code, 404)

    def test_sender_can_cancel_pending_ticket(self):
        self.client.force_login(self.applicant)
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, 200)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.CANCELLED)

    def test_receiver_cannot_cancel(self):
        self.client.force_login(self.pm)
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, 403)

    def test_cannot_cancel_already_resolved_ticket(self):
        self.ticket.status = Ticket.Status.CLOSED_ACCEPTED
        self.ticket.save(update_fields=["status"])
        self.client.force_login(self.applicant)
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, 400)


# ---------------------------------------------------------------------------
# GET /collaboration/tickets?type=&status=
# ---------------------------------------------------------------------------

class TicketListViewTests(TestCase):
    def setUp(self):
        self.pm = make_user("pm5", "pm5@example.com")
        self.user_a = make_user("usera", "usera@example.com")
        self.user_b = make_user("userb", "userb@example.com")
        self.project = make_project(self.pm)
        self.role = make_role(self.project)
        self.url = reverse("collaboration:ticket-list-create")

        # user_a sent an application to pm, still pending -> from user_a's
        # view this is "pending_their_response" (waiting on pm).
        self.sent_pending = Ticket.objects.create(
            sender=self.user_a, receiver=self.pm, project=self.project, project_role=self.role,
            ticket_type=Ticket.TicketType.COLLAB_REQUEST,
        )
        # pm invited user_a, still pending -> from user_a's view this is
        # "pending_our_response" (needs user_a's action).
        role2 = make_role(self.project, role_title="Role 2")
        self.received_pending = Ticket.objects.create(
            sender=self.pm, receiver=self.user_a, project=self.project, project_role=role2,
            ticket_type=Ticket.TicketType.INVITATION,
        )
        # a closed ticket involving user_a
        role3 = make_role(self.project, role_title="Role 3")
        self.closed_ticket = Ticket.objects.create(
            sender=self.user_a, receiver=self.pm, project=self.project, project_role=role3,
            ticket_type=Ticket.TicketType.COLLAB_REQUEST, status=Ticket.Status.CLOSED_REJECTED,
        )
        # a ticket not involving user_a at all
        role4 = make_role(self.project, role_title="Role 4")
        self.unrelated_ticket = Ticket.objects.create(
            sender=self.user_b, receiver=self.pm, project=self.project, project_role=role4,
            ticket_type=Ticket.TicketType.COLLAB_REQUEST,
        )
        self.client.force_login(self.user_a)

    def test_lists_only_tickets_involving_user(self):
        response = self.client.get(self.url)
        ids = {t["id"] for t in response.json()["tickets"]}
        self.assertEqual(
            ids, {self.sent_pending.id, self.received_pending.id, self.closed_ticket.id}
        )

    def test_filter_pending_their_response(self):
        response = self.client.get(self.url, {"status": "pending_their_response"})
        ids = {t["id"] for t in response.json()["tickets"]}
        self.assertEqual(ids, {self.sent_pending.id})

    def test_filter_pending_our_response(self):
        response = self.client.get(self.url, {"status": "pending_our_response"})
        ids = {t["id"] for t in response.json()["tickets"]}
        self.assertEqual(ids, {self.received_pending.id})

    def test_filter_closed(self):
        response = self.client.get(self.url, {"status": "closed"})
        ids = {t["id"] for t in response.json()["tickets"]}
        self.assertEqual(ids, {self.closed_ticket.id})

    def test_filter_by_type(self):
        response = self.client.get(self.url, {"type": "invitation"})
        ids = {t["id"] for t in response.json()["tickets"]}
        self.assertEqual(ids, {self.received_pending.id})

    def test_invalid_status_400(self):
        response = self.client.get(self.url, {"status": "not_a_real_status"})
        self.assertEqual(response.status_code, 400)

    def test_invalid_type_400(self):
        response = self.client.get(self.url, {"type": "not_a_real_type"})
        self.assertEqual(response.status_code, 400)


# ---------------------------------------------------------------------------
# PATCH /collaboration/tickets/:id/respond
# ---------------------------------------------------------------------------

class TicketRespondViewTests(TestCase):
    def setUp(self):
        self.pm = make_user("pm6", "pm6@example.com")
        self.applicant = make_user("applicant3", "applicant3@example.com")
        self.project = make_project(self.pm)
        self.role = make_role(self.project, capacity=1)
        self.ticket = Ticket.objects.create(
            sender=self.applicant, receiver=self.pm, project=self.project, project_role=self.role,
            ticket_type=Ticket.TicketType.COLLAB_REQUEST,
        )
        self.url = reverse("collaboration:ticket-respond", kwargs={"ticket_id": self.ticket.id})

    def _patch(self, as_user, action):
        self.client.force_login(as_user)
        return self.client.patch(
            self.url, data=json.dumps({"action": action}), content_type="application/json"
        )

    def test_only_receiver_can_respond(self):
        response = self._patch(self.applicant, "approve")
        self.assertEqual(response.status_code, 404)

    def test_approve_application_creates_active_membership(self):
        response = self._patch(self.pm, "approve")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], Ticket.Status.CLOSED_ACCEPTED)
        membership = ProjectMember.objects.get(project=self.project, user=self.applicant)
        self.assertEqual(membership.member_status, ProjectMember.MemberStatus.ACTIVE)
        self.assertEqual(membership.project_role_id, self.role.id)

    def test_reject_application_does_not_create_membership(self):
        response = self._patch(self.pm, "reject")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], Ticket.Status.CLOSED_REJECTED)
        self.assertFalse(ProjectMember.objects.filter(project=self.project, user=self.applicant).exists())

    def test_approve_invitation_adds_invited_user_not_pm(self):
        invitee = make_user("invitee2", "invitee2@example.com")
        role2 = make_role(self.project, role_title="Role X")
        invitation = Ticket.objects.create(
            sender=self.pm, receiver=invitee, project=self.project, project_role=role2,
            ticket_type=Ticket.TicketType.INVITATION,
        )
        url = reverse("collaboration:ticket-respond", kwargs={"ticket_id": invitation.id})
        self.client.force_login(invitee)
        response = self.client.patch(
            url, data=json.dumps({"action": "approve"}), content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        membership = ProjectMember.objects.get(project=self.project, user=invitee)
        self.assertEqual(membership.project_role_id, role2.id)
        self.assertFalse(ProjectMember.objects.filter(project=self.project, user=self.pm).exists())

    def test_cannot_approve_when_role_at_capacity(self):
        # fill the only slot with someone else first
        other_member = make_user("othermember", "othermember@example.com")
        ProjectMember.objects.create(
            project=self.project, user=other_member, project_role=self.role,
            member_status=ProjectMember.MemberStatus.ACTIVE,
        )
        response = self._patch(self.pm, "approve")
        self.assertEqual(response.status_code, 400)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.PENDING_FEEDBACK)

    def test_approve_resignation_sets_member_resigned(self):
        member = make_user("resigningmember", "resigningmember@example.com")
        ProjectMember.objects.create(
            project=self.project, user=member, project_role=self.role,
            member_status=ProjectMember.MemberStatus.ACTIVE,
        )
        resignation = Ticket.objects.create(
            sender=member, receiver=self.pm, project=self.project, project_role=self.role,
            ticket_type=Ticket.TicketType.RESIGNATION,
        )
        url = reverse("collaboration:ticket-respond", kwargs={"ticket_id": resignation.id})
        self.client.force_login(self.pm)
        response = self.client.patch(
            url, data=json.dumps({"action": "approve"}), content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        membership = ProjectMember.objects.get(project=self.project, user=member)
        self.assertEqual(membership.member_status, ProjectMember.MemberStatus.RESIGNED)

    def test_cannot_respond_to_already_resolved_ticket(self):
        self._patch(self.pm, "approve")
        response = self._patch(self.pm, "reject")
        self.assertEqual(response.status_code, 400)

    def test_invalid_action_400(self):
        response = self._patch(self.pm, "maybe")
        self.assertEqual(response.status_code, 400)

    def test_invalid_json_400(self):
        self.client.force_login(self.pm)
        response = self.client.patch(self.url, data="{not json", content_type="application/json")
        self.assertEqual(response.status_code, 400)


# ---------------------------------------------------------------------------
# GET /collaboration/tickets/history
# ---------------------------------------------------------------------------

class TicketHistoryViewTests(TestCase):
    def setUp(self):
        self.pm = make_user("pm7", "pm7@example.com")
        self.user_a = make_user("usera2", "usera2@example.com")
        self.user_b = make_user("userb2", "userb2@example.com")
        self.project = make_project(self.pm)
        self.role = make_role(self.project)
        self.url = reverse("collaboration:ticket-history")

    def test_requires_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_includes_all_statuses_for_user(self):
        pending = Ticket.objects.create(
            sender=self.user_a, receiver=self.pm, project=self.project, project_role=self.role,
            ticket_type=Ticket.TicketType.COLLAB_REQUEST,
        )
        role2 = make_role(self.project, role_title="Role 2")
        closed = Ticket.objects.create(
            sender=self.user_a, receiver=self.pm, project=self.project, project_role=role2,
            ticket_type=Ticket.TicketType.COLLAB_REQUEST, status=Ticket.Status.CLOSED_ACCEPTED,
        )
        role3 = make_role(self.project, role_title="Role 3")
        unrelated = Ticket.objects.create(
            sender=self.user_b, receiver=self.pm, project=self.project, project_role=role3,
            ticket_type=Ticket.TicketType.COLLAB_REQUEST,
        )

        self.client.force_login(self.user_a)
        response = self.client.get(self.url)
        ids = {t["id"] for t in response.json()["tickets"]}
        self.assertEqual(ids, {pending.id, closed.id})
        self.assertNotIn(unrelated.id, ids)

    def test_ordered_newest_first(self):
        role2 = make_role(self.project, role_title="Role 2")
        first = Ticket.objects.create(
            sender=self.user_a, receiver=self.pm, project=self.project, project_role=self.role,
            ticket_type=Ticket.TicketType.COLLAB_REQUEST,
        )
        second = Ticket.objects.create(
            sender=self.user_a, receiver=self.pm, project=self.project, project_role=role2,
            ticket_type=Ticket.TicketType.COLLAB_REQUEST,
        )
        self.client.force_login(self.user_a)
        response = self.client.get(self.url)
        ids_in_order = [t["id"] for t in response.json()["tickets"]]
        self.assertEqual(ids_in_order, [second.id, first.id])
