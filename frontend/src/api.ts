import axios from 'axios';

// Use the localtunnel URL for the backend API
const API_BASE_URL = 'https://toqa-ai-backend.loca.lt/api/v1';

// Create axios instance with default config
export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    'Bypass-Tunnel-Reminder': 'true' // Bypass localtunnel warning page
  },
});

// Auth interceptor (if needed later)
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const ChatService = {
  // Use the hybrid chat endpoint by default for the platform
  sendMessage: async (message: string, conversationId?: string) => {
    try {
      const response = await api.post('/chat/hybrid', {
        message,
        conversation_id: conversationId,
      });
      return response.data;
    } catch (error) {
      console.error('Chat API Error:', error);
      throw error;
    }
  }
};

export const DatabaseService = {
  connect: async (data: any) => {
    try {
      const response = await api.post('/connections', data);
      return response.data;
    } catch (error) {
      console.error('Database connection Error:', error);
      throw error;
    }
  }
};
