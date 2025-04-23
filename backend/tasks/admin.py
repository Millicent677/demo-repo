from django.contrib import admin
from .models import Task, Project

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_by', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'priority', 'due_date', 'created_by', 'project')
    list_filter = ('status', 'priority', 'created_at', 'project')
    search_fields = ('title', 'description')
    readonly_fields = ('created_at', 'updated_at')
