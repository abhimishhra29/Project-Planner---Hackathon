from django.shortcuts import render

# Create your views here.
def home(request):
    return render(request, "base.html")

def projects(request):
    return render(request, "projects.html")

def add_project(request):
    return render(request, "add_project.html")