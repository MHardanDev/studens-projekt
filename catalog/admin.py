from django.contrib import admin
from django.core.exceptions import ValidationError

from .models import (
    AcademicYearLevel,
    Course,
    CourseOffering,
    DocumentReport,
    DocumentVersion,
    Faculty,
    Program,
    StudyDocument,
    Term,
    University,
)


@admin.register(University)
class UniversityAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "is_demo", "updated_at"]
    list_filter = ["is_demo"]
    search_fields = ["name", "slug"]
    ordering = ["name"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ["name", "university", "slug", "is_demo", "updated_at"]
    list_filter = ["university", "is_demo"]
    search_fields = ["name", "slug", "university__name"]
    ordering = ["university__name", "name"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ["name", "faculty", "university_name", "is_demo", "updated_at"]
    list_filter = ["faculty__university", "faculty", "is_demo"]
    search_fields = ["name", "slug", "faculty__name", "faculty__university__name"]
    ordering = ["faculty__university__name", "faculty__name", "name"]
    prepopulated_fields = {"slug": ("name",)}

    @admin.display(description="الجامعة")
    def university_name(self, obj):
        return obj.faculty.university.name


@admin.register(AcademicYearLevel)
class AcademicYearLevelAdmin(admin.ModelAdmin):
    list_display = ["name", "order", "program", "faculty_name", "is_demo"]
    list_filter = ["program__faculty__university", "program__faculty", "program"]
    search_fields = ["name", "program__name", "program__faculty__name"]
    ordering = ["program__name", "order"]

    @admin.display(description="الكلية")
    def faculty_name(self, obj):
        return obj.program.faculty.name


@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    list_display = ["name", "order", "year_level", "program_name", "is_demo"]
    list_filter = [
        "year_level__program__faculty__university",
        "year_level__program__faculty",
        "year_level__program",
        "year_level",
    ]
    search_fields = ["name", "year_level__name", "year_level__program__name"]
    ordering = ["year_level__program__name", "year_level__order", "order"]

    @admin.display(description="البرنامج")
    def program_name(self, obj):
        return obj.year_level.program.name


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "is_demo", "updated_at"]
    list_filter = ["is_demo"]
    search_fields = ["name", "code"]
    ordering = ["name", "code"]


@admin.register(CourseOffering)
class CourseOfferingAdmin(admin.ModelAdmin):
    list_display = [
        "course",
        "program",
        "year_level",
        "term",
        "academic_year",
        "is_demo",
    ]
    list_filter = [
        "program__faculty__university",
        "program__faculty",
        "program",
        "year_level",
        "term",
        "academic_year",
        "is_demo",
    ]
    search_fields = [
        "course__name",
        "course__code",
        "program__name",
        "program__faculty__name",
        "program__faculty__university__name",
    ]
    ordering = [
        "program__faculty__university__name",
        "program__faculty__name",
        "program__name",
        "year_level__order",
        "term__order",
        "course__name",
    ]


@admin.register(StudyDocument)
class StudyDocumentAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "course_name",
        "content_type",
        "status",
        "scan_status",
        "contributor_name",
        "contributor",
        "reviewed_by",
        "published_version",
        "file_size",
        "academic_year",
        "is_demo",
    ]
    list_filter = [
        "offering__program__faculty__university",
        "offering__program__faculty",
        "offering__program",
        "offering__year_level",
        "offering__term",
        "offering__course",
        "status",
        "scan_status",
        "content_type",
        "contributor",
        "academic_year",
        "is_demo",
    ]
    search_fields = [
        "title",
        "description",
        "contributor_name",
        "offering__course__name",
        "offering__course__code",
        "offering__program__name",
    ]
    readonly_fields = [
        "uploaded_file",
        "original_filename",
        "file_size",
        "uploaded_content_type",
        "scan_notes",
        "reviewed_by",
        "reviewed_at",
        "rejection_reason",
        "published_version",
    ]
    actions = ["move_clean_uploads_to_review"]
    ordering = [
        "offering__program__faculty__university__name",
        "offering__program__faculty__name",
        "offering__program__name",
        "offering__year_level__order",
        "offering__term__order",
        "offering__course__name",
        "title",
    ]

    @admin.display(description="المادة")
    def course_name(self, obj):
        return obj.offering.course.name

    @admin.action(description="إرسال الملفات النظيفة إلى انتظار المراجعة")
    def move_clean_uploads_to_review(self, request, queryset):
        moved = 0
        for document in queryset:
            try:
                document.move_to_pending_review()
            except ValidationError:
                continue
            moved += 1
        self.message_user(request, f"تم إرسال {moved} ملف/ملفات إلى المراجعة.")


@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "version_number",
        "document",
        "course_name",
        "file_size",
        "page_count",
        "uploaded_by",
        "reviewed_by",
        "reviewed_at",
        "checksum_sha256",
    ]
    list_filter = [
        "offering__program__faculty__university",
        "offering__program__faculty",
        "offering__program",
        "offering__course",
        "content_type",
        "uploaded_by",
        "reviewed_by",
        "reviewed_at",
    ]
    search_fields = [
        "title",
        "description",
        "checksum_sha256",
        "original_filename",
        "document__title",
        "offering__course__name",
    ]
    readonly_fields = [
        "document",
        "version_number",
        "title",
        "description",
        "offering",
        "content_type",
        "internal_file_name",
        "original_filename",
        "file_size",
        "page_count",
        "checksum_sha256",
        "uploaded_by",
        "reviewed_by",
        "reviewed_at",
    ]
    ordering = ["-reviewed_at", "document", "-version_number"]

    @admin.display(description="المادة")
    def course_name(self, obj):
        return obj.offering.course.name


@admin.register(DocumentReport)
class DocumentReportAdmin(admin.ModelAdmin):
    list_display = [
        "document",
        "report_type",
        "status",
        "reporter",
        "reporter_contact",
        "created_at",
    ]
    list_filter = [
        "status",
        "report_type",
        "document__offering__program__faculty__university",
        "document__offering__program__faculty",
        "document__offering__course",
        "created_at",
    ]
    search_fields = [
        "body",
        "reporter_contact",
        "reporter__username",
        "document__title",
        "document__offering__course__name",
    ]
    ordering = ["-created_at"]
