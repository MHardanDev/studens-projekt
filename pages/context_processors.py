from django.conf import settings


def language_links(request):
    parts = request.path_info.strip("/").split("/")
    current_codes = {code for code, _name in settings.LANGUAGES}
    suffix_parts = parts[1:] if parts and parts[0] in current_codes else parts
    suffix = "/".join(part for part in suffix_parts if part)
    links = []
    for code, name in settings.LANGUAGES:
        href = f"/{code}/"
        if suffix:
            href = f"{href}{suffix}/"
        links.append({"code": code, "name": name, "href": href})
    return {"language_links": links}
