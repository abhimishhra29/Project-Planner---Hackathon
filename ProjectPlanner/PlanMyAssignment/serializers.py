from rest_framework import serializers
from .models import Project, Task, Step

class StepSerializer(serializers.ModelSerializer):
    class Meta:
        model = Step
        fields = ['step_description']

class TaskSerializer(serializers.ModelSerializer):
    steps = StepSerializer(many=True)

    class Meta:
        model = Task
        fields = ['task_id', 'task_name', 'efforts', 'deadline', 'steps']

    def create(self, validated_data):
        steps_data = validated_data.pop('steps')
        task = Task.objects.create(**validated_data)
        for step_data in steps_data:
            Step.objects.create(task=task, **step_data)
        return task

class ProjectSerializer(serializers.ModelSerializer):
    tasks = TaskSerializer(many=True)

    class Meta:
        model = Project
        fields = ['project_name', 'project_deadline', 'tasks']

    def create(self, validated_data):
        tasks_data = validated_data.pop('tasks')
        project = Project.objects.create(**validated_data)
        for task_data in tasks_data:
            steps_data = task_data.pop('steps')
            task = Task.objects.create(project=project, **task_data)
            for step_data in steps_data:
                Step.objects.create(task=task, **step_data)
        return project
