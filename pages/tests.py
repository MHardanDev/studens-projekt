from django.core.management import call_command
from django.test import TestCase


class PublicPageTests(TestCase):
    def test_home_page_is_arabic_rtl(self):
        response = self.client.get("/ar/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'lang="ar"')
        self.assertContains(response, 'dir="rtl"')
        self.assertContains(response, "ابحث عن مادة أو ملف بدون تسجيل")
        self.assertContains(response, "تصفح الكليات والمواد")

    def test_browse_page_lists_demo_courses(self):
        response = self.client.get("/ar/browse/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "لا توجد بيانات دراسية بعد")

    def test_language_prefixes_are_available_for_later_translation(self):
        for prefix, direction in [("en", "ltr"), ("de", "ltr")]:
            with self.subTest(prefix=prefix):
                response = self.client.get(f"/{prefix}/")
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, f'lang="{prefix}"')
                self.assertContains(response, f'dir="{direction}"')

    def test_language_switcher_links_are_rendered(self):
        response = self.client.get("/ar/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="/ar/"')
        self.assertContains(response, 'href="/en/"')
        self.assertContains(response, 'href="/de/"')

    def test_home_search_returns_course_result(self):
        call_command("seed_demo_catalog")

        response = self.client.get("/ar/", {"q": "محاسبة"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="محاسبة"')
        self.assertContains(response, "مبادئ المحاسبة")

    def test_home_search_empty_state_when_no_results(self):
        call_command("seed_demo_catalog")

        response = self.client.get("/ar/", {"q": "لاشيء"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="لاشيء"')
        self.assertContains(response, "لا توجد نتائج مطابقة")

    def test_browse_search_returns_document_result(self):
        call_command("seed_demo_catalog")

        response = self.client.get("/ar/browse/", {"q": "حلول"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="حلول"')
        self.assertContains(response, "حلول تمارين رياضيات مالية")

    def test_health_endpoint_is_small_json(self):
        response = self.client.get("/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
