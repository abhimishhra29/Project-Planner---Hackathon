from django.db import models

class Project(models.Model):
    project_name = models.CharField(max_length=255)
    project_deadline = models.DateField()

class Task(models.Model):
    project = models.ForeignKey(Project, related_name="tasks", on_delete=models.CASCADE)
    task_id = models.IntegerField()
    task_name = models.CharField(max_length=255)
    efforts = models.IntegerField()
    deadline = models.DateField()

class Step(models.Model):
    task = models.ForeignKey(Task, related_name="steps", on_delete=models.CASCADE)
    step_description = models.CharField(max_length=255)
