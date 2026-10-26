from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .forms import LoginForm

urlpatterns = [
    path("", views.landing, name="landing"),
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="Inv_Dramas/login.html",
            authentication_form=LoginForm,
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("register/", views.register, name="register"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("dashboard/", views.index, name="dashboard"),
    path("dashboard/featured/", views.featured_manage, name="featured_manage"),
    path("dramas/", views.drama_list, name="drama_list"),
    path("dramas/add/", views.drama_create, name="drama_create"),
    path("dramas/<int:pk>/", views.drama_detail, name="drama_detail"),
    path("dramas/<int:pk>/edit/", views.drama_edit, name="drama_edit"),
    path("dramas/<int:pk>/delete/", views.drama_delete, name="drama_delete"),
]
