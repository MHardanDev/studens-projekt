from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_safe

from accounts.models import User
from accounts.permissions import moderator_scope_filter, user_can_review_document
from pages.preferences import remember_public_location

from .downloads import download_response, has_published_file
from .forms import (
    DocumentReportForm,
    ModerationDecisionForm,
    StudyDocumentUploadForm,
    scoped_offerings_for_user,
)
from .models import StudyDocument
from .publication import published_documents


@login_required
def upload_document(request):
    if request.user.role != User.Role.TRUSTED_CONTRIBUTOR:
        raise PermissionDenied("الرفع متاح للمساهمين الموثوقين فقط.")
    if not scoped_offerings_for_user(request.user).exists():
        raise PermissionDenied("لا يوجد نطاق رفع مخصص لهذا الحساب.")

    if request.method == "POST":
        form = StudyDocumentUploadForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                "تم رفع الملف وحفظه بانتظار الفحص. لن يظهر للطلاب قبل المراجعة.",
            )
            return redirect("pages:home")
    else:
        form = StudyDocumentUploadForm(user=request.user)

    return render(
        request,
        "catalog/upload_document.html",
        {
            "form": form,
            "max_upload_mib": 20,
        },
    )


@login_required
def moderation_documents(request):
    if request.user.role not in {User.Role.FACULTY_MODERATOR, User.Role.SITE_ADMIN}:
        raise PermissionDenied("المراجعة متاحة للمشرفين ضمن نطاقهم فقط.")

    documents = review_documents_for_user(request.user)

    if request.method == "POST":
        document = get_object_or_404(
            StudyDocument.objects.select_related(
                "contributor",
                "offering__course",
                "offering__program__faculty__university",
            ),
            pk=request.POST.get("document_id"),
        )
        if not user_can_review_document(request.user, document):
            raise PermissionDenied("لا تملك صلاحية مراجعة هذا الملف.")

        form = ModerationDecisionForm(request.POST)
        if form.is_valid():
            try:
                if form.cleaned_data["action"] == "approve":
                    document.approve(request.user)
                    messages.success(request, "تم اعتماد الملف وإنشاء نسخة منشورة.")
                else:
                    document.reject(
                        request.user,
                        form.cleaned_data["rejection_reason"],
                    )
                    messages.success(request, "تم رفض الملف وحفظ سبب الرفض.")
                return redirect("catalog:moderation_documents")
            except ValidationError as error:
                form.add_error(None, error)
    else:
        form = ModerationDecisionForm()

    return render(
        request,
        "catalog/moderation_documents.html",
        {
            "documents": documents,
            "form": form,
        },
    )


def report_document(request, document_id):
    document = get_object_or_404(
        published_documents().select_related("offering__course"),
        pk=document_id,
    )
    if request.method == "POST":
        form = DocumentReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.document = document
            if request.user.is_authenticated:
                report.reporter = request.user
            report.full_clean()
            report.save()
            messages.success(request, "تم إرسال البلاغ وسيراجعه الفريق.")
            return redirect(document)
    else:
        form = DocumentReportForm()

    return render(
        request,
        "catalog/report_document.html",
        {
            "document": document,
            "form": form,
        },
    )


@require_safe
def document_detail(request, document_id):
    document = get_object_or_404(
        published_documents().select_related(
            "published_version__offering__course",
            "published_version__offering__program__faculty__university",
            "published_version__offering__year_level",
            "published_version__offering__term",
        ),
        pk=document_id,
    )
    version = document.published_version
    response = render(
        request,
        "catalog/document_detail.html",
        {
            "document": document,
            "version": version,
            "download_available": has_published_file(version),
            "site_name": settings.SITE_NAME,
        },
    )
    return remember_public_location(response, request)


@require_http_methods(["GET", "HEAD"])
def download_document(request, document_id):
    document = get_object_or_404(
        published_documents().select_related("published_version"),
        pk=document_id,
    )
    return download_response(request, document.published_version)


def review_documents_for_user(user):
    return (
        StudyDocument.objects.filter(
            status=StudyDocument.Status.PENDING_REVIEW,
            scan_status=StudyDocument.ScanStatus.CLEAN,
        )
        .filter(moderator_scope_filter(user))
        .exclude(contributor=user)
        .select_related(
            "contributor",
            "offering__course",
            "offering__program__faculty__university",
            "offering__year_level",
            "offering__term",
        )
        .order_by("updated_at", "title")
        .distinct()
    )
