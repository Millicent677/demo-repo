from django.shortcuts import render
from rest_framework import viewsets, status, generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Task, Project
from .serializers import TaskSerializer, ProjectSerializer, UserSerializer, RegisterSerializer
from .notifications import notify_task_assigned, notify_task_updated, notify_project_updated

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': UserSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Project.objects.filter(members=self.request.user) | Project.objects.filter(created_by=self.request.user)

    def perform_create(self, serializer):
        project = serializer.save(created_by=self.request.user)
        project.members.add(self.request.user)

    def perform_update(self, serializer):
        project = serializer.save()
        notify_project_updated(project.id, self.request.user.id)

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def add_member(self, request, pk=None):
        project = self.get_object()
        user_id = request.data.get('user_id')
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                project.members.add(user)
                notify_project_updated(project.id, self.request.user.id)
                return Response({'status': 'member added'})
            except User.DoesNotExist:
                return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'error': 'user_id required'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def remove_member(self, request, pk=None):
        project = self.get_object()
        user_id = request.data.get('user_id')
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                if user == project.created_by:
                    return Response(
                        {'error': 'Cannot remove project owner'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                project.members.remove(user)
                notify_project_updated(project.id, self.request.user.id)
                return Response({'status': 'member removed'})
            except User.DoesNotExist:
                return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'error': 'user_id required'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        project = self.get_object()
        members = project.members.all()
        serializer = UserSerializer(members, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def tasks(self, request, pk=None):
        project = self.get_object()
        tasks = project.tasks.all()
        serializer = TaskSerializer(tasks, many=True)
        return Response(serializer.data)

class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Task.objects.filter(
            assignees=self.request.user
        ) | Task.objects.filter(
            created_by=self.request.user
        ) | Task.objects.filter(
            project__members=self.request.user
        )
        
        project_id = self.request.query_params.get('project', None)
        status_param = self.request.query_params.get('status', None)
        priority = self.request.query_params.get('priority', None)

        if project_id:
            queryset = queryset.filter(project_id=project_id)
        if status_param:
            queryset = queryset.filter(status=status_param)
        if priority:
            queryset = queryset.filter(priority=priority)
            
        return queryset.distinct()

    def perform_create(self, serializer):
        try:
            task = serializer.save(created_by=self.request.user)
            if task.assignees.exists():
                notify_task_assigned(task.id, self.request.user.id)
            return Response(TaskSerializer(task).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def perform_update(self, serializer):
        try:
            task = serializer.save()
            notify_task_updated(task.id, self.request.user.id)
            return Response(TaskSerializer(task).data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        task = self.get_object()
        user_id = request.data.get('user_id')
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                task.assignees.add(user)
                notify_task_assigned(task.id, self.request.user.id)
                return Response({'status': 'assignee added'})
            except User.DoesNotExist:
                return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'error': 'user_id required'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def remove_assignee(self, request, pk=None):
        task = self.get_object()
        user_id = request.data.get('user_id')
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                task.assignees.remove(user)
                notify_task_updated(task.id, self.request.user.id)
                return Response({'status': 'assignee removed'})
            except User.DoesNotExist:
                return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'error': 'user_id required'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def my_tasks(self, request):
        tasks = Task.objects.filter(assignees=request.user)
        serializer = self.get_serializer(tasks, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def assigned(self, request):
        tasks = Task.objects.filter(assignees=request.user)
        serializer = self.get_serializer(tasks, many=True)
        return Response(serializer.data)
