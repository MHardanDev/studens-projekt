INDEXABLE_VIEW_NAMES = {
    "pages:home",
    "pages:browse",
    "pages:about",
    "pages:content_guidelines",
    "pages:privacy",
    "pages:contact_reporting",
    "catalog:course_detail",
    "catalog:document_detail",
}


class PrivatePageNoIndexMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        match = request.resolver_match
        view_name = match.view_name if match else ""
        is_search = view_name in {"pages:home", "pages:browse"} and bool(
            request.GET.get("q", "").strip(),
        )
        if view_name not in INDEXABLE_VIEW_NAMES or is_search:
            response.setdefault("X-Robots-Tag", "noindex, nofollow")
        return response
