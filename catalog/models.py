from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Max
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


def study_document_upload_path(instance, filename):
    return f"study-documents/{uuid4().hex}.pdf"


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class University(TimestampedModel):
    name = models.CharField(max_length=160, unique=True)
    slug = models.SlugField(max_length=180, unique=True, allow_unicode=True)
    is_demo = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]
        verbose_name = "جامعة"
        verbose_name_plural = "الجامعات"

    def __str__(self):
        return self.name


class Faculty(TimestampedModel):
    university = models.ForeignKey(
        University,
        on_delete=models.CASCADE,
        related_name="faculties",
    )
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, allow_unicode=True)
    is_demo = models.BooleanField(default=False)

    class Meta:
        ordering = ["university__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["university", "slug"],
                name="unique_faculty_slug_per_university",
            ),
            models.UniqueConstraint(
                fields=["university", "name"],
                name="unique_faculty_name_per_university",
            ),
        ]
        verbose_name = "كلية"
        verbose_name_plural = "الكليات"

    def __str__(self):
        return f"{self.name} - {self.university.name}"


class Program(TimestampedModel):
    faculty = models.ForeignKey(
        Faculty,
        on_delete=models.CASCADE,
        related_name="programs",
    )
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, allow_unicode=True)
    is_demo = models.BooleanField(default=False)

    class Meta:
        ordering = ["faculty__university__name", "faculty__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["faculty", "slug"],
                name="unique_program_slug_per_faculty",
            ),
            models.UniqueConstraint(
                fields=["faculty", "name"],
                name="unique_program_name_per_faculty",
            ),
        ]
        verbose_name = "برنامج"
        verbose_name_plural = "البرامج"

    def __str__(self):
        return f"{self.name} - {self.faculty.name}"


class AcademicYearLevel(TimestampedModel):
    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name="year_levels",
    )
    name = models.CharField(max_length=80)
    order = models.PositiveSmallIntegerField()
    is_demo = models.BooleanField(default=False)

    class Meta:
        ordering = ["program__name", "order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["program", "order"],
                name="unique_year_level_order_per_program",
            ),
            models.UniqueConstraint(
                fields=["program", "name"],
                name="unique_year_level_name_per_program",
            ),
        ]
        verbose_name = "سنة دراسية"
        verbose_name_plural = "السنوات الدراسية"

    def __str__(self):
        return f"{self.name} - {self.program.name}"


class Term(TimestampedModel):
    year_level = models.ForeignKey(
        AcademicYearLevel,
        on_delete=models.CASCADE,
        related_name="terms",
    )
    name = models.CharField(max_length=80)
    order = models.PositiveSmallIntegerField()
    is_demo = models.BooleanField(default=False)

    class Meta:
        ordering = ["year_level__order", "order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["year_level", "order"],
                name="unique_term_order_per_year_level",
            ),
            models.UniqueConstraint(
                fields=["year_level", "name"],
                name="unique_term_name_per_year_level",
            ),
        ]
        verbose_name = "فصل"
        verbose_name_plural = "الفصول"

    def __str__(self):
        return f"{self.name} - {self.year_level.name}"


class Course(TimestampedModel):
    name = models.CharField(max_length=160)
    code = models.CharField(max_length=40, blank=True)
    is_demo = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "code"],
                name="unique_course_name_code",
            ),
        ]
        verbose_name = "مادة"
        verbose_name_plural = "المواد"

    def __str__(self):
        if self.code:
            return f"{self.name} ({self.code})"
        return self.name


class CourseOffering(TimestampedModel):
    course = models.ForeignKey(
        Course,
        on_delete=models.PROTECT,
        related_name="offerings",
    )
    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name="course_offerings",
    )
    year_level = models.ForeignKey(
        AcademicYearLevel,
        on_delete=models.CASCADE,
        related_name="course_offerings",
    )
    term = models.ForeignKey(
        Term,
        on_delete=models.CASCADE,
        related_name="course_offerings",
    )
    academic_year = models.CharField(max_length=20, blank=True)
    is_demo = models.BooleanField(default=False)

    class Meta:
        ordering = [
            "program__faculty__university__name",
            "program__faculty__name",
            "program__name",
            "year_level__order",
            "term__order",
            "course__name",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "course",
                    "program",
                    "year_level",
                    "term",
                    "academic_year",
                ],
                name="unique_course_offering_per_context",
            ),
        ]
        verbose_name = "طرح مادة"
        verbose_name_plural = "طروحات المواد"

    def __str__(self):
        return (
            f"{self.course.name} - {self.program.name} - "
            f"{self.year_level.name} - {self.term.name}"
        )


class StudyDocument(TimestampedModel):
    class ContentType(models.TextChoices):
        SUMMARY = "summary", "ملخص"
        LECTURE = "lecture", "محاضرة"
        PAST_EXAM = "past_exam", "أسئلة دورة"
        SOLUTION = "solution", "حل"
        BOOK = "book", "كتاب"
        PRACTICAL = "practical", "عملي"
        OTHER = "other", "غير ذلك"

    class Status(models.TextChoices):
        DRAFT = "draft", "مسودة"
        UPLOADED_PENDING_SCAN = "uploaded_pending_scan", "مرفوع بانتظار الفحص"
        PENDING_REVIEW = "pending_review", "بانتظار المراجعة"
        APPROVED = "approved", "معتمد"
        REJECTED = "rejected", "مرفوض"
        ARCHIVED = "archived", "مؤرشف"

    class ScanStatus(models.TextChoices):
        PENDING = "pending", "بانتظار الفحص"
        CLEAN = "clean", "سليم"
        INFECTED = "infected", "مصاب"
        FAILED = "failed", "فشل الفحص"

    offering = models.ForeignKey(
        CourseOffering,
        on_delete=models.PROTECT,
        related_name="documents",
    )
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    content_type = models.CharField(
        max_length=30,
        choices=ContentType.choices,
        default=ContentType.SUMMARY,
    )
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    contributor_name = models.CharField(max_length=120, blank=True)
    contributor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="study_documents",
        blank=True,
        null=True,
    )
    publication_year = models.PositiveSmallIntegerField(blank=True, null=True)
    academic_year = models.CharField(max_length=20, blank=True)
    uploaded_file = models.FileField(
        upload_to=study_document_upload_path,
        blank=True,
        null=True,
    )
    original_filename = models.CharField(max_length=255, blank=True)
    file_size = models.PositiveIntegerField(blank=True, null=True)
    uploaded_content_type = models.CharField(max_length=100, blank=True)
    scan_status = models.CharField(
        max_length=20,
        choices=ScanStatus.choices,
        default=ScanStatus.PENDING,
        db_index=True,
    )
    scan_notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="reviewed_study_documents",
        blank=True,
        null=True,
    )
    reviewed_at = models.DateTimeField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True)
    published_version = models.ForeignKey(
        "catalog.DocumentVersion",
        on_delete=models.SET_NULL,
        related_name="current_for_documents",
        blank=True,
        null=True,
    )
    is_demo = models.BooleanField(default=False)

    class Meta:
        ordering = ["offering__course__name", "title"]
        indexes = [
            models.Index(fields=["status", "content_type"]),
            models.Index(fields=["status", "scan_status"]),
            models.Index(fields=["academic_year"]),
        ]
        verbose_name = "ملف دراسي"
        verbose_name_plural = "الملفات الدراسية"

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()
        if (
            self.status == self.Status.PENDING_REVIEW
            and self.scan_status != self.ScanStatus.CLEAN
        ):
            raise ValidationError(
                {"status": "لا ينتقل الملف إلى المراجعة قبل نجاح الفحص."},
            )
        if self.status == self.Status.APPROVED:
            if self.scan_status != self.ScanStatus.CLEAN:
                raise ValidationError(
                    {"status": "لا يعتمد الملف قبل نجاح الفحص."},
                )
            if not self.published_version_id and not self.is_demo:
                raise ValidationError(
                    {"status": "اعتماد الملف يحتاج إنشاء نسخة منشورة عبر المراجعة."},
                )

    @property
    def course(self):
        return self.offering.course

    def get_absolute_url(self):
        return reverse("catalog:document_detail", args=[self.pk])

    @property
    def is_publishable_after_scan(self):
        return self.scan_status == self.ScanStatus.CLEAN

    @property
    def can_be_public(self):
        return (
            self.status == self.Status.APPROVED
            and self.scan_status == self.ScanStatus.CLEAN
            and self.published_version_id is not None
        )

    @property
    def has_safe_internal_file_name(self):
        if not self.uploaded_file:
            return True
        stored_name = self.uploaded_file.name
        return Path(stored_name).name == stored_name.split("/")[-1]

    def move_to_pending_review(self):
        if self.scan_status != self.ScanStatus.CLEAN:
            raise ValidationError("لا يمكن إرسال الملف للمراجعة قبل فحص clean.")
        if self.status not in {
            self.Status.UPLOADED_PENDING_SCAN,
            self.Status.REJECTED,
        }:
            raise ValidationError("حالة الملف الحالية لا تسمح بإرساله للمراجعة.")
        self.status = self.Status.PENDING_REVIEW
        self.save(update_fields=["status", "updated_at"])
        return self

    def approve(self, reviewer, page_count=None):
        from accounts.permissions import user_can_review_document

        if self.status != self.Status.PENDING_REVIEW:
            raise ValidationError("لا يعتمد إلا ملف بانتظار المراجعة.")
        if self.scan_status != self.ScanStatus.CLEAN:
            raise ValidationError("لا يعتمد الملف قبل نجاح الفحص.")
        if not user_can_review_document(reviewer, self):
            raise ValidationError("لا يملك هذا الحساب صلاحية اعتماد الملف.")

        version = self.create_version_snapshot(reviewer, page_count=page_count)
        self.status = self.Status.APPROVED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.rejection_reason = ""
        self.published_version = version
        self.save(
            update_fields=[
                "status",
                "reviewed_by",
                "reviewed_at",
                "rejection_reason",
                "published_version",
                "updated_at",
            ],
        )
        return version

    def reject(self, reviewer, reason):
        from accounts.permissions import user_can_review_document

        if self.status != self.Status.PENDING_REVIEW:
            raise ValidationError("لا يرفض إلا ملف بانتظار المراجعة.")
        if not reason or not reason.strip():
            raise ValidationError("سبب الرفض مطلوب.")
        if not user_can_review_document(reviewer, self):
            raise ValidationError("لا يملك هذا الحساب صلاحية رفض الملف.")

        self.status = self.Status.REJECTED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.rejection_reason = reason.strip()
        self.save(
            update_fields=[
                "status",
                "reviewed_by",
                "reviewed_at",
                "rejection_reason",
                "updated_at",
            ],
        )
        return self

    def create_version_snapshot(self, reviewer, page_count=None):
        next_number = (self.versions.aggregate(Max("version_number"))[
            "version_number__max"
        ] or 0) + 1
        return self.versions.create(
            version_number=next_number,
            title=self.title,
            description=self.description,
            offering=self.offering,
            content_type=self.content_type,
            internal_file_name=self.uploaded_file.name if self.uploaded_file else "",
            original_filename=self.original_filename,
            file_size=self.file_size,
            page_count=page_count,
            checksum_sha256=self.calculate_sha256(),
            uploaded_by=self.contributor,
            reviewed_by=reviewer,
            reviewed_at=timezone.now(),
        )

    def calculate_sha256(self):
        if not self.uploaded_file:
            return ""
        import hashlib

        hasher = hashlib.sha256()
        try:
            self.uploaded_file.open("rb")
            for chunk in self.uploaded_file.chunks():
                hasher.update(chunk)
        except OSError:
            return ""
        finally:
            try:
                self.uploaded_file.close()
            except OSError:
                pass
        return hasher.hexdigest()


class DocumentVersion(TimestampedModel):
    document = models.ForeignKey(
        StudyDocument,
        on_delete=models.CASCADE,
        related_name="versions",
    )
    version_number = models.PositiveIntegerField()
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    offering = models.ForeignKey(
        CourseOffering,
        on_delete=models.PROTECT,
        related_name="document_versions",
    )
    content_type = models.CharField(
        max_length=30,
        choices=StudyDocument.ContentType.choices,
        default=StudyDocument.ContentType.SUMMARY,
    )
    internal_file_name = models.CharField(max_length=255, blank=True)
    original_filename = models.CharField(max_length=255, blank=True)
    file_size = models.PositiveIntegerField(blank=True, null=True)
    page_count = models.PositiveIntegerField(blank=True, null=True)
    checksum_sha256 = models.CharField(max_length=64, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="uploaded_document_versions",
        blank=True,
        null=True,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="approved_document_versions",
        blank=True,
        null=True,
    )
    reviewed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["document", "-version_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "version_number"],
                name="unique_document_version_number",
            ),
        ]
        verbose_name = "نسخة ملف"
        verbose_name_plural = "نسخ الملفات"

    def __str__(self):
        return f"{self.title} v{self.version_number}"


class DocumentReport(TimestampedModel):
    class ReportType(models.TextChoices):
        SCIENTIFIC_ERROR = "scientific_error", "خطأ علمي"
        BROKEN_FILE = "broken_file", "ملف لا يفتح"
        COPYRIGHT = "copyright", "حقوق نشر"
        INAPPROPRIATE = "inappropriate", "محتوى غير مناسب"
        OTHER = "other", "غير ذلك"

    class Status(models.TextChoices):
        OPEN = "open", "مفتوح"
        REVIEWING = "reviewing", "قيد المراجعة"
        RESOLVED = "resolved", "محلول"
        REJECTED = "rejected", "مرفوض"

    document = models.ForeignKey(
        StudyDocument,
        on_delete=models.CASCADE,
        related_name="reports",
    )
    report_type = models.CharField(
        max_length=32,
        choices=ReportType.choices,
        default=ReportType.OTHER,
    )
    body = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
    )
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="document_reports",
        blank=True,
        null=True,
    )
    reporter_contact = models.CharField(max_length=254, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "بلاغ ملف"
        verbose_name_plural = "بلاغات الملفات"

    def clean(self):
        super().clean()
        if self.document_id and not self.document.can_be_public:
            raise ValidationError("البلاغات متاحة للملفات المنشورة فقط.")

    def __str__(self):
        return f"{self.get_report_type_display()} - {self.document.title}"


class MissingMaterialRequest(TimestampedModel):
    class Status(models.TextChoices):
        OPEN = "open", "مفتوح"
        IN_PROGRESS = "in_progress", "قيد المتابعة"
        FULFILLED = "fulfilled", "تمت تلبيته"
        REJECTED = "rejected", "مرفوض"
        DUPLICATE = "duplicate", "مكرر"

    offering = models.ForeignKey(
        CourseOffering,
        on_delete=models.PROTECT,
        related_name="material_requests",
    )
    request_type = models.CharField(
        max_length=30,
        choices=StudyDocument.ContentType.choices,
    )
    description = models.TextField(max_length=500)
    student_name = models.CharField(max_length=120, blank=True)
    email = models.EmailField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
    )
    supervisor_notes = models.TextField(blank=True)
    fulfilled_document = models.ForeignKey(
        StudyDocument,
        on_delete=models.SET_NULL,
        related_name="fulfilled_material_requests",
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
        ]
        permissions = [
            (
                "manage_missing_material_requests",
                "Can manage missing material requests within assigned scope",
            ),
        ]
        verbose_name = "طلب ملف ناقص"
        verbose_name_plural = "طلبات الملفات الناقصة"

    def clean(self):
        super().clean()
        if self.description and not self.description.strip():
            raise ValidationError({"description": "وصف الطلب مطلوب."})
        if self.fulfilled_document_id:
            if not self.fulfilled_document.can_be_public:
                raise ValidationError(
                    {"fulfilled_document": "يجب اختيار ملف منشور ومتاح للعامة."},
                )
            if self.fulfilled_document.offering_id != self.offering_id:
                raise ValidationError(
                    {"fulfilled_document": "الملف المنشور يجب أن يخص المادة نفسها."},
                )

    def __str__(self):
        return f"{self.get_request_type_display()} - {self.offering.course.name}"


def make_slug(value):
    slug = slugify(value, allow_unicode=True)
    return slug or value.replace(" ", "-")
