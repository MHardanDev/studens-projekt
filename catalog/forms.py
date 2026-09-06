from pathlib import Path

from django import forms
from django.conf import settings

from accounts.models import ContributorScope, User

from .models import CourseOffering, DocumentReport, StudyDocument


class StudyDocumentUploadForm(forms.ModelForm):
    upload = forms.FileField(label="ملف PDF")

    class Meta:
        model = StudyDocument
        fields = [
            "offering",
            "title",
            "description",
            "content_type",
            "academic_year",
            "publication_year",
            "upload",
        ]
        labels = {
            "offering": "المادة",
            "title": "العنوان",
            "description": "الوصف",
            "content_type": "نوع المحتوى",
            "academic_year": "العام الدراسي",
            "publication_year": "سنة النشر",
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields["offering"].queryset = scoped_offerings_for_user(user)
        self.fields["description"].required = False
        self.fields["academic_year"].required = False
        self.fields["publication_year"].required = False

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
        }
