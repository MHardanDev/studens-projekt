from django.core.management import call_command
from django.test import TestCase

from .models import (
    AcademicYearLevel,
    Course,
    CourseOffering,
    Faculty,
    Program,
    StudyDocument,
    Term,
    University,
    make_slug,
)


class CatalogModelTests(TestCase):
    def test_create_flexible_study_structure(self):
        university = University.objects.create(
            name="جامعة تجريبية",
            slug=make_slug("جامعة تجريبية"),
        )
        faculty = Faculty.objects.create(
            university=university,
            name="كلية تجريبية",
            slug=make_slug("كلية تجريبية"),
        )
        program = Program.objects.create(
            faculty=faculty,
            name="برنامج تجريبي",
            slug=make_slug("برنامج تجريبي"),
        )
        level = AcademicYearLevel.objects.create(
            program=program,
            name="سنة اختيارية",
            order=1,
        )
        term = Term.objects.create(year_level=level, name="فصل صيفي", order=1)
        course = Course.objects.create(name="مادة تجريبية", code="DEMO-1")
        offering = CourseOffering.objects.create(
            course=course,
            program=program,
            year_level=level,
            term=term,
            academic_year="2026/2027",
        )
        document = StudyDocument.objects.create(
            offering=offering,
            title="ملف تجريبي",
            content_type=StudyDocument.ContentType.SUMMARY,
            status=StudyDocument.Status.DRAFT,
            contributor_name="مساهم مؤقت",
        )

        self.assertEqual(document.course, course)
        self.assertEqual(document.offering.program.faculty.university, university)

    def test_program_is_not_limited_to_four_years(self):
        university = University.objects.create(
            name="جامعة مرنة",
            slug=make_slug("جامعة مرنة"),
        )
        faculty = Faculty.objects.create(
            university=university,
            name="كلية مرنة",
            slug=make_slug("كلية مرنة"),
        )
        program = Program.objects.create(
            faculty=faculty,
            name="برنامج خمس سنوات",
            slug=make_slug("برنامج خمس سنوات"),
        )

        for order in range(1, 6):
            AcademicYearLevel.objects.create(
                program=program,
                name=f"السنة {order}",
                order=order,
            )

        self.assertEqual(program.year_levels.count(), 5)


class DemoSeedTests(TestCase):
    def test_seed_creates_tishreen_economics_demo_data(self):
        call_command("seed_demo_catalog")
        call_command("seed_demo_catalog")

        self.assertEqual(University.objects.filter(name="جامعة تشرين").count(), 1)
        self.assertEqual(Faculty.objects.filter(name="كلية الاقتصاد").count(), 1)
        self.assertEqual(Program.objects.filter(name="اقتصاد").count(), 1)
        self.assertEqual(AcademicYearLevel.objects.count(), 4)
        self.assertEqual(Term.objects.count(), 8)
        self.assertEqual(Course.objects.count(), 3)
        self.assertEqual(StudyDocument.objects.count(), 3)

    def test_browse_page_shows_seeded_courses(self):
        call_command("seed_demo_catalog")

        response = self.client.get("/ar/browse/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "جامعة تشرين")
        self.assertContains(response, "كلية الاقتصاد")
        self.assertContains(response, "مبادئ الاقتصاد الجزئي")
        self.assertContains(response, "مبادئ المحاسبة")
        self.assertContains(response, "رياضيات مالية")

    def test_browse_page_empty_state_without_seed(self):
        response = self.client.get("/ar/browse/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "لا توجد بيانات دراسية بعد")
