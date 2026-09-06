import secrets

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        TRUSTED_CONTRIBUTOR = "trusted_contributor", "TrustedContributor"
        FACULTY_MODERATOR = "faculty_moderator", "FacultyModerator"
        SITE_ADMIN = "site_admin", "SiteAdmin"

    role = models.CharField(
        max_length=32,
        choices=Role.choices,
        default=Role.STUDENT,
        db_index=True,
    )

    @property
    def can_publish_documents(self):
        return False


class ScopedModel(models.Model):
    university = models.ForeignKey(
        "catalog.University",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    faculty = models.ForeignKey(
        "catalog.Faculty",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    program = models.ForeignKey(
        "catalog.Program",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    course = models.ForeignKey(
        "catalog.Course",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )

    class Meta:
        abstract = True

    def clean(self):
        super().clean()
        if not any([self.university, self.faculty, self.program, self.course]):
            raise ValidationError("يجب تحديد نطاق واحد على الأقل.")

    def scope_label(self):
        parts = [
            self.university,
            self.faculty,
            self.program,
            self.course,
        ]
        return " / ".join(str(part) for part in parts if part) or "نطاق غير محدد"


class ContributorScope(ScopedModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="contributor_scopes",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "نطاق مساهم"
        verbose_name_plural = "نطاقات المساهمين"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(university__isnull=False)
                    | models.Q(faculty__isnull=False)
                    | models.Q(program__isnull=False)
                    | models.Q(course__isnull=False)
                ),
                name="contributor_scope_has_boundary",
            ),
        ]

    def __str__(self):
        return f"{self.user} - {self.scope_label()}"


class ModeratorScope(ScopedModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="moderator_scopes",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "نطاق مشرف"
        verbose_name_plural = "نطاقات المشرفين"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(university__isnull=False)
                    | models.Q(faculty__isnull=False)
                    | models.Q(program__isnull=False)
                    | models.Q(course__isnull=False)
                ),
                name="moderator_scope_has_boundary",
            ),
        ]

    def __str__(self):
        return f"{self.user} - {self.scope_label()}"


def invitation_token():
    return secrets.token_urlsafe(32)


class ContributorInvitation(ScopedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "pending"
        ACCEPTED = "accepted", "accepted"
        REVOKED = "revoked", "revoked"
        EXPIRED = "expired", "expired"

    invited_identifier = models.CharField(max_length=254)
    requested_role = models.CharField(
        max_length=32,
        choices=[
            (User.Role.TRUSTED_CONTRIBUTOR, "TrustedContributor"),
            (User.Role.FACULTY_MODERATOR, "FacultyModerator"),
            (User.Role.SITE_ADMIN, "SiteAdmin"),
        ],
        default=User.Role.TRUSTED_CONTRIBUTOR,
    )
    token = models.CharField(max_length=128, unique=True, default=invitation_token)
    expires_at = models.DateTimeField()
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="created_invitations",
        blank=True,
        null=True,
    )
    accepted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="accepted_invitations",
        blank=True,
        null=True,
    )
    accepted_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "دعوة مساهم"
        verbose_name_plural = "دعوات المساهمين"
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(university__isnull=False)
                    | models.Q(faculty__isnull=False)
                    | models.Q(program__isnull=False)
                    | models.Q(course__isnull=False)
                ),
                name="invitation_scope_has_boundary",
            ),
        ]

    def __str__(self):
        return f"{self.invited_identifier} - {self.get_requested_role_display()}"

    def is_expired(self):
        return timezone.now() >= self.expires_at

    def can_accept(self):
        return self.status == self.Status.PENDING and not self.is_expired()

    def accept(self, user):
        if self.status != self.Status.PENDING:
            raise ValidationError("هذه الدعوة غير متاحة.")
        if self.is_expired():
            self.status = self.Status.EXPIRED
            self.save(update_fields=["status"])
            raise ValidationError("انتهت صلاحية هذه الدعوة.")

        user.role = self.requested_role
        user.is_superuser = False
        user.save(update_fields=["role", "is_superuser"])

        if self.requested_role == User.Role.TRUSTED_CONTRIBUTOR:
            ContributorScope.objects.get_or_create(
                user=user,
                university=self.university,
                faculty=self.faculty,
                program=self.program,
                course=self.course,
            )
        elif self.requested_role == User.Role.FACULTY_MODERATOR:
            ModeratorScope.objects.get_or_create(
                user=user,
                university=self.university,
                faculty=self.faculty,
                program=self.program,
                course=self.course,
            )

        self.status = self.Status.ACCEPTED
        self.accepted_by = user
        self.accepted_at = timezone.now()
        self.save(update_fields=["status", "accepted_by", "accepted_at"])
        return user

# Create your models here.
