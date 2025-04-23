import { io } from 'socket.io-client';

class NotificationService {
    constructor() {
        this.socket = null;
        this.subscribers = new Set();
        this.notifications = this.loadNotificationsFromStorage() || [];
        this.connectPromise = null;
        this.maxRetries = 3;
        this.retryDelay = 2000;
        this.retryCount = 0;
    }

    loadNotificationsFromStorage() {
        const stored = localStorage.getItem('notifications');
        return stored ? JSON.parse(stored) : null;
    }

    saveNotificationsToStorage() {
        localStorage.setItem('notifications', JSON.stringify(this.notifications.slice(0, 50)));
    }

    async connect() {
        if (this.socket?.connected) return;
        if (this.connectPromise) return this.connectPromise;

        this.connectPromise = new Promise((resolve, reject) => {
            const token = localStorage.getItem('token');
            if (!token) {
                reject(new Error('No authentication token found'));
                return;
            }

            this.socket = io('http://localhost:8001', {
                withCredentials: true,
                auth: {
                    token: token
                },
                transports: ['websocket'],
                upgrade: false,
                reconnection: true,
                reconnectionDelay: this.retryDelay,
                reconnectionAttempts: this.maxRetries
            });

            this.socket.on('connect', () => {
                console.log('Connected to notification server');
                this.retryCount = 0;
                resolve(this.socket);
            });

            this.socket.on('notification', (notification) => {
                this.addNotification(notification);
            });

            this.socket.on('connect_error', (error) => {
                console.error('Socket connection error:', error);
                this.handleConnectionError(error, reject);
            });

            this.socket.on('disconnect', () => {
                console.log('Disconnected from notification server');
                this.connectPromise = null;
            });

            this.socket.on('notifications_cleared', () => {
                this.notifications = [];
                this.saveNotificationsToStorage();
                this.notifySubscribers();
            });
        });

        return this.connectPromise;
    }

    addNotification(notification) {
        // Add timestamp if not present
        const notificationWithTimestamp = {
            ...notification,
            timestamp: notification.timestamp || new Date().toISOString()
        };
        
        // Add to front of array and limit to 50 notifications
        this.notifications.unshift(notificationWithTimestamp);
        if (this.notifications.length > 50) {
            this.notifications = this.notifications.slice(0, 50);
        }
        
        this.saveNotificationsToStorage();
        this.notifySubscribers(notificationWithTimestamp);
    }

    handleConnectionError(error, reject) {
        this.retryCount++;
        if (this.retryCount >= this.maxRetries) {
            this.subscribers.forEach(callback => 
                callback({ type: 'CONNECTION_ERROR', message: 'Failed to connect to notification service' })
            );
            reject(error);
            return;
        }
        
        setTimeout(() => {
            this.connect().catch(console.error);
        }, this.retryDelay * this.retryCount);
    }

    subscribe(callback) {
        this.subscribers.add(callback);
        return () => this.subscribers.delete(callback);
    }

    notifySubscribers(notification = null) {
        this.subscribers.forEach(callback => callback(notification));
    }

    disconnect() {
        if (this.socket) {
            this.socket.disconnect();
            this.socket = null;
        }
        this.subscribers.clear();
        this.connectPromise = null;
    }

    async markAsRead(notificationId) {
        this.notifications = this.notifications.map(notification => 
            notification.id === notificationId 
                ? { ...notification, read: true }
                : notification
        );
        this.saveNotificationsToStorage();
        this.notifySubscribers();
        
        if (this.socket?.connected) {
            await this.socket.emit('mark_as_read', { notificationId });
        }
    }

    async markAllAsRead() {
        this.notifications = this.notifications.map(notification => ({
            ...notification,
            read: true
        }));
        this.saveNotificationsToStorage();
        this.notifySubscribers();
        
        if (this.socket?.connected) {
            await this.socket.emit('mark_all_as_read');
        }
    }

    getNotifications() {
        return this.notifications;
    }

    getUnreadCount() {
        return this.notifications.filter(n => !n.read).length;
    }

    clearNotifications() {
        this.notifications = [];
        this.saveNotificationsToStorage();
        this.notifySubscribers();
        
        if (this.socket?.connected) {
            this.socket.emit('clear_notifications');
        }
    }
}

export const notificationService = new NotificationService();