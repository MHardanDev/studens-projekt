from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count, F, Sum
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_safe

from accounts.models import User
from accounts.permissions import (
    moderator_scope_filter,
    user_can_access_document_report_management,
    user_can_access_material_request_management,
    user_can_manage_document_report,
    user_can_manage_material_request,
    user_can_review_document,
)
from pages.preferences import remember_public_location
from pages.seo import page_seo

from .downloads import download_response, has_published_file
from .forms import (
    DocumentReportForm,
    DocumentReportModerationForm,
    MissingMaterialRequestForm,
    MissingMaterialRequestModerationForm,
    ModerationDecisionForm,
    StudyDocumentUploadForm,
    scoped_offerings_for_user,
)
from .models import (
    CourseOffering,
    DocumentReport,
    DocumentVersion,
    MissingMaterialRequest,
    StudyDocument,
)
from .publication import published_documents
from .rate_limits import consume_document_report_quota, consume_material_request_quota


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


@require_http_methods(["GET", "POST"])
def report_document(request, document_id):
    document = get_object_or_404(
        published_documents().select_related("offering__course"),
        pk=document_id,
    )
    if request.method == "POST":
        form = DocumentReportForm(request.POST)
        if form.is_valid():
            if not consume_document_report_quota(request):
                form.add_error(
                    None,
                    "وصلت إلى حد إرسال البلاغات المؤقت. حاول مرة أخرى لاحقاً.",
                )
                return render(
                    request,
                    "catalog/report_document.html",
                    {"document": document, "form": form},
                    status=429,
                )
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


@login_required
@require_http_methods(["GET", "POST"])
def moderation_document_reports(request):
    if not user_can_access_document_report_management(request.user):
        raise PermissionDenied("إدارة البلاغات تحتاج صلاحية إشراف.")

    selected_report = None
    selected_form = None
    if request.method == "POST":
        selected_report = get_object_or_404(
            DocumentReport.objects.select_related(
                "document__contributor",
                "document__offering__course",
                "document__offering__program__faculty__university",
            ),
            pk=request.POST.get("report_id"),
        )
        if not user_can_manage_document_report(request.user, selected_report):
            raise PermissionDenied("هذا البلاغ خارج نطاق إشرافك.")
        selected_form = DocumentReportModerationForm(request.POST)
        if selected_form.is_valid():
            try:
                selected_report.process(
                    request.user,
                    selected_form.cleaned_data["action"],
                    selected_form.cleaned_data["moderator_notes"],
                )
                messages.success(request, "تم تحديث البلاغ وتطبيق الإجراء.")
                return redirect("catalog:moderation_document_reports")
            except ValidationError as error:
                selected_form.add_error(None, error)

    report_rows = []
    for report in document_reports_for_user(request.user):
        report_rows.append(
            {
                "item": report,
                "form": selected_form
                if report == selected_report
                else DocumentReportModerationForm(),
            },
        )

    return render(
        request,
        "catalog/moderation_document_reports.html",
        {"report_rows": report_rows, "site_name": settings.SITE_NAME},
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
    description = version.description or (
        f"{version.get_content_type_display()} لمادة {version.offering.course.name}، "
        f"{version.offering.year_level.name}، {version.offering.term.name}."
    )
    seo_context = page_seo(
        request,
        title=f"{version.title} | {settings.SITE_NAME}",
        description=description,
        canonical_path=document.get_absolute_url(),
        schema_type="LearningResource",
        schema_extra={
            "learningResourceType": version.get_content_type_display(),
            "educationalLevel": version.offering.year_level.name,
            "isAccessibleForFree": True,
            "datePublished": (
                version.reviewed_at or version.created_at
            ).date().isoformat(),
            "about": {
                "@type": "Course",
                "name": version.offering.course.name,
            },
        },
        og_type="article",
    )
    response = render(
        request,
        "catalog/document_detail.html",
        {
            "document": document,
            "version": version,
            "download_available": has_published_file(version),
            "site_name": settings.SITE_NAME,
            **seo_context,
        },
    )
    return remember_public_location(response, request)


@require_http_methods(["GET", "HEAD"])
def download_document(request, document_id):
    document = get_object_or_404(
        published_documents().select_related("published_version"),
        pk=document_id,
    )
    version = document.published_version
    response = download_response(request, version)
    if (
        request.method == "GET"
        and "Range" not in request.headers
        and response.status_code == 200
    ):
        DocumentVersion.objects.filter(pk=version.pk).update(
            full_download_count=F("full_download_count") + 1,
        )
    return response


@require_safe
def course_detail(request, offering_id):
    offering = get_object_or_404(
        CourseOffering.objects.select_related(
            "course",
            "program__faculty__university",
            "year_level",
            "term",
        ),
        pk=offering_id,
    )
    documents = published_documents().filter(offering=offering).select_related(
        "published_version",
    )
    description = (
        f"ملفات وطلبات مادة {offering.course.name} في {offering.program.name}، "
        f"{offering.year_level.name}، {offering.term.name}."
    )
    schema_extra = {
        "educationalLevel": offering.year_level.name,
        "isAccessibleForFree": True,
    }
    if offering.course.code:
        schema_extra["courseCode"] = offering.course.code
    seo_context = page_seo(
        request,
        title=f"{offering.course.name} | {settings.SITE_NAME}",
        description=description,
        canonical_path=reverse(
            "catalog:course_detail",
            args=[offering.pk],
        ),
        schema_type="Course",
        schema_extra=schema_extra,
    )
    response = render(
        request,
        "catalog/course_detail.html",
        {
            "offering": offering,
            "documents": documents,
            "site_name": settings.SITE_NAME,
            **seo_context,
        },
    )
    return remember_public_location(response, request)


@login_required
@require_safe
def moderation_metrics(request):
    if request.user.role not in {User.Role.FACULTY_MODERATOR, User.Role.SITE_ADMIN}:
        raise PermissionDenied("عرض المؤشرات متاح للمشرفين والمديرين فقط.")

    scoped_documents = (
        published_documents()
        .filter(moderator_scope_filter(request.user))
        .distinct()
    )
    totals = {
        "documents": scoped_documents.count(),
        "downloads": (
            scoped_documents.aggregate(
                total=Sum("published_version__full_download_count"),
            )["total"]
            or 0
        ),
        "reports": DocumentReport.objects.filter(
            document__in=scoped_documents,
        ).count(),
    }
    documents = (
        scoped_documents.select_related(
            "published_version",
            "offering__course",
            "offering__program__faculty__university",
        )
        .annotate(report_count=Count("reports", distinct=True))
        .order_by("offering__course__name", "title")
    )
    return render(
        request,
        "catalog/moderation_metrics.html",
        {
            "documents": documents,
            "totals": totals,
            "site_name": settings.SITE_NAME,
        },
    )


@require_http_methods(["GET", "POST"])
def request_material(request):
    initial_offering = None
    if request.method == "GET" and request.GET.get("offering"):
        try:
            offering_id = int(request.GET["offering"])
        except (TypeError, ValueError) as error:
            raise Http404("المادة المطلوبة غير موجودة.") from error
        initial_offering = get_object_or_404(
            CourseOffering,
            pk=offering_id,
        )

    if request.method == "POST":
        form = MissingMaterialRequestForm(request.POST)
        if form.is_valid():
            if not consume_material_request_quota(request):
                form.add_error(
                    None,
                    "وصلت إلى حد الإرسال المؤقت. حاول مرة أخرى بعد عشر دقائق.",
                )
                return render(
                    request,
                    "catalog/request_material.html",
                    {"form": form, "site_name": settings.SITE_NAME},
                    status=429,
                )
            material_request = form.save()
            messages.success(
                request,
                "تم إرسال طلبك. سيظهر للمشرفين ضمن الكلية والبرنامج المناسبين.",
            )
            return redirect(
                "catalog:course_detail",
                offering_id=material_request.offering_id,
            )
    else:
        form = MissingMaterialRequestForm(initial={"offering": initial_offering})

    return render(
        request,
        "catalog/request_material.html",
        {"form": form, "site_name": settings.SITE_NAME},
    )


@login_required
@require_http_methods(["GET", "POST"])
def moderation_material_requests(request):
    if not user_can_access_material_request_management(request.user):
        raise PermissionDenied("إدارة الطلبات تحتاج صلاحية إشراف صريحة.")

    selected_request = None
    selected_form = None
    if request.method == "POST":
        selected_request = get_object_or_404(
            MissingMaterialRequest.objects.select_related(
                "offering__course",
                "offering__program__faculty__university",
                "offering__year_level",
                "offering__term",
            ),
            pk=request.POST.get("request_id"),
        )
        if not user_can_manage_material_request(request.user, selected_request):
            raise PermissionDenied("هذا الطلب خارج نطاق إشرافك.")
        selected_form = MissingMaterialRequestModerationForm(
            request.POST,
            instance=selected_request,
            prefix=f"request-{selected_request.pk}",
        )
        if selected_form.is_valid():
            selected_form.save()
            messages.success(request, "تم تحديث حالة الطلب.")
            return redirect("catalog:moderation_material_requests")

    material_requests = material_requests_for_user(request.user)
    request_rows = []
    for item in material_requests:
        item_form = selected_form if item == selected_request else (
            MissingMaterialRequestModerationForm(
                instance=item,
                prefix=f"request-{item.pk}",
            )
        )
        request_rows.append({"item": item, "form": item_form})

    return render(
        request,
        "catalog/moderation_material_requests.html",
        {
            "request_rows": request_rows,
            "site_name": settings.SITE_NAME,
        },
    )


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
            "rights_declared_by",
            "offering__course",
            "offering__program__faculty__university",
            "offering__year_level",
            "offering__term",
        )
        .order_by("updated_at", "title")
        .distinct()
    )


def document_reports_for_user(user):
    return (
        DocumentReport.objects.filter(
            moderator_scope_filter(user, prefix="document__"),
            status__in=[
                DocumentReport.Status.OPEN,
                DocumentReport.Status.REVIEWING,
            ],
        )
        .exclude(document__contributor=user)
        .select_related(
            "reporter",
            "document__contributor",
            "document__offering__course",
            "document__offering__program__faculty__university",
        )
        .order_by("created_at")
        .distinct()
    )


def material_requests_for_user(user):
    return (
        MissingMaterialRequest.objects.filter(moderator_scope_filter(user))
        .select_related(
            "fulfilled_document",
            "offering__course",
            "offering__program__faculty__university",
            "offering__year_level",
            "offering__term",
        )
        .order_by("status", "-created_at")
        .distinct()
    )
