from rest_framework import serializers
from .models import Project, Task, Step, Grading

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

# class PartSerializer(serializers.ModelSerializer):
    
#     class Meta:
#         model = Part
#         fields = ['part_id', 'part_name', 'part_review', 'part_student_score', 'part_score']

#     def create(self, validated_data):
#         part = Part.objects.create(**validated_data)
#         return part

class GradingSerializer(serializers.ModelSerializer):
    # parts = PartSerializer(many=True)

    class Meta:
        model = Grading
        fields = ['grader_name', 'description']

    # def create(self, validated_data):
    #     parts_data = validated_data.pop('parts')
    #     grading = Grading.objects.create(**validated_data)
    #     for part_data in parts_data:
    #         Part.objects.create(grading=grading, **part_data)
    #     return grading

