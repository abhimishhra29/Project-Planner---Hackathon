from django.urls import path
from .views import home, projects, add_project

urlpatterns = [
    path("projects/create/", add_project, name="create_project"),
    path("projects/list/", projects, name="list_projects"),
    path("", home, name="home"),
]
