"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from tasks.views import TaskViewSet, ProjectViewSet, RegisterView
from django.contrib.auth.models import User
from rest_framework import generics, permissions
from rest_framework.response import Response

class UserList(generics.ListAPIView):
    queryset = User.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return User.objects.filter(is_active=True).exclude(id=self.request.user.id)
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        data = [{'id': user.id, 'username': user.username, 'email': user.email} for user in queryset]
        return Response(data)

router = DefaultRouter()
router.register(r'tasks', TaskViewSet, basename='task')
router.register(r'projects', ProjectViewSet, basename='project')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/register/', RegisterView.as_view(), name='register'),
    path('api/users/', UserList.as_view(), name='user-list'),
    path('api-auth/', include('rest_framework.urls')),
]
