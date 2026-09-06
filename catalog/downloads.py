import hashlib
from pathlib import PurePosixPath

from django.core.files.storage import default_storage
from django.http import Http404, HttpResponse, StreamingHttpResponse
from django.utils.http import (
    content_disposition_header,
    http_date,
    parse_http_date_safe,
)

DOWNLOAD_CHUNK_SIZE = 64 * 1024


class InvalidRange(ValueError):
    pass


def published_file_name(version):
    name = version.internal_file_name
    if not name or "\\" in name:
        return None

    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        return None
    if not path.parts or path.parts[0] != "study-documents":
        return None

    normalized_name = str(path)
    if not default_storage.exists(normalized_name):
        return None
    return normalized_name


def has_published_file(version):
    return published_file_name(version) is not None


def download_response(request, version):
    name = published_file_name(version)
    if name is None:
        raise Http404("لا يوجد ملف PDF منشور للتنزيل.")

    size = default_storage.size(name)
    etag = version_etag(version, size)
    last_modified = version.reviewed_at or version.updated_at
    range_header = request.headers.get("Range")
    if range_header and request.method == "GET":
        if_range = request.headers.get("If-Range")
        if not if_range or if_range_matches(if_range, etag, last_modified):
            try:
                start, end = parse_byte_range(range_header, size)
            except InvalidRange:
                return range_not_satisfiable(size, etag, last_modified)
            return streaming_file_response(
                name,
                version,
                size,
                etag,
                last_modified,
                start=start,
                end=end,
                status=206,
            )

    if request.method == "HEAD":
        response = HttpResponse(content_type="application/pdf")
        set_download_headers(response, version, size, etag, last_modified)
        return response

    return streaming_file_response(
        name,
        version,
        size,
        etag,
        last_modified,
        start=0,
        end=max(size - 1, 0),
        status=200,
    )


def parse_byte_range(header, size):
    if not header.startswith("bytes=") or "," in header or size <= 0:
        raise InvalidRange

    range_value = header.removeprefix("bytes=").strip()
    if "-" not in range_value:
        raise InvalidRange
    start_value, end_value = range_value.split("-", 1)

    try:
        if not start_value:
            suffix_length = int(end_value)
            if suffix_length <= 0:
                raise InvalidRange
            start = max(size - suffix_length, 0)
            end = size - 1
        else:
            start = int(start_value)
            if start < 0 or start >= size:
                raise InvalidRange
            end = size - 1 if not end_value else int(end_value)
            if end < start:
                raise InvalidRange
            end = min(end, size - 1)
    except (TypeError, ValueError) as error:
        raise InvalidRange from error

    return start, end


def if_range_matches(value, etag, last_modified):
    value = value.strip()
    if value.startswith("W/"):
        return False
    if value.startswith('"'):
        return value == etag

    parsed_date = parse_http_date_safe(value)
    if parsed_date is None:
        return False
    return int(last_modified.timestamp()) <= parsed_date


def version_etag(version, size):
    validator = version.checksum_sha256
    if not validator:
        seed = f"{version.pk}:{size}:{version.updated_at.isoformat()}"
        validator = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return f'"{validator}"'


def streaming_file_response(
    name,
    version,
    size,
    etag,
    last_modified,
    *,
    start,
    end,
    status,
):
    length = 0 if size == 0 else end - start + 1
    response = StreamingHttpResponse(
        stream_file(name, start, length),
        status=status,
        content_type="application/pdf",
    )
    set_download_headers(response, version, length, etag, last_modified)
    if status == 206:
        response["Content-Range"] = f"bytes {start}-{end}/{size}"
    return response


def stream_file(name, start, length):
    with default_storage.open(name, "rb") as file_object:
        file_object.seek(start)
        remaining = length
        while remaining > 0:
            chunk = file_object.read(min(DOWNLOAD_CHUNK_SIZE, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk


def set_download_headers(response, version, length, etag, last_modified):
    filename = PurePosixPath(version.original_filename).name or "document.pdf"
    if not filename.lower().endswith(".pdf"):
        filename = f"{filename}.pdf"
    response["Content-Disposition"] = content_disposition_header(True, filename)
    response["Content-Length"] = str(length)
    response["Accept-Ranges"] = "bytes"
    response["ETag"] = etag
    response["Last-Modified"] = http_date(last_modified.timestamp())
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "no-store"


def range_not_satisfiable(size, etag, last_modified):
    response = HttpResponse(status=416)
    response["Content-Range"] = f"bytes */{size}"
    response["Content-Length"] = "0"
    response["Accept-Ranges"] = "bytes"
    response["ETag"] = etag
    response["Last-Modified"] = http_date(last_modified.timestamp())
    response["Cache-Control"] = "no-store"
    return response
