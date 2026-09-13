import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import ContributorScope, ModeratorScope, User

from .models import DocumentReport, Faculty, StudyDocument
from .rights import RIGHTS_DECLARATION_TEXT


class SeoTests(TestCase):
    def setUp(self):
        call_command("seed_demo_catalog")
        self.documents = list(
            StudyDocument.objects.filter(
                status=StudyDocument.Status.APPROVED,
            ).order_by("pk"),
        )
        self.offering = self.documents[0].offering

    def test_public_pages_have_meta_canonical_open_graph_and_schema(self):
        public_paths = [
            reverse("pages:home"),
            reverse("pages:browse"),
            reverse("catalog:course_detail", args=[self.offering.pk]),
            reverse("catalog:document_detail", args=[self.documents[0].pk]),
            reverse("pages:about"),
            reverse("pages:content_guidelines"),
            reverse("pages:privacy"),
            reverse("pages:contact_reporting"),
        ]

        for path in public_paths:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, '<meta name="description"')
                self.assertContains(
                    response,
                    f'<link rel="canonical" href="http://testserver{path}">',
                    html=True,
                )
                self.assertContains(response, '<meta property="og:title"')
                self.assertContains(response, 'type="application/ld+json"')
                self.assertNotIn("X-Robots-Tag", response)

    def test_search_is_noindex_and_canonical_drops_query(self):
        home_path = reverse("pages:home")
        response = self.client.get(home_path, {"q": "محاسبة"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            '<meta name="robots" content="noindex, nofollow">',
        )
        self.assertEqual(response["X-Robots-Tag"], "noindex, nofollow")
        self.assertContains(
            response,
            f'<link rel="canonical" href="http://testserver{home_path}">',
            html=True,
        )
        self.assertNotContains(response, "application/ld+json")

    def test_sitemap_contains_only_public_documents_and_useful_courses(self):
        public_document = self.documents[0]
        archived_document = self.documents[1]
        rejected_document = self.documents[2]
        archived_document.status = StudyDocument.Status.ARCHIVED
        archived_document.save(update_fields=["status", "updated_at"])
        rejected_document.status = StudyDocument.Status.REJECTED
        rejected_document.save(update_fields=["status", "updated_at"])
        pending_document = StudyDocument.objects.create(
            offering=self.offering,
            title="ملف خاص غير منشور",
            status=StudyDocument.Status.UPLOADED_PENDING_SCAN,
            scan_status=StudyDocument.ScanStatus.PENDING,
        )

        response = self.client.get(reverse("sitemap"))
        body = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/xml")
        self.assertIn(
            reverse("catalog:document_detail", args=[public_document.pk]),
            body,
        )
        self.assertNotIn(
            reverse("catalog:document_detail", args=[archived_document.pk]),
            body,
        )
        self.assertNotIn(
            reverse("catalog:document_detail", args=[rejected_document.pk]),
            body,
        )
        self.assertNotIn(
            reverse("catalog:document_detail", args=[pending_document.pk]),
            body,
        )
        self.assertIn(
            reverse("catalog:course_detail", args=[public_document.offering_id]),
            body,
        )
        self.assertIn("http://testserver/en/", body)
        self.assertIn("http://testserver/de/", body)
        self.assertNotIn("/accounts/", body)
        self.assertNotIn("/moderation/", body)
        self.assertNotIn("/contribute/", body)
        self.assertNotIn("/download/", body)
        self.assertNotIn("/report/", body)

    def test_robots_blocks_private_routes(self):
        response = self.client.get(reverse("robots"))
        body = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertIn("Disallow: /*/accounts/", body)
        self.assertIn("Disallow: /*/contribute/", body)
        self.assertIn("Disallow: /*/moderation/", body)
        self.assertIn("Disallow: /*/requests/", body)
        self.assertIn("Disallow: /*/documents/*/download/", body)
        self.assertIn("Disallow: /*/documents/*/report/", body)
        self.assertIn("Sitemap: http://testserver/sitemap.xml", body)

    def test_private_html_page_and_health_send_noindex(self):
        login = self.client.get(reverse("accounts:login"))
        health = self.client.get(reverse("health"))

        self.assertContains(login, '<meta name="robots" content="noindex, nofollow">')
        self.assertEqual(login["X-Robots-Tag"], "noindex, nofollow")
        self.assertEqual(health["X-Robots-Tag"], "noindex, nofollow")

    def test_public_pages_load_no_external_tracking(self):
        response = self.client.get(reverse("pages:home"))
        body = response.content.decode().lower()

        self.assertNotIn("google-analytics", body)
        self.assertNotIn("googletagmanager", body)
        self.assertNotIn("doubleclick", body)


class DownloadMetricsTests(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.settings_override = override_settings(MEDIA_ROOT=self.media_root)
        self.settings_override.enable()
        call_command("seed_demo_catalog")
        self.faculty = Faculty.objects.get(name="كلية الاقتصاد")
        self.offering = self.faculty.programs.get().course_offerings.first()
        self.contributor = get_user_model().objects.create_user(
            username="metrics-contributor",
            password="strong-test-password",
            role=User.Role.TRUSTED_CONTRIBUTOR,
        )
        self.moderator = get_user_model().objects.create_user(
            username="metrics-moderator",
            password="strong-test-password",
            role=User.Role.FACULTY_MODERATOR,
        )
        ContributorScope.objects.create(user=self.contributor, faculty=self.faculty)
        ModeratorScope.objects.create(user=self.moderator, faculty=self.faculty)
        self.pdf_body = b"%PDF-1.4\nmetrics test bytes\n%%EOF"
        self.document = self.publish_document()

    def tearDown(self):
        self.settings_override.disable()
        shutil.rmtree(self.media_root, ignore_errors=True)

    def publish_document(self):
        upload = SimpleUploadedFile(
            "metrics.pdf",
            self.pdf_body,
            content_type="application/pdf",
        )
        document = StudyDocument.objects.create(
            offering=self.offering,
            title="ملف مؤشرات منشور",
            description="وصف ملف المؤشرات.",
            content_type=StudyDocument.ContentType.SUMMARY,
            status=StudyDocument.Status.PENDING_REVIEW,
            scan_status=StudyDocument.ScanStatus.CLEAN,
            contributor=self.contributor,
            contributor_name=self.contributor.username,
            content_owner_name="مساهم الاختبار",
            content_source="ملاحظات اختبار أصلية.",
            rights_basis=StudyDocument.RightsBasis.CONTRIBUTOR_ORIGINAL,
            rights_declaration_text=RIGHTS_DECLARATION_TEXT,
            rights_declared_at=timezone.now(),
            rights_declared_by=self.contributor,
            uploaded_file=upload,
            original_filename="metrics.pdf",
            file_size=len(self.pdf_body),
            uploaded_content_type="application/pdf",
        )
        document.approve(self.moderator)
        document.refresh_from_db()
        return document

    def consume_stream(self, response):
        if response.streaming:
            return b"".join(response.streaming_content)
        return response.content

    def download_count(self):
        self.document.published_version.refresh_from_db()
        return self.document.published_version.full_download_count

    def test_only_full_get_without_range_increments_download_count(self):
        url = reverse("catalog:download_document", args=[self.document.pk])

        head = self.client.head(url)
        self.assertEqual(head.status_code, 200)
        self.assertEqual(self.download_count(), 0)

        partial = self.client.get(url, HTTP_RANGE="bytes=0-4")
        self.assertEqual(partial.status_code, 206)
        self.consume_stream(partial)
        self.assertEqual(self.download_count(), 0)

        stale_if_range = self.client.get(
            url,
            HTTP_RANGE="bytes=0-4",
            HTTP_IF_RANGE='"stale"',
        )
        self.assertEqual(stale_if_range.status_code, 200)
        self.consume_stream(stale_if_range)
        self.assertEqual(self.download_count(), 0)

        full = self.client.get(url)
        self.assertEqual(full.status_code, 200)
        self.assertEqual(self.consume_stream(full), self.pdf_body)
        self.assertEqual(self.download_count(), 1)

    def test_metrics_are_private_scoped_and_do_not_show_contact(self):
        self.document.published_version.full_download_count = 4
        self.document.published_version.save(update_fields=["full_download_count"])
        DocumentReport.objects.create(
            document=self.document,
            report_type=DocumentReport.ReportType.BROKEN_FILE,
            body="بلاغ للاختبار",
            reporter_contact="private@example.test",
        )
        url = reverse("catalog:moderation_metrics")

        visitor = self.client.get(url)
        self.assertEqual(visitor.status_code, 302)

        student = get_user_model().objects.create_user(
            username="metrics-student",
            password="strong-test-password",
            role=User.Role.STUDENT,
        )
        self.client.force_login(student)
        self.assertEqual(self.client.get(url).status_code, 403)

        self.client.force_login(self.contributor)
        self.assertEqual(self.client.get(url).status_code, 403)

        unscoped_moderator = get_user_model().objects.create_user(
            username="unscoped-metrics-moderator",
            password="strong-test-password",
            role=User.Role.FACULTY_MODERATOR,
        )
        self.client.force_login(unscoped_moderator)
        unscoped = self.client.get(url)
        self.assertEqual(unscoped.status_code, 200)
        self.assertNotContains(unscoped, self.document.title)

        self.client.force_login(self.moderator)
        scoped = self.client.get(url)
        self.assertEqual(scoped.status_code, 200)
        self.assertContains(scoped, self.document.title)
        self.assertContains(scoped, "4")
        self.assertContains(scoped, "1")
        self.assertNotContains(scoped, "private@example.test")
        self.assertEqual(scoped["X-Robots-Tag"], "noindex, nofollow")

    def test_site_admin_with_scope_can_view_metrics(self):
        admin_user = get_user_model().objects.create_user(
            username="metrics-site-admin",
            password="strong-test-password",
            role=User.Role.SITE_ADMIN,
        )
        ModeratorScope.objects.create(user=admin_user, faculty=self.faculty)
        self.client.force_login(admin_user)

        response = self.client.get(reverse("catalog:moderation_metrics"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.document.title)
