import socketio
import asyncio
import jwt
from django.conf import settings
from .models import Task, Project

# Create Socket.IO server with asyncio
sio = socketio.AsyncServer(
    cors_allowed_origins=['http://localhost:5173', 'http://127.0.0.1:5173'],  # Match Vite's default dev server URLs
    async_mode='asgi',
    logger=True,
    engineio_logger=True
)

# Client sessions storage
sessions = {}

@sio.event
async def connect(sid, environ):
    try:
        auth = environ.get('HTTP_AUTHORIZATION', '') or environ.get('QUERY_STRING', '')
        if 'auth' in environ:
            auth_data = environ['auth']
            if isinstance(auth_data, dict) and 'token' in auth_data:
                token = auth_data['token']
                try:
                    # Verify and decode the JWT token
                    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
                    user_id = payload.get('user_id')
                    
                    if user_id:
                        # Store the user's session
                        if user_id not in sessions:
                            sessions[user_id] = set()
                        sessions[user_id].add(sid)
                        return True
                except jwt.InvalidTokenError:
                    return False
        return False
    except Exception as e:
        print(f"Connection error: {str(e)}")
        return False

@sio.event
async def disconnect(sid):
    if sid in sessions:
        del sessions[sid]

def get_user_sids(user_id):
    return list(sessions.get(user_id, set()))

async def notify_users(user_ids, notification_data):
    for user_id in user_ids:
        sids = get_user_sids(user_id)
        tasks = [sio.emit('notification', notification_data, room=sid) for sid in sids]
        if tasks:
            await asyncio.gather(*tasks)

async def notify_task_assigned(task_id, assigned_by_id):
    try:
        task = Task.objects.select_related('project').get(id=task_id)
        assignee_ids = list(task.assignees.values_list('id', flat=True))
        
        notification_data = {
            'id': f'task_assigned_{task_id}_{assigned_by_id}',
            'type': 'TASK_ASSIGNED',
            'message': f'You have been assigned to task: {task.title}',
            'timestamp': task.updated_at.isoformat(),
            'data': {
                'task_id': task_id,
                'project_id': task.project_id if task.project else None
            },
            'read': False
        }
        
        await notify_users(assignee_ids, notification_data)
    except Task.DoesNotExist:
        pass

async def notify_task_updated(task_id, updated_by_id):
    try:
        task = Task.objects.select_related('project').get(id=task_id)
        user_ids = list(task.assignees.values_list('id', flat=True))
        if task.created_by_id not in user_ids:
            user_ids.append(task.created_by_id)
            
        notification_data = {
            'id': f'task_updated_{task_id}_{updated_by_id}',
            'type': 'TASK_UPDATED',
            'message': f'Task updated: {task.title}',
            'timestamp': task.updated_at.isoformat(),
            'data': {
                'task_id': task_id,
                'project_id': task.project_id if task.project else None
            },
            'read': False
        }
        
        await notify_users(user_ids, notification_data)
    except Task.DoesNotExist:
        pass

async def notify_project_updated(project_id, updated_by_id):
    try:
        project = Project.objects.get(id=project_id)
        member_ids = list(project.members.values_list('id', flat=True))
        
        notification_data = {
            'id': f'project_updated_{project_id}_{updated_by_id}',
            'type': 'PROJECT_UPDATED',
            'message': f'Project updated: {project.name}',
            'timestamp': project.updated_at.isoformat(),
            'data': {
                'project_id': project_id
            },
            'read': False
        }
        
        await notify_users(member_ids, notification_data)
    except Project.DoesNotExist:
        pass

async def notify_deadline_approaching(task_id):
    """Send notification when a task deadline is approaching"""
    try:
        task = Task.objects.select_related('project').get(id=task_id)
        user_ids = list(task.assignees.values_list('id', flat=True))
        
        notification_data = {
            'id': f'deadline_{task_id}',
            'type': 'DEADLINE',
            'message': f'Deadline approaching for task: {task.title}',
            'timestamp': task.updated_at.isoformat(),
            'data': {
                'task_id': task_id,
                'project_id': task.project_id if task.project else None,
                'due_date': task.due_date.isoformat() if task.due_date else None
            },
            'read': False
        }
        
        await notify_users(user_ids, notification_data)
    except Task.DoesNotExist:
        pass