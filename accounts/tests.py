from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from catalog.models import Faculty, University

from .models import ContributorInvitation, ContributorScope, ModeratorScope, User


class AuthPageTests(TestCase):
    def test_login_and_logout(self):
        get_user_model().objects.create_user(
            username="student",
            password="strong-test-password",
        )

        login_response = self.client.post(
            reverse("accounts:login"),
            {"username": "student", "password": "strong-test-password"},
        )
        self.assertEqual(login_response.status_code, 302)

        logout_response = self.client.post(reverse("accounts:logout"))
        self.assertEqual(logout_response.status_code, 302)

    def test_public_pages_do_not_require_login(self):
        for path in ["/ar/", "/ar/browse/"]:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)


class InvitationTests(TestCase):
    def setUp(self):
        call_command("seed_demo_catalog")
        self.university = University.objects.get(name="جامعة تشرين")
        self.faculty = Faculty.objects.get(name="كلية الاقتصاد")
        self.user = get_user_model().objects.create_user(
            username="contributor",
            email="contributor@example.test",
            password="strong-test-password",
        )

    def make_invitation(self, **overrides):
        values = {
            "invited_identifier": self.user.email,
            "requested_role": User.Role.TRUSTED_CONTRIBUTOR,
            "university": self.university,
            "faculty": self.faculty,
            "expires_at": timezone.now() + timedelta(days=3),
        }
        values.update(overrides)
        return ContributorInvitation.objects.create(**values)

    def test_create_contributor_invitation(self):
        invitation = self.make_invitation()

        self.assertEqual(invitation.status, ContributorInvitation.Status.PENDING)
        self.assertTrue(invitation.token)
        self.assertTrue(invitation.can_accept())
        self.assertEqual(invitation.faculty, self.faculty)

    def test_accept_invitation_once_only(self):
        invitation = self.make_invitation()
        self.client.force_login(self.user)

        first = self.client.post(
            reverse("accounts:accept_invitation", args=[invitation.token]),
        )
        second = self.client.post(
            reverse("accounts:accept_invitation", args=[invitation.token]),
        )
        invitation.refresh_from_db()
        self.user.refresh_from_db()

        self.assertEqual(first.status_code, 302)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(invitation.status, ContributorInvitation.Status.ACCEPTED)
        self.assertEqual(self.user.role, User.Role.TRUSTED_CONTRIBUTOR)
        self.assertEqual(ContributorScope.objects.filter(user=self.user).count(), 1)

    def test_revoked_invitation_cannot_be_accepted(self):
        invitation = self.make_invitation(status=ContributorInvitation.Status.REVOKED)
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("accounts:accept_invitation", args=[invitation.token]),
        )
        self.user.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.user.role, User.Role.STUDENT)
        self.assertFalse(ContributorScope.objects.filter(user=self.user).exists())

    def test_expired_invitation_cannot_be_accepted(self):
        invitation = self.make_invitation(
            expires_at=timezone.now() - timedelta(days=1),
        )
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("accounts:accept_invitation", args=[invitation.token]),
        )
        invitation.refresh_from_db()
        self.user.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(invitation.status, ContributorInvitation.Status.EXPIRED)
        self.assertEqual(self.user.role, User.Role.STUDENT)

    def test_trusted_contributor_does_not_get_publish_permission(self):
        invitation = self.make_invitation()

        invitation.accept(self.user)
        self.user.refresh_from_db()

        self.assertEqual(self.user.role, User.Role.TRUSTED_CONTRIBUTOR)
        self.assertFalse(self.user.can_publish_documents)
        self.assertFalse(self.user.is_superuser)

    def test_faculty_moderator_is_not_superuser(self):
        invitation = self.make_invitation(
            requested_role=User.Role.FACULTY_MODERATOR,
        )

        invitation.accept(self.user)
        self.user.refresh_from_db()

        self.assertEqual(self.user.role, User.Role.FACULTY_MODERATOR)
        self.assertFalse(self.user.is_superuser)
        self.assertEqual(ModeratorScope.objects.filter(user=self.user).count(), 1)

    def test_contributor_scope_is_not_site_wide_by_default(self):
        invitation = self.make_invitation()

        invitation.accept(self.user)
        scope = ContributorScope.objects.get(user=self.user)

        self.assertEqual(scope.university, self.university)
        self.assertEqual(scope.faculty, self.faculty)
        self.assertIsNone(scope.program)
        self.assertIsNone(scope.course)

    def test_scope_requires_a_boundary(self):
        invitation = ContributorInvitation(
            invited_identifier=self.user.email,
            requested_role=User.Role.TRUSTED_CONTRIBUTOR,
            expires_at=timezone.now() + timedelta(days=3),
        )

        with self.assertRaises(ValidationError):
            invitation.clean()
