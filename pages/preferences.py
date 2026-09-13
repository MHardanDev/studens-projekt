from urllib.parse import parse_qs, urlencode, urlsplit

from django.conf import settings
from django.urls import Resolver404, resolve

DATA_SAVER_COOKIE = "data_saver"
LAST_LOCATION_COOKIE = "last_public_location"
COOKIE_MAX_AGE = 30 * 24 * 60 * 60
REMEMBERED_VIEWS = {
    "catalog:course_detail",
    "catalog:document_detail",
    "pages:browse",
    "pages:home",
}


def preference_context(request):
    return {
        "data_saver_enabled": request.COOKIES.get(DATA_SAVER_COOKIE) == "1",
        "resume_url": safe_resume_url(
            request.COOKIES.get(LAST_LOCATION_COOKIE, ""),
        ),
        "site_name": settings.SITE_NAME,
    }


def remember_public_location(response, request, *, include_search=False):
    location = request.path
    if include_search:
        query = safe_search_query(request.GET.get("q", ""))
        if query:
            location = f"{location}?{urlencode({'q': query})}"
    response.set_cookie(
        LAST_LOCATION_COOKIE,
        location,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="Lax",
    )
    return response


def safe_search_query(value):
    value = " ".join(value.split())[:80]
    if not value or "@" in value or "://" in value:
        return ""
    if any(ord(character) < 32 for character in value):
        return ""
    return value


def safe_resume_url(value):
    if not value or len(value) > 300:
        return None

    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc or not parsed.path.startswith("/"):
        return None
    if parsed.path.startswith("//") or parsed.fragment:
        return None

    try:
        match = resolve(parsed.path)
    except Resolver404:
        return None
    if match.view_name not in REMEMBERED_VIEWS:
        return None

    if not parsed.query:
        return parsed.path
    if match.view_name not in {"pages:home", "pages:browse"}:
        return None

    query_values = parse_qs(parsed.query, keep_blank_values=False)
    if set(query_values) != {"q"} or len(query_values["q"]) != 1:
        return None
    query = safe_search_query(query_values["q"][0])
    if not query:
        return None
    return f"{parsed.path}?{urlencode({'q': query})}"
