import json

from django.conf import settings
from django.utils.safestring import mark_safe


def _plain_text(value, limit):
    text = " ".join(str(value).split())
    if len(text) <= limit:
        return text
    return f"{text[: limit - 1].rstrip()}…"


def _safe_json(data):
    serialized = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    serialized = (
        serialized.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
    )
    return mark_safe(serialized)


def page_seo(
    request,
    *,
    title,
    description,
    canonical_path=None,
    schema_type="WebPage",
    schema_extra=None,
    og_type="website",
    indexable=True,
):
    canonical_url = request.build_absolute_uri(canonical_path or request.path)
    clean_title = _plain_text(title, 70)
    clean_description = _plain_text(description, 160)
    schema = {
        "@context": "https://schema.org",
        "@type": schema_type,
        "name": clean_title,
        "description": clean_description,
        "url": canonical_url,
        "inLanguage": getattr(request, "LANGUAGE_CODE", settings.LANGUAGE_CODE),
    }
    if schema_extra:
        schema.update(schema_extra)

    return {
        "site_name": settings.SITE_NAME,
        "seo_title": clean_title,
        "seo_description": clean_description,
        "seo_canonical_url": canonical_url,
        "seo_og_type": og_type,
        "seo_indexable": indexable,
        "seo_structured_data": _safe_json(schema) if indexable else "",
    }
