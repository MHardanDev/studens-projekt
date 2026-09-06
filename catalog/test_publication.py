import hashlib
import shutil
import tempfile
from urllib.parse import unquote

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import ContributorScope, ModeratorScope, User
from pages.preferences import DATA_SAVER_COOKIE, LAST_LOCATION_COOKIE

from .models import Faculty, StudyDocument


class PublicDocumentTests(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.settings_override = override_settings(MEDIA_ROOT=self.media_root)
        self.settings_override.enable()
        call_command("seed_demo_catalog")
        self.faculty = Faculty.objects.get(name="كلية الاقتصاد")
        self.offering = self.faculty.programs.get().course_offerings.first()
        self.contributor = get_user_model().objects.create_user(
            username="publisher-contributor",
            password="strong-test-password",
            role=User.Role.TRUSTED_CONTRIBUTOR,
        )
        self.moderator = get_user_model().objects.create_user(
            username="publisher-moderator",
            password="strong-test-password",
            role=User.Role.FACULTY_MODERATOR,
        )
        ContributorScope.objects.create(user=self.contributor, faculty=self.faculty)
        ModeratorScope.objects.create(user=self.moderator, faculty=self.faculty)
        self.pdf_body = b"%PDF-1.4\npublic document bytes\n%%EOF"

    def tearDown(self):
        self.settings_override.disable()
        shutil.rmtree(self.media_root, ignore_errors=True)

    def make_document(
        self,
        title,
        status=StudyDocument.Status.PENDING_REVIEW,
        pdf_body=None,
    ):
        body = self.pdf_body if pdf_body is None else pdf_body
        upload = SimpleUploadedFile(
            f"{title}.pdf",
            body,
            content_type="application/pdf",
        )
        return StudyDocument.objects.create(
            offering=self.offering,
            title=title,
            description="وصف النسخة المنشورة.",
            content_type=StudyDocument.ContentType.SUMMARY,
            status=status,
            scan_status=StudyDocument.ScanStatus.CLEAN,
            contributor=self.contributor,
            contributor_name=self.contributor.username,
            uploaded_file=upload,
            original_filename="public-document.pdf",
            file_size=len(body),
            uploaded_content_type="application/pdf",
        )

    def publish_document(
        self,
        title="ملف منشور فعلي",
        pdf_body=None,
        page_count=None,
    ):
        document = self.make_document(title, pdf_body=pdf_body)
        document.approve(self.moderator, page_count=page_count)
        document.refresh_from_db()
        return document

    def response_body(self, response):
        return b"".join(response.streaming_content)

    def test_approved_clean_document_is_public(self):
        document = self.publish_document()

        response = self.client.get(document.get_absolute_url())

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, document.title)
        self.assertContains(response, self.offering.program.faculty.university.name)

    def test_pending_and_rejected_documents_are_not_public(self):
        pending = self.make_document("ملف خاص بانتظار المراجعة")
        rejected = self.make_document(
            "ملف خاص مرفوض",
            status=StudyDocument.Status.REJECTED,
        )

        for document in [pending, rejected]:
            with self.subTest(status=document.status):
                detail = self.client.get(
                    reverse("catalog:document_detail", args=[document.id]),
                )
                download = self.client.get(
                    reverse("catalog:download_document", args=[document.id]),
                )
                self.assertEqual(detail.status_code, 404)
                self.assertEqual(download.status_code, 404)

        browse = self.client.get(reverse("pages:browse"))
        self.assertNotContains(browse, pending.title)
        self.assertNotContains(browse, rejected.title)

    def test_approved_document_download_streams_pdf(self):
        document = self.publish_document()

        response = self.client.get(
            reverse("catalog:download_document", args=[document.id]),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertEqual(response["Content-Length"], str(len(self.pdf_body)))
        self.assertEqual(response["Accept-Ranges"], "bytes")
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertTrue(response["ETag"].startswith('"'))
        self.assertEqual(self.response_body(response), self.pdf_body)

    def test_head_returns_download_metadata_without_body(self):
        document = self.publish_document()

        response = self.client.head(
            reverse("catalog:download_document", args=[document.id]),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Length"], str(len(self.pdf_body)))
        self.assertEqual(response["Accept-Ranges"], "bytes")
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertIn("ETag", response)
        self.assertEqual(response.content, b"")

    def test_valid_range_returns_partial_content(self):
        document = self.publish_document()

        response = self.client.get(
            reverse("catalog:download_document", args=[document.id]),
            HTTP_RANGE="bytes=0-7",
        )

        self.assertEqual(response.status_code, 206)
        self.assertEqual(response["Content-Range"], f"bytes 0-7/{len(self.pdf_body)}")
        self.assertEqual(response["Content-Length"], "8")
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertEqual(self.response_body(response), self.pdf_body[:8])

    def test_if_range_controls_partial_response(self):
        document = self.publish_document()
        url = reverse("catalog:download_document", args=[document.id])
        head = self.client.head(url)

        matching = self.client.get(
            url,
            HTTP_RANGE="bytes=0-3",
            HTTP_IF_RANGE=head["ETag"],
        )
        stale = self.client.get(
            url,
            HTTP_RANGE="bytes=0-3",
            HTTP_IF_RANGE='"stale-validator"',
        )

        self.assertEqual(matching.status_code, 206)
        self.assertEqual(stale.status_code, 200)
        self.assertEqual(self.response_body(matching), self.pdf_body[:4])
        self.assertEqual(self.response_body(stale), self.pdf_body)

    def test_invalid_range_returns_416(self):
        document = self.publish_document()

        response = self.client.get(
            reverse("catalog:download_document", args=[document.id]),
            HTTP_RANGE="bytes=999-1000",
        )

        self.assertEqual(response.status_code, 416)
        self.assertEqual(response["Content-Range"], f"bytes */{len(self.pdf_body)}")
        self.assertEqual(response["Accept-Ranges"], "bytes")
        self.assertEqual(response["Cache-Control"], "no-store")

    def test_realistic_range_reassembly_and_sha256_match(self):
        chunk_data = b"%PDF-1.4\n%realistic Syrian student lecture notes payload\n"
        tail = b"\n%%EOF"
        padding = b"A" * (16384 - len(chunk_data) - len(tail))
        realistic_pdf = chunk_data + padding + tail
        self.assertEqual(len(realistic_pdf), 16384)
        original_sha256 = hashlib.sha256(realistic_pdf).hexdigest()

        document = self.publish_document(
            title="ملف واقعي لإعادة تجميع النطاقات",
            pdf_body=realistic_pdf,
            page_count=6,
        )
        url = reverse("catalog:download_document", args=[document.id])

        ranges = [
            ("bytes=0-4999", 0, 4999, 5000),
            ("bytes=5000-9999", 5000, 9999, 5000),
            ("bytes=10000-16383", 10000, 16383, 6384),
        ]

        reassembled_parts = []
        for range_header, start, end, expected_len in ranges:
            response = self.client.get(url, HTTP_RANGE=range_header)
            self.assertEqual(response.status_code, 206)
            self.assertEqual(response["Cache-Control"], "no-store")
            self.assertEqual(response["Content-Range"], f"bytes {start}-{end}/16384")
            self.assertEqual(response["Content-Length"], str(expected_len))
            part = self.response_body(response)
            self.assertEqual(len(part), expected_len)
            reassembled_parts.append(part)

        reassembled_body = b"".join(reassembled_parts)
        self.assertEqual(len(reassembled_body), 16384)
        self.assertEqual(
            hashlib.sha256(reassembled_body).hexdigest(),
            original_sha256,
        )
        self.assertEqual(reassembled_body, realistic_pdf)

    def test_document_detail_displays_version_size_and_page_count(self):
        doc_with_pages = self.publish_document(
            title="ملف منشور ذو صفحات",
            page_count=14,
        )
        response = self.client.get(doc_with_pages.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "رقم الإصدار")
        self.assertContains(response, "1")
        self.assertContains(response, "عدد الصفحات")
        self.assertContains(response, "14")
        self.assertContains(response, "حجم الملف")

        doc_without_pages = self.publish_document(
            title="ملف منشور بدون صفحات",
            page_count=None,
        )
        response_no_pages = self.client.get(doc_without_pages.get_absolute_url())
        self.assertEqual(response_no_pages.status_code, 200)
        self.assertContains(response_no_pages, "رقم الإصدار")
        self.assertContains(response_no_pages, "حجم الملف")
        self.assertNotContains(response_no_pages, "عدد الصفحات")

    def test_document_page_has_download_and_report_actions(self):
        document = self.publish_document()

        response = self.client.get(document.get_absolute_url())

        self.assertContains(
            response,
            reverse("catalog:download_document", args=[document.id]),
        )
        self.assertContains(
            response,
            reverse("catalog:report_document", args=[document.id]),
        )
        self.assertContains(response, "بلاغ عن الملف")

    def test_data_saver_preference_uses_non_sensitive_cookie(self):
        document = self.publish_document()
        response = self.client.post(
            reverse("pages:set_data_saver"),
            {"enabled": "1", "next": document.get_absolute_url()},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.cookies[DATA_SAVER_COOKIE].value, "1")
        self.assertTrue(response.cookies[DATA_SAVER_COOKIE]["httponly"])

        detail = self.client.get(document.get_absolute_url())
        self.assertContains(detail, "وضع توفير البيانات مفعّل")

    def test_last_document_and_search_are_remembered_as_internal_paths(self):
        document = self.publish_document()
        detail = self.client.get(document.get_absolute_url())
        self.assertEqual(
            detail.cookies[LAST_LOCATION_COOKIE].value,
            document.get_absolute_url(),
        )

        search = self.client.get(reverse("pages:home"), {"q": "محاسبة"})
        remembered = unquote(search.cookies[LAST_LOCATION_COOKIE].value)
        self.assertTrue(remembered.startswith(reverse("pages:home")))
        self.assertIn("q=محاسبة", remembered)
        self.assertNotIn(self.contributor.username, remembered)

        home = self.client.get(reverse("pages:home"))
        self.assertContains(home, "تابع من آخر مكان")
