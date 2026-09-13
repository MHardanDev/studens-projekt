from django.conf import settings
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import override
from django.views.decorators.http import require_safe

from catalog.models import CourseOffering
from catalog.publication import published_documents


@require_safe
def sitemap(request):
    documents = list(
        published_documents().only("pk", "offering_id", "updated_at"),
    )
    offering_ids = {document.offering_id for document in documents}
    offerings = list(
        CourseOffering.objects.filter(pk__in=offering_ids).only("pk", "updated_at"),
    )
    static_view_names = [
        "pages:home",
        "pages:browse",
        "pages:about",
        "pages:content_guidelines",
        "pages:privacy",
        "pages:contact_reporting",
    ]

    entries = []
    for language_code, _language_name in settings.LANGUAGES:
        with override(language_code):
            for view_name in static_view_names:
                entries.append(
                    {"location": request.build_absolute_uri(reverse(view_name))},
                )
            for offering in offerings:
                entries.append(
                    {
                        "location": request.build_absolute_uri(
                            reverse("catalog:course_detail", args=[offering.pk]),
                        ),
                        "last_modified": offering.updated_at,
                    },
                )
            for document in documents:
                entries.append(
                    {
                        "location": request.build_absolute_uri(
                            reverse("catalog:document_detail", args=[document.pk]),
                        ),
                        "last_modified": document.updated_at,
                    },
                )

    response = render(
        request,
        "seo/sitemap.xml",
        {"entries": entries},
        content_type="application/xml",
    )
    response["Cache-Control"] = "public, max-age=3600"
    return response


@require_safe
def robots(request):
    response = render(
        request,
        "seo/robots.txt",
        {"sitemap_url": request.build_absolute_uri(reverse("sitemap"))},
        content_type="text/plain; charset=utf-8",
    )
    response["Cache-Control"] = "public, max-age=3600"
    return response
