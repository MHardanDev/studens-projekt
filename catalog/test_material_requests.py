from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from accounts.models import ModeratorScope, User

from .models import Faculty, MissingMaterialRequest, StudyDocument
from .publication import published_documents


class MissingMaterialRequestTests(TestCase):
    def setUp(self):
        cache.clear()
        call_command("seed_demo_catalog")
        self.faculty = Faculty.objects.get(name="كلية الاقتصاد")
        offerings = list(
            self.faculty.programs.get().course_offerings.select_related("course")[:2],
        )
        self.offering = offerings[0]
        self.other_offering = offerings[1]
        self.moderator = get_user_model().objects.create_user(
            username="request-moderator",
            password="strong-test-password",
            role=User.Role.FACULTY_MODERATOR,
        )
        self.outside_moderator = get_user_model().objects.create_user(
            username="outside-request-moderator",
            password="strong-test-password",
            role=User.Role.FACULTY_MODERATOR,
        )
        self.contributor = get_user_model().objects.create_user(
            username="request-contributor",
            password="strong-test-password",
            role=User.Role.TRUSTED_CONTRIBUTOR,
        )
        ModeratorScope.objects.create(
            user=self.moderator,
            course=self.offering.course,
        )
        ModeratorScope.objects.create(
            user=self.outside_moderator,
            course=self.other_offering.course,
        )
        self.public_url = reverse("catalog:request_material")
        self.management_url = reverse("catalog:moderation_material_requests")

    def valid_data(self, offering=None, description="أحتاج ملخصاً قبل الامتحان."):
        return {
            "offering": (offering or self.offering).id,
            "request_type": StudyDocument.ContentType.SUMMARY,
            "description": description,
            "student_name": "طالب تجريبي",
            "email": "student-private@example.com",
        }

    def make_request(self, offering=None, **kwargs):
        defaults = {
            "offering": offering or self.offering,
            "request_type": StudyDocument.ContentType.SUMMARY,
            "description": "طلب للاختبار الإداري.",
            "student_name": "طالب",
            "email": "private@example.com",
        }
        defaults.update(kwargs)
        return MissingMaterialRequest.objects.create(**defaults)

    def moderation_data(self, material_request, status, **kwargs):
        prefix = f"request-{material_request.id}"
        return {
            "request_id": material_request.id,
            f"{prefix}-status": status,
            f"{prefix}-supervisor_notes": kwargs.get("notes", "تمت المراجعة."),
            f"{prefix}-fulfilled_document": kwargs.get("document", ""),
        }

    def test_valid_anonymous_request_succeeds(self):
        response = self.client.post(self.public_url, self.valid_data())

        material_request = MissingMaterialRequest.objects.get()
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse("catalog:course_detail", args=[self.offering.id]),
        )
        self.assertEqual(material_request.status, MissingMaterialRequest.Status.OPEN)
        self.assertEqual(material_request.offering, self.offering)
        self.assertEqual(material_request.email, "student-private@example.com")

    def test_empty_request_is_rejected(self):
        response = self.client.post(
            self.public_url,
            {
                "offering": self.offering.id,
                "request_type": StudyDocument.ContentType.SUMMARY,
                "description": "   ",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "اكتب وصفاً مختصراً")
        self.assertFalse(MissingMaterialRequest.objects.exists())

    def test_invalid_offering_preselection_returns_404(self):
        response = self.client.get(self.public_url, {"offering": "not-an-id"})

        self.assertEqual(response.status_code, 404)

    def test_public_request_form_is_csrf_protected(self):
        csrf_client = Client(enforce_csrf_checks=True)

        response = csrf_client.post(self.public_url, self.valid_data())

        self.assertEqual(response.status_code, 403)
        self.assertFalse(MissingMaterialRequest.objects.exists())

    def test_anonymous_visitor_cannot_manage_requests(self):
        response = self.client.get(self.management_url)

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])

    def test_in_scope_moderator_can_manage_request(self):
        material_request = self.make_request()
        self.client.force_login(self.moderator)

        response = self.client.post(
            self.management_url,
            self.moderation_data(
                material_request,
                MissingMaterialRequest.Status.IN_PROGRESS,
                notes="تواصلنا مع مساهم ضمن المادة.",
            ),
        )

        material_request.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            material_request.status,
            MissingMaterialRequest.Status.IN_PROGRESS,
        )
        self.assertEqual(
            material_request.supervisor_notes,
            "تواصلنا مع مساهم ضمن المادة.",
        )

    def test_out_of_scope_moderator_is_forbidden(self):
        material_request = self.make_request()
        self.client.force_login(self.outside_moderator)

        listing = self.client.get(self.management_url)
        update = self.client.post(
            self.management_url,
            self.moderation_data(
                material_request,
                MissingMaterialRequest.Status.REJECTED,
            ),
        )

        self.assertNotContains(listing, material_request.description)
        self.assertEqual(update.status_code, 403)
        material_request.refresh_from_db()
        self.assertEqual(material_request.status, MissingMaterialRequest.Status.OPEN)

    def test_every_status_can_be_saved_by_in_scope_moderator(self):
        self.client.force_login(self.moderator)

        for status, _label in MissingMaterialRequest.Status.choices:
            with self.subTest(status=status):
                material_request = self.make_request(description=f"طلب {status}")
                response = self.client.post(
                    self.management_url,
                    self.moderation_data(material_request, status),
                )
                self.assertEqual(response.status_code, 302)
                material_request.refresh_from_db()
                self.assertEqual(material_request.status, status)

    def test_fulfilled_request_can_link_matching_published_document(self):
        material_request = self.make_request()
        document = published_documents().get(offering=self.offering)
        self.client.force_login(self.moderator)

        response = self.client.post(
            self.management_url,
            self.moderation_data(
                material_request,
                MissingMaterialRequest.Status.FULFILLED,
                document=document.id,
            ),
        )

        self.assertEqual(response.status_code, 302)
        material_request.refresh_from_db()
        self.assertEqual(material_request.fulfilled_document, document)

    def test_student_email_is_not_rendered_on_public_pages(self):
        private_email = "never-public@example.com"
        self.make_request(email=private_email)

        public_urls = [
            reverse("pages:home"),
            reverse("pages:browse"),
            reverse("catalog:request_material"),
            reverse("catalog:course_detail", args=[self.offering.id]),
        ]
        for url in public_urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, private_email)

    @override_settings(MATERIAL_REQUEST_RATE_LIMIT=2)
    def test_rate_limit_blocks_repeated_valid_submissions(self):
        first = self.client.post(
            self.public_url,
            self.valid_data(description="الطلب الأول"),
        )
        second = self.client.post(
            self.public_url,
            self.valid_data(description="الطلب الثاني"),
        )
        blocked = self.client.post(
            self.public_url,
            self.valid_data(description="الطلب الثالث"),
        )

        self.assertEqual(first.status_code, 302)
        self.assertEqual(second.status_code, 302)
        self.assertEqual(blocked.status_code, 429)
        self.assertContains(blocked, "حد الإرسال المؤقت", status_code=429)
        self.assertEqual(MissingMaterialRequest.objects.count(), 2)

    def test_contributor_requires_explicit_permission_and_scope(self):
        material_request = self.make_request()
        self.client.force_login(self.contributor)
        denied = self.client.get(self.management_url)
        self.assertEqual(denied.status_code, 403)

        permission = Permission.objects.get(
            codename="manage_missing_material_requests",
        )
        self.contributor.user_permissions.add(permission)
        ModeratorScope.objects.create(
            user=self.contributor,
            course=self.offering.course,
        )
        self.contributor = get_user_model().objects.get(pk=self.contributor.pk)
        self.client.force_login(self.contributor)

        allowed = self.client.post(
            self.management_url,
            self.moderation_data(
                material_request,
                MissingMaterialRequest.Status.DUPLICATE,
            ),
        )
        self.assertEqual(allowed.status_code, 302)
        material_request.refresh_from_db()
        self.assertEqual(
            material_request.status,
            MissingMaterialRequest.Status.DUPLICATE,
        )

    def test_request_links_exist_on_home_browse_and_course_pages(self):
        pages = [
            self.client.get(reverse("pages:home")),
            self.client.get(reverse("pages:browse")),
            self.client.get(reverse("catalog:course_detail", args=[self.offering.id])),
        ]

        for response in pages:
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "اطلب ملفاً")
