from django.urls import path

from . import views

app_name = "pages"

urlpatterns = [
    path("", views.home, name="home"),
    path("browse/", views.browse, name="browse"),
    path("about/", views.about, name="about"),
    path("content-guidelines/", views.content_guidelines, name="content_guidelines"),
    path("privacy/", views.privacy, name="privacy"),
    path("contact-reporting/", views.contact_reporting, name="contact_reporting"),
    path("preferences/data-saver/", views.set_data_saver, name="set_data_saver"),
]
