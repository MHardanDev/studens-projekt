from pathlib import Path

from django import forms
from django.conf import settings
from django.utils import timezone

from accounts.models import ContributorScope, User

from .models import (
    CourseOffering,
    DocumentReport,
    MissingMaterialRequest,
    StudyDocument,
)
from .publication import published_documents
from .rights import RIGHTS_DECLARATION_TEXT


class StudyDocumentUploadForm(forms.ModelForm):
    upload = forms.FileField(label="ملف PDF")
    rights_declaration = forms.BooleanField(
        label="أوافق على إقرار حق المشاركة",
        help_text=RIGHTS_DECLARATION_TEXT,
    )

    class Meta:
        model = StudyDocument
        fields = [
            "offering",
            "title",
            "description",
            "content_type",
            "content_owner_name",
            "content_source",
            "rights_basis",
            "license_name",
            "permission_evidence",
            "rights_contact",
            "academic_year",
            "publication_year",
            "upload",
        ]
        labels = {
            "offering": "المادة",
            "title": "العنوان",
            "description": "الوصف",
            "content_type": "نوع المحتوى",
            "content_owner_name": "اسم صاحب المحتوى",
            "content_source": "مصدر المحتوى",
            "rights_basis": "أساس السماح بالنشر",
            "license_name": "اسم الترخيص وشروطه (عند الانطباق)",
            "permission_evidence": "دليل الإذن الخاص (عند الانطباق)",
            "rights_contact": "وسيلة تواصل للتحقق (اختيارية وخاصة)",
            "academic_year": "العام الدراسي",
            "publication_year": "سنة النشر",
        }
        help_texts = {
            "content_source": (
                "صف المصدر بوضوح، مثل: ملاحظاتي الأصلية أو اسم صاحب الملف."
            ),
            "permission_evidence": (
                "يظهر للمشرفين المخولين فقط، ولا ينشر في صفحة الملف."
            ),
            "rights_contact": (
                "للمراجعة عند الحاجة فقط، ولا يظهر للطلاب أو في البحث."
            ),
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "content_source": forms.Textarea(attrs={"rows": 3}),
            "permission_evidence": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields["offering"].queryset = scoped_offerings_for_user(user)
        self.fields["description"].required = False
        self.fields["content_owner_name"].required = True
        self.fields["content_source"].required = True
        self.fields["rights_basis"].required = True
        self.fields["academic_year"].required = False
        self.fields["publication_year"].required = False
        self.fields["license_name"].required = False
        self.fields["permission_evidence"].required = False
        self.fields["rights_contact"].required = False

    def clean(self):
        cleaned_data = super().clean()
        rights_basis = cleaned_data.get("rights_basis")
        if (
            rights_basis == StudyDocument.RightsBasis.OWNER_PERMISSION
            and not cleaned_data.get("permission_evidence", "").strip()
        ):
            self.add_error(
                "permission_evidence",
                "أضف مرجعاً خاصاً يوضح الإذن الصريح من صاحب المحتوى.",
            )
        if (
            rights_basis == StudyDocument.RightsBasis.OPEN_LICENSE
            and not cleaned_data.get("license_name", "").strip()
        ):
            self.add_error(
                "license_name",
                "اكتب اسم الترخيص وشروط الإسناد التي تسمح بالنشر.",
            )
        return cleaned_data

    def clean_upload(self):
        upload = self.cleaned_data["upload"]
        name = Path(upload.name).name
        suffix = Path(name).suffix.lower()
        if name != upload.name:
            raise forms.ValidationError("اسم الملف غير صالح.")
        if suffix != ".pdf":
            raise forms.ValidationError("يسمح برفع ملفات PDF فقط.")
        if upload.size > settings.MAX_UPLOAD_SIZE:
            raise forms.ValidationError("حجم الملف يتجاوز الحد المسموح 20 MiB.")
        content_type = getattr(upload, "content_type", "")
        if content_type not in settings.ALLOWED_UPLOAD_CONTENT_TYPES:
            raise forms.ValidationError("نوع الملف المعلن ليس PDF.")

        position = upload.tell()
        upload.seek(0)
        header = upload.read(5)
        upload.seek(position)
        if header != b"%PDF-":
            raise forms.ValidationError("محتوى الملف لا يبدأ بتوقيع PDF الصحيح.")
        return upload

    def save(self, commit=True):
        document = super().save(commit=False)
        upload = self.cleaned_data["upload"]
        document.contributor = self.user
        document.contributor_name = self.user.get_username()
        document.rights_declaration_text = RIGHTS_DECLARATION_TEXT
        document.rights_declared_at = timezone.now()
        document.rights_declared_by = self.user
        document.status = StudyDocument.Status.UPLOADED_PENDING_SCAN
        document.scan_status = StudyDocument.ScanStatus.PENDING
        document.uploaded_file = upload
        document.original_filename = Path(upload.name).name
        document.file_size = upload.size
        document.uploaded_content_type = getattr(upload, "content_type", "")
        document.scan_notes = "لم يتم تشغيل فحص antivirus حقيقي بعد."
        if commit:
            document.save()
        return document


def scoped_offerings_for_user(user):
    if not user or not user.is_authenticated:
        return CourseOffering.objects.none()
    if user.role != User.Role.TRUSTED_CONTRIBUTOR:
        return CourseOffering.objects.none()

    scopes = ContributorScope.objects.filter(user=user)
    query = CourseOffering.objects.none()
    for scope in scopes:
        current = CourseOffering.objects.all()
        if scope.course_id:
            current = current.filter(course=scope.course)
        if scope.program_id:
            current = current.filter(program=scope.program)
        if scope.faculty_id:
            current = current.filter(program__faculty=scope.faculty)
        if scope.university_id:
            current = current.filter(program__faculty__university=scope.university)
        query = query | current
    return query.select_related(
        "course",
        "program__faculty__university",
        "year_level",
        "term",
    ).distinct()


class ModerationDecisionForm(forms.Form):
    action = forms.ChoiceField(
        choices=[("approve", "اعتماد"), ("reject", "رفض")],
        widget=forms.HiddenInput,
    )
    rejection_reason = forms.CharField(
        label="سبب الرفض",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("action") == "reject" and not cleaned_data.get(
            "rejection_reason",
            "",
        ).strip():
            self.add_error("rejection_reason", "سبب الرفض مطلوب عند رفض الملف.")
        return cleaned_data


class DocumentReportForm(forms.ModelForm):
    class Meta:
        model = DocumentReport
        fields = ["report_type", "body", "reporter_contact"]
        labels = {
            "report_type": "نوع البلاغ",
            "body": "نص البلاغ",
            "reporter_contact": "وسيلة تواصل اختيارية",
        }
        widgets = {
            "body": forms.Textarea(attrs={"rows": 4}),
            "reporter_contact": forms.TextInput(
                attrs={"autocomplete": "email"},
            ),
        }
        help_texts = {
            "reporter_contact": (
                "يبقى خاصاً ولا يظهر في صفحة الملف أو الصفحات العامة."
            ),
        }


class DocumentReportModerationForm(forms.Form):
    action = forms.ChoiceField(
        choices=[
            ("review", "بدء المراجعة"),
            ("resolve", "إغلاق بعد المعالجة"),
            ("reject", "رفض البلاغ"),
            ("block", "حجب الملف"),
        ],
        widget=forms.HiddenInput,
    )
    moderator_notes = forms.CharField(
        label="ملاحظات المعالجة",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def clean(self):
        cleaned_data = super().clean()
        if (
            cleaned_data.get("action") == "block"
            and not cleaned_data.get("moderator_notes", "").strip()
        ):
            self.add_error("moderator_notes", "سبب الحجب مطلوب.")
        return cleaned_data


class MissingMaterialRequestForm(forms.ModelForm):
    class Meta:
        model = MissingMaterialRequest
        fields = [
            "offering",
            "request_type",
            "description",
            "student_name",
            "email",
        ]
        labels = {
            "offering": "المادة والسياق الدراسي",
            "request_type": "نوع الملف المطلوب",
            "description": "وصف مختصر",
            "student_name": "اسم الطالب (اختياري)",
            "email": "البريد الإلكتروني (اختياري وخاص)",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4, "maxlength": 500}),
            "student_name": forms.TextInput(attrs={"autocomplete": "name"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
        }
        error_messages = {
            "description": {
                "required": "اكتب وصفاً مختصراً للملف المطلوب.",
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["offering"].queryset = CourseOffering.objects.select_related(
            "course",
            "program__faculty__university",
            "year_level",
            "term",
        ).order_by(
            "program__faculty__university__name",
            "program__faculty__name",
            "program__name",
            "year_level__order",
            "term__order",
            "course__name",
        )

    def clean_description(self):
        description = self.cleaned_data["description"].strip()
        if not description:
            raise forms.ValidationError("اكتب وصفاً مختصراً للملف المطلوب.")
        return description


class MissingMaterialRequestModerationForm(forms.ModelForm):
    class Meta:
        model = MissingMaterialRequest
        fields = ["status", "supervisor_notes", "fulfilled_document"]
        labels = {
            "status": "الحالة",
            "supervisor_notes": "ملاحظات المشرف",
            "fulfilled_document": "الملف المنشور المرتبط",
        }
        widgets = {
            "supervisor_notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.offering_id:
            self.fields["fulfilled_document"].queryset = published_documents().filter(
                offering=self.instance.offering,
            )
        else:
            self.fields["fulfilled_document"].queryset = StudyDocument.objects.none()
