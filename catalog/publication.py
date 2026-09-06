from .models import StudyDocument


def published_documents():
    return StudyDocument.objects.filter(
        status=StudyDocument.Status.APPROVED,
        scan_status=StudyDocument.ScanStatus.CLEAN,
        published_version__isnull=False,
    )
