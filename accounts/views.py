from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.exceptions import ValidationError
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy

from .models import ContributorInvitation


class LoginPageView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        return self.get_redirect_url() or reverse_lazy("pages:home")


def logout_view(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    logout(request)
    messages.success(request, "تم تسجيل الخروج.")
    return redirect("pages:home")


def _matches_invited_identifier(invitation, user):
    identifier = invitation.invited_identifier.strip().lower()
    return identifier in {
        user.username.lower(),
        (user.email or "").lower(),
    }


@login_required
def accept_invitation(request, token):
    invitation = get_object_or_404(ContributorInvitation, token=token)
    if request.method == "POST":
        if not _matches_invited_identifier(invitation, request.user):
            messages.error(request, "هذه الدعوة ليست مخصصة لهذا الحساب.")
        else:
            try:
                invitation.accept(request.user)
            except ValidationError as error:
                messages.error(request, error.messages[0])
            else:
                messages.success(request, "تم قبول الدعوة وتحديث دور الحساب.")
                return redirect("pages:home")
    return render(
        request,
        "accounts/accept_invitation.html",
        {"invitation": invitation},
    )
