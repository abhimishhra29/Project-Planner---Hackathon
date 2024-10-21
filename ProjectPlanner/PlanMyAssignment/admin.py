from django.contrib import admin
from .models import Project, Task, Step, Part, Grading

class ProjectAdmin(admin.ModelAdmin):
    list_display = ('project_name', 'project_deadline')

class TaskAdmin(admin.ModelAdmin):
    list_display = ('project', 'task_id', 'task_name', 'efforts', 'deadline')

class StepAdmin(admin.ModelAdmin):
    list_display = ('task', 'step_description')

class GradingAdmin(admin.ModelAdmin):
    list_display = ('grader_name',)

class PartAdmin(admin.ModelAdmin):
    list_display = ('grading', 'part_id', 'part_name', 'part_review', 'part_student_score', 'part_score')

# Register your models here.
admin.site.register(Project, ProjectAdmin)
admin.site.register(Task, TaskAdmin)
admin.site.register(Step, StepAdmin)
admin.site.register(Grading, GradingAdmin)
admin.site.register(Part, PartAdmin)
