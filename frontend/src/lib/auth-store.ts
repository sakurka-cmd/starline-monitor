import { create } from 'zustand';
import type { User } from './types';
import { api } from './api';

interface AuthState {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  isInitialized: boolean;
  error: string | null;
  
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
  logout: () => void;
  checkAuth: () => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: null,
  isLoading: false,
  isInitialized: false,
  error: null,

  login: async (email: string, password: string) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.login({ email, password });
      set({ 
        user: response.user, 
        token: response.token, 
        isLoading: false,
        isInitialized: true,
      });
    } catch (error) {
      set({ 
        error: error instanceof Error ? error.message : 'Ошибка входа', 
        isLoading: false 
      });
      throw error;
    }
  },

  register: async (email: string, password: string, name: string) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.register({ email, password, name });
      set({ 
        user: response.user, 
        token: response.token, 
        isLoading: false,
        isInitialized: true,
      });
    } catch (error) {
      set({ 
        error: error instanceof Error ? error.message : 'Ошибка регистрации', 
        isLoading: false 
      });
      throw error;
    }
  },

  logout: () => {
    api.logout();
    set({ user: null, token: null, isInitialized: true });
  },

  checkAuth: async () => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    if (!token) {
      set({ isInitialized: true });
      return;
    }

    set({ isLoading: true });
    try {
      const user = await api.getMe();
      set({ user, token, isLoading: false, isInitialized: true });
    } catch {
      api.logout();
      set({ user: null, token: null, isLoading: false, isInitialized: true });
    }
  },

  clearError: () => set({ error: null }),
}));
