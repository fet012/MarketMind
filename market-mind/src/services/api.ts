import axios from 'axios';
import { Platform } from 'react-native';

// The local Wi-Fi IP address provided by the user
export const BACKEND_URL = 'http://10.208.140.216:8000';

const api = axios.create({
  baseURL: BACKEND_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const fetchSummary = async (userId: string = 'default') => {
  try {
    const response = await api.get(`/summary?user_id=${userId}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching summary:', error);
    throw error;
  }
};

export const fetchTransactions = async (userId: string = 'default', limit: number = 50) => {
  try {
    const response = await api.get(`/transactions?user_id=${userId}&limit=${limit}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching transactions:', error);
    throw error;
  }
};

export const sendChatMessage = async (message: string, userId: string = 'default') => {
  try {
    const response = await api.post('/chat', {
      message,
      user_id: userId,
    });
    return response.data;
  } catch (error) {
    console.error('Error sending chat:', error);
    throw error;
  }
};

export const sendVoiceMessage = async (audioUri: string, userId: string = 'default') => {
  try {
    const formData = new FormData();
    
    // We need to pass the file to the FormData
    const filename = audioUri.split('/').pop() || 'audio.m4a';
    const match = /\.(\w+)$/.exec(filename);
    const type = match ? `audio/${match[1]}` : 'audio/m4a';

    // React Native FormData format for files
    formData.append('audio', {
      uri: Platform.OS === 'ios' ? audioUri.replace('file://', '') : audioUri,
      name: filename,
      type,
    } as any);

    const response = await axios.post(`${BACKEND_URL}/voice?user_id=${userId}`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      responseType: 'blob', // Because /voice returns a WAV audio file
    });

    return response.data;
  } catch (error) {
    console.error('Error sending voice message:', error);
    throw error;
  }
};

export default api;
