from django.urls import path

from . import views

app_name = "pages"

urlpatterns = [
    path("", views.home, name="home"),
    path("browse/", views.browse, name="browse"),
    path("preferences/data-saver/", views.set_data_saver, name="set_data_saver"),
]
