from django.urls import path
from .views import home, projects, add_project

urlpatterns = [
    path("add_project", add_project),
    path("projects", projects),
    path("", home),
]
