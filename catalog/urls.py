from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("contribute/upload/", views.upload_document, name="upload_document"),
    path(
        "moderation/documents/",
        views.moderation_documents,
        name="moderation_documents",
    ),
    path(
        "moderation/requests/",
        views.moderation_material_requests,
        name="moderation_material_requests",
    ),
    path("requests/new/", views.request_material, name="request_material"),
    path(
        "courses/<int:offering_id>/",
        views.course_detail,
        name="course_detail",
    ),
    path(
        "documents/<int:document_id>/",
        views.document_detail,
        name="document_detail",
    ),
    path(
        "documents/<int:document_id>/download/",
        views.download_document,
        name="download_document",
    ),
    path(
        "documents/<int:document_id>/report/",
        views.report_document,
        name="report_document",
    ),
]
