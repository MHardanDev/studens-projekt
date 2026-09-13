from django.db.models import Q

from .models import ModeratorScope, User


def offering_matches_scope(offering, scope):
    if scope.course_id and offering.course_id != scope.course_id:
        return False
    if scope.program_id and offering.program_id != scope.program_id:
        return False
    if scope.faculty_id and offering.program.faculty_id != scope.faculty_id:
        return False
    if (
        scope.university_id
        and offering.program.faculty.university_id != scope.university_id
    ):
        return False
    return True


def moderator_scope_filter(user, prefix=""):
    scopes = ModeratorScope.objects.filter(user=user)
    query = Q(pk__in=[])
    for scope in scopes:
        current = Q()
        if scope.course_id:
            current &= Q(**{f"{prefix}offering__course": scope.course})
        if scope.program_id:
            current &= Q(**{f"{prefix}offering__program": scope.program})
        if scope.faculty_id:
            current &= Q(**{f"{prefix}offering__program__faculty": scope.faculty})
        if scope.university_id:
            current &= Q(
                **{
                    f"{prefix}offering__program__faculty__university": (
                        scope.university
                    ),
                },
            )
        query |= current
    return query


def user_can_moderate_offering(user, offering):
    if not user or not user.is_authenticated:
        return False
    if user.role not in {User.Role.FACULTY_MODERATOR, User.Role.SITE_ADMIN}:
        return False
    scopes = ModeratorScope.objects.filter(user=user).select_related(
        "university",
        "faculty",
        "program",
        "course",
    )
    return any(offering_matches_scope(offering, scope) for scope in scopes)


def user_can_access_material_request_management(user):
    if not user or not user.is_authenticated:
        return False
    if user.role in {User.Role.FACULTY_MODERATOR, User.Role.SITE_ADMIN}:
        return True
    return bool(
        user.role == User.Role.TRUSTED_CONTRIBUTOR
        and user.has_perm("catalog.manage_missing_material_requests")
    )


def user_can_manage_material_request(user, material_request):
    if not user_can_access_material_request_management(user):
        return False
    scopes = ModeratorScope.objects.filter(user=user).select_related(
        "university",
        "faculty",
        "program",
        "course",
    )
    return any(
        offering_matches_scope(material_request.offering, scope) for scope in scopes
    )


def user_can_review_document(user, document):
    if document.contributor_id and document.contributor_id == user.id:
        return False
    return user_can_moderate_offering(user, document.offering)


def user_can_access_document_report_management(user):
    return bool(
        user
        and user.is_authenticated
        and user.role in {User.Role.FACULTY_MODERATOR, User.Role.SITE_ADMIN}
    )


def user_can_manage_document_report(user, report):
    return user_can_access_document_report_management(
        user,
    ) and user_can_review_document(user, report.document)
