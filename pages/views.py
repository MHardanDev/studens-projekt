from django.conf import settings
from django.db.models import Count, Prefetch, Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST, require_safe

from catalog.models import CourseOffering, StudyDocument, University
from catalog.publication import published_documents

from .preferences import (
    COOKIE_MAX_AGE,
    DATA_SAVER_COOKIE,
    remember_public_location,
)
from .seo import page_seo


def approved_documents():
    return published_documents()


def search_catalog(query):
    if not query:
        return [], []
    course_results = (
        CourseOffering.objects.filter(
            Q(course__name__icontains=query) | Q(course__code__icontains=query),
        )
        .select_related("course", "program__faculty__university", "year_level", "term")
        .annotate(approved_document_count=Count("documents"))
        .order_by(
            "program__faculty__university__name",
            "program__faculty__name",
            "year_level__order",
            "term__order",
            "course__name",
        )[:10]
    )
    document_results = (
        approved_documents()
        .filter(title__icontains=query)
        .select_related(
            "offering__course",
            "offering__program__faculty__university",
            "offering__year_level",
            "offering__term",
        )
        .order_by("-updated_at", "title")[:10]
    )
    return course_results, document_results


def base_context():
    return {
        "site_name": settings.SITE_NAME,
    }


def home(request):
    context = base_context()
    context["query"] = request.GET.get("q", "").strip()
    home_path = reverse("pages:home")
    context.update(
        page_seo(
            request,
            title=f"{settings.SITE_NAME} | ملفات ومواد جامعية للطلاب",
            description=(
                "ابحث مجاناً عن المواد والملفات الجامعية المنشورة، "
                "وتصفح الكليات والبرامج من واجهة عربية خفيفة."
            ),
            canonical_path=home_path,
            schema_type="WebSite",
            schema_extra={
                "potentialAction": {
                    "@type": "SearchAction",
                    "target": (
                        f"{request.build_absolute_uri(home_path)}"
                        "?q={search_term_string}"
                    ),
                    "query-input": "required name=search_term_string",
                },
            },
            indexable=not context["query"],
        ),
    )
    context["latest_documents"] = (
        approved_documents()
        .select_related(
            "offering__course",
            "offering__program__faculty__university",
            "offering__year_level",
            "offering__term",
        )
        .order_by("-updated_at", "title")[:5]
    )
    context["available_faculties"] = University.objects.prefetch_related(
        "faculties__programs",
    )
    context["missing_offerings"] = (
        CourseOffering.objects.select_related(
            "course",
            "program__faculty__university",
            "year_level",
            "term",
        )
        .annotate(
            document_count=Count(
                "documents",
                filter=Q(
                    documents__status=StudyDocument.Status.APPROVED,
                    documents__scan_status=StudyDocument.ScanStatus.CLEAN,
                    documents__published_version__isnull=False,
                ),
            ),
        )
        .filter(document_count=0)
        .order_by("year_level__order", "term__order", "course__name")[:5]
    )
    course_results, document_results = search_catalog(context["query"])
    context["course_results"] = course_results
    context["document_results"] = document_results
    context["has_search_results"] = bool(course_results or document_results)
    response = render(request, "pages/home.html", context)
    if context["query"]:
        return remember_public_location(response, request, include_search=True)
    return response


def browse(request):
    universities = University.objects.prefetch_related(
        "faculties__programs__year_levels__terms__course_offerings__course",
        Prefetch(
            "faculties__programs__year_levels__terms__course_offerings__documents",
            queryset=approved_documents(),
            to_attr="public_documents",
        ),
    )
    context = base_context()
    context["query"] = request.GET.get("q", "").strip()
    context.update(
        page_seo(
            request,
            title=f"تصفح الكليات والمواد | {settings.SITE_NAME}",
            description=(
                "تصفح الجامعات والكليات والبرامج والمواد والملفات المنشورة "
                "من فهرس دراسي عربي خفيف."
            ),
            canonical_path=reverse("pages:browse"),
            schema_type="CollectionPage",
            indexable=not context["query"],
        ),
    )
    context["universities"] = universities
    course_results, document_results = search_catalog(context["query"])
    context["course_results"] = course_results
    context["document_results"] = document_results
    context["has_search_results"] = bool(course_results or document_results)
    response = render(request, "pages/browse.html", context)
    return remember_public_location(
        response,
        request,
        include_search=bool(context["query"]),
    )


@require_safe
def about(request):
    context = page_seo(
        request,
        title=f"عن الموقع | {settings.SITE_NAME}",
        description=(
            "تعرف إلى المبادرة الطلابية المستقلة وهدفها في تنظيم الوصول "
            "المجاني إلى الملفات الجامعية المنشورة."
        ),
    )
    return render(request, "pages/about.html", context)


@require_safe
def content_guidelines(request):
    context = page_seo(
        request,
        title=f"إرشادات مشاركة المحتوى | {settings.SITE_NAME}",
        description=(
            "إرشادات حقوق المصدر والإذن والفحص والمراجعة قبل نشر الملفات "
            "الدراسية على الموقع."
        ),
    )
    return render(request, "pages/content_guidelines.html", context)


@require_safe
def privacy(request):
    context = page_seo(
        request,
        title=f"الخصوصية | {settings.SITE_NAME}",
        description=(
            "مسودة خصوصية توضح البيانات والكوكيز والعدادات الداخلية المحدودة "
            "المستخدمة فعلياً في الموقع."
        ),
    )
    return render(request, "pages/privacy.html", context)


@require_safe
def contact_reporting(request):
    context = page_seo(
        request,
        title=f"التواصل والإبلاغ | {settings.SITE_NAME}",
        description=(
            "طريقة الإبلاغ عن خطأ أو ملف لا يفتح أو انتهاك حقوق في الملفات "
            "الجامعية المنشورة."
        ),
    )
    return render(request, "pages/contact_reporting.html", context)


@require_POST
def set_data_saver(request):
    enabled = request.POST.get("enabled") == "1"
    next_url = request.POST.get("next", "")
    if not (
        next_url.startswith("/")
        and not next_url.startswith("//")
        and url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        )
    ):
        next_url = reverse("pages:home")

    response = redirect(next_url)
    response.set_cookie(
        DATA_SAVER_COOKIE,
        "1" if enabled else "0",
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="Lax",
    )
    return response


def health(request):
    return JsonResponse({"status": "ok"})
