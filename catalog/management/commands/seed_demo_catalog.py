from django.core.management.base import BaseCommand

from catalog.models import (
    AcademicYearLevel,
    Course,
    CourseOffering,
    DocumentVersion,
    Faculty,
    Program,
    StudyDocument,
    Term,
    University,
    make_slug,
)


class Command(BaseCommand):
    help = "Create idempotent Arabic demo catalog data for local development."

    def handle(self, *args, **options):
        university, _ = University.objects.update_or_create(
            slug=make_slug("جامعة تشرين"),
            defaults={"name": "جامعة تشرين", "is_demo": True},
        )
        faculty, _ = Faculty.objects.update_or_create(
            university=university,
            slug=make_slug("كلية الاقتصاد"),
            defaults={"name": "كلية الاقتصاد", "is_demo": True},
        )
        program, _ = Program.objects.update_or_create(
            faculty=faculty,
            slug=make_slug("اقتصاد"),
            defaults={"name": "اقتصاد", "is_demo": True},
        )

        levels = []
        level_names = [
            "السنة الأولى",
            "السنة الثانية",
            "السنة الثالثة",
            "السنة الرابعة",
        ]
        for order, name in enumerate(level_names, start=1):
            level, _ = AcademicYearLevel.objects.update_or_create(
                program=program,
                order=order,
                defaults={"name": name, "is_demo": True},
            )
            levels.append(level)
            for term_order, term_name in enumerate(
                ["الفصل الأول", "الفصل الثاني"],
                start=1,
            ):
                Term.objects.update_or_create(
                    year_level=level,
                    order=term_order,
                    defaults={"name": term_name, "is_demo": True},
                )

        first_level = levels[0]
        first_term = first_level.terms.get(order=1)
        second_term = first_level.terms.get(order=2)
        demo_courses = [
            ("مبادئ الاقتصاد الجزئي", "ECO-101", first_term),
            ("مبادئ المحاسبة", "ACC-101", first_term),
            ("رياضيات مالية", "MTH-102", second_term),
        ]

        offerings = []
        for name, code, term in demo_courses:
            course, _ = Course.objects.update_or_create(
                code=code,
                defaults={"name": name, "is_demo": True},
            )
            offering, _ = CourseOffering.objects.update_or_create(
                course=course,
                program=program,
                year_level=term.year_level,
                term=term,
                academic_year="2026/2027",
                defaults={"is_demo": True},
            )
            offerings.append(offering)

        documents = [
            (
                offerings[0],
                "ملخص مبادئ الاقتصاد الجزئي",
                StudyDocument.ContentType.SUMMARY,
            ),
            (
                offerings[1],
                "أسئلة تدريبية في مبادئ المحاسبة",
                StudyDocument.ContentType.PAST_EXAM,
            ),
            (
                offerings[2],
                "حلول تمارين رياضيات مالية",
                StudyDocument.ContentType.SOLUTION,
            ),
        ]
        for offering, title, content_type in documents:
            document, _ = StudyDocument.objects.update_or_create(
                offering=offering,
                title=title,
                defaults={
                    "description": "بيانات تجريبية بدون ملف PDF حقيقي.",
                    "content_type": content_type,
                    "status": StudyDocument.Status.APPROVED,
                    "scan_status": StudyDocument.ScanStatus.CLEAN,
                    "contributor_name": "مساهم تجريبي",
                    "publication_year": 2026,
                    "academic_year": "2026/2027",
                    "is_demo": True,
                },
            )
            version, _ = DocumentVersion.objects.update_or_create(
                document=document,
                version_number=1,
                defaults={
                    "title": document.title,
                    "description": document.description,
                    "offering": document.offering,
                    "content_type": document.content_type,
                    "internal_file_name": "",
                    "original_filename": "",
                    "file_size": document.file_size,
                    "checksum_sha256": "",
                    "uploaded_by": document.contributor,
                    "reviewed_by": document.reviewed_by,
                    "reviewed_at": document.reviewed_at,
                },
            )
            if document.published_version_id != version.id:
                document.published_version = version
                document.save(update_fields=["published_version", "updated_at"])

        self.stdout.write(self.style.SUCCESS("Demo catalog data is ready."))
