import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import ContributorScope, User

from .models import Faculty, StudyDocument


class UploadSecurityTests(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.settings_override = override_settings(MEDIA_ROOT=self.media_root)
        self.settings_override.enable()
        call_command("seed_demo_catalog")
        self.faculty = Faculty.objects.get(name="كلية الاقتصاد")
        self.offering = self.faculty.programs.get().course_offerings.first()
        self.user = get_user_model().objects.create_user(
            username="uploader",
            email="uploader@example.test",
            password="strong-test-password",
            role=User.Role.TRUSTED_CONTRIBUTOR,
        )
        self.upload_url = reverse("catalog:upload_document")

    def tearDown(self):
        self.settings_override.disable()
        shutil.rmtree(self.media_root, ignore_errors=True)

    def pdf_upload(self, name="safe.pdf", body=b"%PDF-1.4\n%test"):
        return SimpleUploadedFile(
            name,
            body,
            content_type="application/pdf",
        )

    def valid_payload(self, upload=None):
        return {
            "offering": self.offering.pk,
            "title": "ملف مرفوع للاختبار",
            "description": "وصف اختباري",
            "content_type": StudyDocument.ContentType.SUMMARY,
            "content_owner_name": "المساهم التجريبي",
            "content_source": "ملاحظات أصلية أعدها المساهم للاختبار.",
            "rights_basis": StudyDocument.RightsBasis.CONTRIBUTOR_ORIGINAL,
            "license_name": "",
            "permission_evidence": "",
            "rights_contact": "rights-private@example.test",
            "rights_declaration": "on",
            "academic_year": "2026/2027",
            "publication_year": "2026",
            "upload": upload or self.pdf_upload(),
        }

    def test_anonymous_user_cannot_open_upload_page(self):
        response = self.client.get(self.upload_url)

        self.assertEqual(response.status_code, 302)

    def test_student_cannot_upload(self):
        student = get_user_model().objects.create_user(
            username="student-only",
            password="strong-test-password",
        )
        self.client.force_login(student)

        response = self.client.get(self.upload_url)

        self.assertEqual(response.status_code, 403)

    def test_trusted_contributor_without_scope_cannot_upload(self):
        self.client.force_login(self.user)

        response = self.client.get(self.upload_url)

        self.assertEqual(response.status_code, 403)

    def test_trusted_contributor_with_scope_creates_pending_document(self):
        ContributorScope.objects.create(user=self.user, faculty=self.faculty)
        self.client.force_login(self.user)

        response = self.client.post(self.upload_url, self.valid_payload())
        document = StudyDocument.objects.get(title="ملف مرفوع للاختبار")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(document.status, StudyDocument.Status.UPLOADED_PENDING_SCAN)
        self.assertEqual(document.scan_status, StudyDocument.ScanStatus.PENDING)
        self.assertEqual(document.contributor, self.user)
        self.assertNotEqual(document.uploaded_file.name, document.original_filename)
        self.assertTrue(document.uploaded_file.name.startswith("study-documents/"))
        self.assertFalse(document.can_be_public)

    def test_rejects_non_pdf_extension(self):
        ContributorScope.objects.create(user=self.user, faculty=self.faculty)
        self.client.force_login(self.user)
        upload = self.pdf_upload(name="notes.txt")

        response = self.client.post(self.upload_url, self.valid_payload(upload))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "يسمح برفع ملفات PDF فقط")
        exists = StudyDocument.objects.filter(title="ملف مرفوع للاختبار").exists()
        self.assertFalse(exists)

    @override_settings(MAX_UPLOAD_SIZE=8)
    def test_rejects_file_larger_than_configured_limit(self):
        ContributorScope.objects.create(user=self.user, faculty=self.faculty)
        self.client.force_login(self.user)
        upload = self.pdf_upload(body=b"%PDF-1.4\nlarge")

        response = self.client.post(self.upload_url, self.valid_payload(upload))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "حجم الملف يتجاوز الحد المسموح")
        exists = StudyDocument.objects.filter(title="ملف مرفوع للاختبار").exists()
        self.assertFalse(exists)

    def test_rejects_file_without_pdf_magic_bytes(self):
        ContributorScope.objects.create(user=self.user, faculty=self.faculty)
        self.client.force_login(self.user)
        upload = self.pdf_upload(body=b"not a pdf")

        response = self.client.post(self.upload_url, self.valid_payload(upload))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "محتوى الملف لا يبدأ بتوقيع PDF الصحيح")

    def test_path_traversal_filename_is_stored_with_safe_internal_name(self):
        ContributorScope.objects.create(user=self.user, faculty=self.faculty)
        self.client.force_login(self.user)
        upload = self.pdf_upload(name="../evil.pdf")

        response = self.client.post(self.upload_url, self.valid_payload(upload))
        document = StudyDocument.objects.get(title="ملف مرفوع للاختبار")

        self.assertEqual(response.status_code, 302)
        self.assertTrue(document.has_safe_internal_file_name)
        self.assertTrue(document.uploaded_file.name.startswith("study-documents/"))
        self.assertNotIn("..", document.uploaded_file.name)
        self.assertNotIn(self.user.username, document.uploaded_file.name)

    def test_uploaded_document_does_not_appear_on_public_browse(self):
        ContributorScope.objects.create(user=self.user, faculty=self.faculty)
        self.client.force_login(self.user)
        self.client.post(self.upload_url, self.valid_payload())

        response = self.client.get("/ar/browse/")

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "ملف مرفوع للاختبار")
