import axios from 'axios';
import { authService } from './authService';

const api = axios.create({
    baseURL: 'http://localhost:8000',
    headers: {
        'Content-Type': 'application/json',
    },
    withCredentials: true,
    timeout: 10000, // Add timeout of 10 seconds
});

// Initialize authorization header from stored token
const token = localStorage.getItem('token');
if (token) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
}

// Add request interceptor for auth token
api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

// Add response interceptor for token refresh and error handling
api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config;

        // Handle network errors or server unreachable
        if (!error.response) {
            const errorMessage = error.code === 'ECONNABORTED'
                ? 'Request timed out. Please check your connection and try again.'
                : 'Unable to connect to the server. Please check if the server is running and try again.';
            return Promise.reject(new Error(errorMessage));
        }

        // Handle 401 and token refresh
        if (error.response.status === 401 && !originalRequest._retry) {
            originalRequest._retry = true;

            try {
                const newToken = await authService.refreshToken();
                originalRequest.headers.Authorization = `Bearer ${newToken}`;
                api.defaults.headers.common['Authorization'] = `Bearer ${newToken}`;
                return api(originalRequest);
            } catch (refreshError) {
                authService.logout();
                window.location.href = '/login';
                return Promise.reject(refreshError);
            }
        }

        // Handle other error responses
        const errorMessage = error.response.data?.detail || 
                           error.response.data?.error ||
                           error.response.data?.message ||
                           'An error occurred. Please try again.';
        
        return Promise.reject(new Error(errorMessage));
    }
);

export default api;