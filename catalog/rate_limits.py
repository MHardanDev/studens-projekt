from hashlib import sha256

from django.conf import settings
from django.core.cache import cache


def consume_material_request_quota(request):
    identity = request_identity(request)
    digest = sha256(
        f"{settings.SECRET_KEY}:{identity}".encode("utf-8"),
    ).hexdigest()
    cache_key = f"material-request-rate:{digest}"
    timeout = settings.MATERIAL_REQUEST_RATE_WINDOW_SECONDS

    if cache.add(cache_key, 1, timeout=timeout):
        return True
    try:
        count = cache.incr(cache_key)
    except ValueError:
        return cache.add(cache_key, 1, timeout=timeout)
    return count <= settings.MATERIAL_REQUEST_RATE_LIMIT


def request_identity(request):
    if request.user.is_authenticated:
        return f"user:{request.user.pk}"
    remote_address = request.META.get("REMOTE_ADDR", "unknown")
    user_agent = request.META.get("HTTP_USER_AGENT", "")[:160]
    return f"visitor:{remote_address}:{user_agent}"
