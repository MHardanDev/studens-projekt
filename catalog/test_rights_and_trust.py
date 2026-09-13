import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import ContributorScope, ModeratorScope, User

from .models import DocumentReport, Faculty, StudyDocument
from .rights import RIGHTS_DECLARATION_TEXT


class RightsAndTrustTests(TestCase):
    def setUp(self):
        cache.clear()
        self.media_root = tempfile.mkdtemp()
        self.settings_override = override_settings(MEDIA_ROOT=self.media_root)
        self.settings_override.enable()
        call_command("seed_demo_catalog")
        self.faculty = Faculty.objects.get(name="كلية الاقتصاد")
        self.offerings = list(
            self.faculty.programs.get().course_offerings.select_related("course")[:2],
        )
        self.offering = self.offerings[0]
        self.other_offering = self.offerings[1]
        self.contributor = get_user_model().objects.create_user(
            username="rights-contributor",
            password="strong-test-password",
            role=User.Role.TRUSTED_CONTRIBUTOR,
        )
        self.moderator = get_user_model().objects.create_user(
            username="rights-moderator",
            password="strong-test-password",
            role=User.Role.FACULTY_MODERATOR,
        )
        self.outside_moderator = get_user_model().objects.create_user(
            username="outside-rights-moderator",
            password="strong-test-password",
            role=User.Role.FACULTY_MODERATOR,
        )
        self.student = get_user_model().objects.create_user(
            username="rights-student",
            password="strong-test-password",
        )
        ContributorScope.objects.create(user=self.contributor, faculty=self.faculty)
        ModeratorScope.objects.create(
            user=self.moderator,
            course=self.offering.course,
        )
        ModeratorScope.objects.create(
            user=self.outside_moderator,
            course=self.other_offering.course,
        )
        self.private_evidence = "إذن مكتوب محفوظ لدى المشرف فقط."
        self.private_contact = "rights-owner-private@example.test"
        self.pdf_body = b"%PDF-1.4\nrights test\n%%EOF"

    def tearDown(self):
        self.settings_override.disable()
        shutil.rmtree(self.media_root, ignore_errors=True)

    def pdf_upload(self):
        return SimpleUploadedFile(
            "rights.pdf",
            self.pdf_body,
            content_type="application/pdf",
        )

    def upload_data(self, *, declaration="on", evidence=None):
        return {
            "offering": self.offering.pk,
            "title": "ملف حقوق تجريبي",
            "description": "وصف أصلي للاختبار.",
            "content_type": StudyDocument.ContentType.LECTURE,
            "content_owner_name": "صاحب المحتوى التجريبي",
            "content_source": "ملف أرسله صاحبه بإذن صريح للاختبار.",
            "rights_basis": StudyDocument.RightsBasis.OWNER_PERMISSION,
            "license_name": "",
            "permission_evidence": evidence or self.private_evidence,
            "rights_contact": self.private_contact,
            "rights_declaration": declaration,
            "academic_year": "2026/2027",
            "publication_year": "2026",
            "upload": self.pdf_upload(),
        }

    def complete_document(self, *, offering=None, status=None):
        return StudyDocument.objects.create(
            offering=offering or self.offering,
            title="وثيقة مكتملة الحقوق",
            description="وصف تجريبي.",
            content_type=StudyDocument.ContentType.LECTURE,
            status=status or StudyDocument.Status.PENDING_REVIEW,
            scan_status=StudyDocument.ScanStatus.CLEAN,
            contributor=self.contributor,
            contributor_name=self.contributor.username,
            content_owner_name="صاحب المحتوى التجريبي",
            content_source="مصدر أصلي موثق للاختبار.",
            rights_basis=StudyDocument.RightsBasis.OWNER_PERMISSION,
            permission_evidence=self.private_evidence,
            rights_contact=self.private_contact,
            rights_declaration_text=RIGHTS_DECLARATION_TEXT,
            rights_declared_at=timezone.now(),
            rights_declared_by=self.contributor,
            uploaded_file=self.pdf_upload(),
            original_filename="rights.pdf",
            file_size=len(self.pdf_body),
            uploaded_content_type="application/pdf",
        )

    def publish_document(self):
        document = self.complete_document()
        document.approve(self.moderator)
        document.refresh_from_db()
        return document

    def test_upload_requires_and_records_rights_declaration(self):
        self.client.force_login(self.contributor)
        missing_data = self.upload_data(declaration="")

        missing = self.client.post(reverse("catalog:upload_document"), missing_data)

        self.assertEqual(missing.status_code, 200)
        self.assertIn("rights_declaration", missing.context["form"].errors)
        self.assertFalse(
            StudyDocument.objects.filter(title="ملف حقوق تجريبي").exists(),
        )

        accepted = self.client.post(
            reverse("catalog:upload_document"),
            self.upload_data(),
        )
        document = StudyDocument.objects.get(title="ملف حقوق تجريبي")
        self.assertEqual(accepted.status_code, 302)
        self.assertEqual(document.rights_declaration_text, RIGHTS_DECLARATION_TEXT)
        self.assertEqual(document.rights_declared_by, self.contributor)
        self.assertIsNotNone(document.rights_declared_at)

    def test_permission_basis_requires_private_evidence(self):
        self.client.force_login(self.contributor)
        data = self.upload_data()
        data["permission_evidence"] = ""

        response = self.client.post(reverse("catalog:upload_document"), data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "الإذن الصريح")
        self.assertFalse(
            StudyDocument.objects.filter(title="ملف حقوق تجريبي").exists(),
        )

    def test_incomplete_legacy_rights_cannot_be_approved(self):
        document = StudyDocument.objects.create(
            offering=self.offering,
            title="ملف قديم بلا حقوق مختلقة",
            status=StudyDocument.Status.PENDING_REVIEW,
            scan_status=StudyDocument.ScanStatus.CLEAN,
            contributor=self.contributor,
        )

        with self.assertRaisesMessage(ValidationError, "بيانات الحقوق غير مكتملة"):
            document.approve(self.moderator)

        document.refresh_from_db()
        self.assertEqual(document.content_owner_name, "")
        self.assertEqual(document.rights_basis, "")
        self.assertIsNone(document.published_version)

    def test_private_rights_data_is_visible_only_in_scoped_moderation(self):
        document = self.complete_document()
        self.client.force_login(self.moderator)

        review = self.client.get(reverse("catalog:moderation_documents"))

        self.assertContains(review, self.private_evidence)
        self.assertContains(review, self.private_contact)

        self.client.force_login(self.outside_moderator)
        outside = self.client.get(reverse("catalog:moderation_documents"))
        self.assertNotContains(outside, self.private_evidence)
        self.assertNotContains(outside, self.private_contact)

        self.client.force_login(self.moderator)
        document.approve(self.moderator)
        document.refresh_from_db()
        public = self.client.get(document.get_absolute_url())
        self.assertNotContains(public, self.private_evidence)
        self.assertNotContains(public, self.private_contact)
        self.assertNotContains(public, RIGHTS_DECLARATION_TEXT)
        self.assertEqual(
            document.published_version.permission_evidence,
            self.private_evidence,
        )

    def test_copyright_report_is_csrf_protected_and_contact_stays_private(self):
        document = self.publish_document()
        url = reverse("catalog:report_document", args=[document.pk])
        payload = {
            "report_type": DocumentReport.ReportType.COPYRIGHT,
            "body": "أنا صاحب المحتوى وأعترض على نشره.",
            "reporter_contact": "reporter-private@example.test",
        }
        csrf_client = Client(enforce_csrf_checks=True)

        denied = csrf_client.post(url, payload)
        accepted = self.client.post(url, payload)

        self.assertEqual(denied.status_code, 403)
        self.assertEqual(accepted.status_code, 302)
        report = DocumentReport.objects.get(document=document)
        self.assertEqual(report.report_type, DocumentReport.ReportType.COPYRIGHT)

        public = self.client.get(document.get_absolute_url())
        self.assertNotContains(public, report.reporter_contact)

        self.client.force_login(self.moderator)
        moderation = self.client.get(
            reverse("catalog:moderation_document_reports"),
        )
        self.assertContains(moderation, report.reporter_contact)

    @override_settings(DOCUMENT_REPORT_RATE_LIMIT=2)
    def test_report_rate_limit_blocks_repeated_valid_submissions(self):
        document = self.publish_document()
        url = reverse("catalog:report_document", args=[document.pk])

        responses = [
            self.client.post(
                url,
                {
                    "report_type": DocumentReport.ReportType.OTHER,
                    "body": f"بلاغ تجريبي رقم {number}",
                    "reporter_contact": "",
                },
            )
            for number in range(1, 4)
        ]

        self.assertEqual(
            [response.status_code for response in responses],
            [302, 302, 429],
        )
        self.assertEqual(DocumentReport.objects.filter(document=document).count(), 2)
        self.assertContains(responses[-1], "حد إرسال البلاغات", status_code=429)

    def test_report_management_enforces_role_and_scope(self):
        document = self.publish_document()
        report = DocumentReport.objects.create(
            document=document,
            report_type=DocumentReport.ReportType.COPYRIGHT,
            body="بلاغ نطاق.",
        )
        management_url = reverse("catalog:moderation_document_reports")

        anonymous = self.client.get(management_url)
        self.assertEqual(anonymous.status_code, 302)

        self.client.force_login(self.student)
        self.assertEqual(self.client.get(management_url).status_code, 403)

        self.client.force_login(self.contributor)
        self.assertEqual(self.client.get(management_url).status_code, 403)

        self.client.force_login(self.outside_moderator)
        listing = self.client.get(management_url)
        update = self.client.post(
            management_url,
            {"report_id": report.pk, "action": "resolve", "moderator_notes": ""},
        )
        self.assertNotContains(listing, report.body)
        self.assertEqual(update.status_code, 403)

    def test_in_scope_moderator_can_mark_report_as_reviewing(self):
        document = self.publish_document()
        report = DocumentReport.objects.create(
            document=document,
            report_type=DocumentReport.ReportType.COPYRIGHT,
            body="بلاغ سيبدأ المشرف مراجعته.",
        )
        self.client.force_login(self.moderator)

        response = self.client.post(
            reverse("catalog:moderation_document_reports"),
            {
                "report_id": report.pk,
                "action": "review",
                "moderator_notes": "بدأ التحقق من مصدر الملف.",
            },
        )

        report.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(report.status, DocumentReport.Status.REVIEWING)
        self.assertEqual(report.reviewed_by, self.moderator)

    def test_blocked_document_rejects_get_head_and_range(self):
        document = self.publish_document()
        report = DocumentReport.objects.create(
            document=document,
            report_type=DocumentReport.ReportType.COPYRIGHT,
            body="طلب إزالة بعد مراجعة الحقوق.",
            reporter_contact="owner-private@example.test",
        )
        self.client.force_login(self.moderator)

        result = self.client.post(
            reverse("catalog:moderation_document_reports"),
            {
                "report_id": report.pk,
                "action": "block",
                "moderator_notes": "تعذر إثبات الإذن، حجب حتى حسم النزاع.",
            },
        )

        self.assertEqual(result.status_code, 302)
        document.refresh_from_db()
        report.refresh_from_db()
        self.assertEqual(document.status, StudyDocument.Status.ARCHIVED)
        self.assertEqual(report.status, DocumentReport.Status.RESOLVED)
        self.assertEqual(report.reviewed_by, self.moderator)

        download_url = reverse("catalog:download_document", args=[document.pk])
        responses = [
            self.client.get(download_url),
            self.client.head(download_url),
            self.client.get(download_url, HTTP_RANGE="bytes=0-3"),
        ]
        self.assertEqual(
            [response.status_code for response in responses],
            [404, 404, 404],
        )
        self.assertEqual(self.client.get(document.get_absolute_url()).status_code, 404)

    def test_trust_pages_work_for_all_language_prefixes_and_are_linked(self):
        slugs = [
            "about/",
            "content-guidelines/",
            "privacy/",
            "contact-reporting/",
        ]
        home = self.client.get("/ar/")
        for slug in slugs:
            self.assertContains(home, f"/ar/{slug}")

        for prefix, direction in [("ar", "rtl"), ("en", "ltr"), ("de", "ltr")]:
            for slug in slugs:
                with self.subTest(prefix=prefix, route=slug):
                    path = f"/{prefix}/{slug}"
                    response = self.client.get(path)
                    self.assertEqual(response.status_code, 200)
                    self.assertContains(response, f'lang="{prefix}"')
                    self.assertContains(response, f'dir="{direction}"')
