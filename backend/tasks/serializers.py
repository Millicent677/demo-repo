from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Task, Project

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password')

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']

class ProjectSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()
    task_count = serializers.SerializerMethodField()
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = Project
        fields = [
            'id', 'name', 'description', 'status', 'priority',
            'start_date', 'due_date', 'created_at', 'updated_at',
            'created_by', 'created_by_username', 'members',
            'member_count', 'task_count'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by']

    def get_member_count(self, obj):
        return obj.members.count()

    def get_task_count(self, obj):
        return obj.tasks.count()

class TaskSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    assignee_details = UserSerializer(source='assignees', many=True, read_only=True)

    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'status', 'priority',
            'created_at', 'updated_at', 'due_date', 'assignees',
            'created_by', 'created_by_username', 'project', 'project_name',
            'assignee_details'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by']