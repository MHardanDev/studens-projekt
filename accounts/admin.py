from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.urls import reverse
from django.utils.html import format_html

from .models import ContributorInvitation, ContributorScope, ModeratorScope, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("دور المنصة", {"fields": ("role",)}),
    )
    list_display = ["username", "email", "role", "is_staff", "is_superuser"]
    list_filter = UserAdmin.list_filter + ("role",)


class SiteAdminOnlyMixin:
    def has_module_permission(self, request):
        return self.has_view_permission(request)

    def has_view_permission(self, request, obj=None):
        return self._can_manage(request.user)

    def has_add_permission(self, request):
        return self._can_manage(request.user)

    def has_change_permission(self, request, obj=None):
        return self._can_manage(request.user)

    def has_delete_permission(self, request, obj=None):
        return self._can_manage(request.user)

    def _can_manage(self, user):
        return bool(
            user.is_active
            and user.is_staff
            and (user.is_superuser or user.role == User.Role.SITE_ADMIN)
        )


@admin.register(ContributorScope)
class ContributorScopeAdmin(SiteAdminOnlyMixin, admin.ModelAdmin):
    list_display = ["user", "university", "faculty", "program", "course", "created_at"]
    list_filter = ["university", "faculty", "program", "course"]
    search_fields = ["user__username", "user__email", "faculty__name", "course__name"]
    ordering = ["user__username", "university__name", "faculty__name"]


@admin.register(ModeratorScope)
class ModeratorScopeAdmin(SiteAdminOnlyMixin, admin.ModelAdmin):
    list_display = ["user", "university", "faculty", "program", "course", "created_at"]
    list_filter = ["university", "faculty", "program", "course"]
    search_fields = ["user__username", "user__email", "faculty__name", "course__name"]
    ordering = ["user__username", "university__name", "faculty__name"]


@admin.register(ContributorInvitation)
class ContributorInvitationAdmin(SiteAdminOnlyMixin, admin.ModelAdmin):
    list_display = [
        "invited_identifier",
        "requested_role",
        "status",
        "university",
        "faculty",
        "program",
        "course",
        "expires_at",
        "invitation_link",
    ]
    list_filter = [
        "requested_role",
        "status",
        "university",
        "faculty",
        "program",
        "course",
        "expires_at",
    ]
    search_fields = [
        "invited_identifier",
        "token",
        "faculty__name",
        "program__name",
        "course__name",
    ]
    readonly_fields = ["token", "invitation_link", "accepted_by", "accepted_at"]
    ordering = ["-created_at"]

    @admin.display(description="رابط الدعوة")
    def invitation_link(self, obj):
        if not obj.pk:
            return "يحفظ بعد إنشاء الدعوة"
        path = reverse("accounts:accept_invitation", args=[obj.token])
        return format_html('<code>{}</code>', path)

# Register your models here.
