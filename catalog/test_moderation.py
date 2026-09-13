import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import ContributorScope, ModeratorScope, User

from .models import DocumentReport, DocumentVersion, Faculty, StudyDocument
from .rights import RIGHTS_DECLARATION_TEXT


class ModerationWorkflowTests(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.settings_override = override_settings(MEDIA_ROOT=self.media_root)
        self.settings_override.enable()
        call_command("seed_demo_catalog")
        self.faculty = Faculty.objects.get(name="كلية الاقتصاد")
        self.offering = self.faculty.programs.get().course_offerings.first()
        self.contributor = get_user_model().objects.create_user(
            username="contributor",
            password="strong-test-password",
            role=User.Role.TRUSTED_CONTRIBUTOR,
        )
        self.moderator = get_user_model().objects.create_user(
            username="moderator",
            password="strong-test-password",
            role=User.Role.FACULTY_MODERATOR,
        )
        self.student = get_user_model().objects.create_user(
            username="student",
            password="strong-test-password",
        )
        ContributorScope.objects.create(user=self.contributor, faculty=self.faculty)
        ModeratorScope.objects.create(user=self.moderator, faculty=self.faculty)
        self.moderation_url = reverse("catalog:moderation_documents")

    def tearDown(self):
        self.settings_override.disable()
        shutil.rmtree(self.media_root, ignore_errors=True)

    def pdf_file(self, name="review.pdf", body=b"%PDF-1.4\nreview"):
        return SimpleUploadedFile(name, body, content_type="application/pdf")

    def document(self, *, scan_status=StudyDocument.ScanStatus.CLEAN, status=None):
        return StudyDocument.objects.create(
            offering=self.offering,
            title="ملف يحتاج مراجعة",
            content_type=StudyDocument.ContentType.SUMMARY,
            status=status or StudyDocument.Status.UPLOADED_PENDING_SCAN,
            scan_status=scan_status,
            contributor=self.contributor,
            contributor_name=self.contributor.username,
            content_owner_name="صاحب محتوى تجريبي",
            content_source="ملاحظات أصلية للاختبار.",
            rights_basis=StudyDocument.RightsBasis.CONTRIBUTOR_ORIGINAL,
            rights_declaration_text=RIGHTS_DECLARATION_TEXT,
            rights_declared_at=timezone.now(),
            rights_declared_by=self.contributor,
            uploaded_file=self.pdf_file(),
            original_filename="review.pdf",
            file_size=16,
            uploaded_content_type="application/pdf",
        )

    def test_pending_scan_file_cannot_be_sent_to_review(self):
        document = self.document(scan_status=StudyDocument.ScanStatus.PENDING)

        with self.assertRaises(ValidationError):
            document.move_to_pending_review()

    def test_failed_or_infected_scan_cannot_be_sent_to_review(self):
        for scan_status in [
            StudyDocument.ScanStatus.FAILED,
            StudyDocument.ScanStatus.INFECTED,
        ]:
            with self.subTest(scan_status=scan_status):
                document = self.document(scan_status=scan_status)

                with self.assertRaises(ValidationError):
                    document.move_to_pending_review()

    def test_clean_scan_can_move_to_pending_review(self):
        document = self.document(scan_status=StudyDocument.ScanStatus.CLEAN)

        document.move_to_pending_review()

        document.refresh_from_db()
        self.assertEqual(document.status, StudyDocument.Status.PENDING_REVIEW)

    def test_moderator_in_scope_can_approve(self):
        document = self.document(status=StudyDocument.Status.PENDING_REVIEW)
        self.client.force_login(self.moderator)

        response = self.client.post(
            self.moderation_url,
            {"document_id": document.id, "action": "approve"},
        )

        document.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(document.status, StudyDocument.Status.APPROVED)
        self.assertEqual(document.reviewed_by, self.moderator)
        self.assertIsNotNone(document.published_version)
        self.assertEqual(document.versions.count(), 1)

    def test_moderator_outside_scope_cannot_approve(self):
        other_moderator = get_user_model().objects.create_user(
            username="other-mod",
            password="strong-test-password",
            role=User.Role.FACULTY_MODERATOR,
        )
        document = self.document(status=StudyDocument.Status.PENDING_REVIEW)
        self.client.force_login(other_moderator)

        response = self.client.post(
            self.moderation_url,
            {"document_id": document.id, "action": "approve"},
        )

        document.refresh_from_db()
        self.assertEqual(response.status_code, 403)
        self.assertEqual(document.status, StudyDocument.Status.PENDING_REVIEW)

    def test_trusted_contributor_cannot_approve_own_file(self):
        document = self.document(status=StudyDocument.Status.PENDING_REVIEW)

        with self.assertRaises(ValidationError):
            document.approve(self.contributor)

    def test_student_and_anonymous_user_cannot_enter_moderation(self):
        anonymous_response = self.client.get(self.moderation_url)
        self.assertEqual(anonymous_response.status_code, 302)

        self.client.force_login(self.student)
        student_response = self.client.get(self.moderation_url)
        self.assertEqual(student_response.status_code, 403)

    def test_rejection_saves_reason(self):
        document = self.document(status=StudyDocument.Status.PENDING_REVIEW)
        self.client.force_login(self.moderator)

        response = self.client.post(
            self.moderation_url,
            {
                "document_id": document.id,
                "action": "reject",
                "rejection_reason": "الملف غير واضح.",
            },
        )

        document.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(document.status, StudyDocument.Status.REJECTED)
        self.assertEqual(document.rejection_reason, "الملف غير واضح.")

    def test_new_upload_does_not_delete_old_published_version(self):
        published = self.document(status=StudyDocument.Status.PENDING_REVIEW)
        version = published.approve(self.moderator)

        newer_upload = self.document(status=StudyDocument.Status.UPLOADED_PENDING_SCAN)
        newer_upload.title = "نسخة أحدث بانتظار الفحص"
        newer_upload.save(update_fields=["title"])

        published.refresh_from_db()
        self.assertEqual(published.published_version, version)
        self.assertTrue(DocumentVersion.objects.filter(pk=version.pk).exists())
        self.assertEqual(published.status, StudyDocument.Status.APPROVED)
        self.assertEqual(
            newer_upload.status,
            StudyDocument.Status.UPLOADED_PENDING_SCAN,
        )

    def test_report_for_published_file_can_be_created(self):
        document = self.document(status=StudyDocument.Status.PENDING_REVIEW)
        document.approve(self.moderator)
        url = reverse("catalog:report_document", args=[document.id])

        response = self.client.post(
            url,
            {
                "report_type": DocumentReport.ReportType.BROKEN_FILE,
                "body": "لا يفتح الملف عند التجربة.",
                "reporter_contact": "",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(DocumentReport.objects.filter(document=document).exists())
