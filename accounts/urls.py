from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.LoginPageView.as_view(), name="login"),
    path("logout/", views.logout_view, name="logout"),
    path(
        "invitations/<str:token>/",
        views.accept_invitation,
        name="accept_invitation",
    ),
]
