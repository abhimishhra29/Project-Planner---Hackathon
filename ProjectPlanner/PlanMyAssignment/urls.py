from django.urls import path
from .views import home, projects, add_project, add_reviewer, reviews

urlpatterns = [
    path("projects/create/", add_project, name="create_project"),
    path("projects/list/", projects, name="list_projects"),
    path("reviewer/create/", add_reviewer, name="create_reviewer"),
    path("reviewer/list/", reviews, name="list_gradings"),
    path("", home, name="home"),
]
