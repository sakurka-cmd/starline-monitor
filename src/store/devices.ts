// Device Store using Zustand
import { create } from 'zustand';
import type { StarLineDevice, DeviceWithState, HistoryResponse, CreateDeviceRequest } from '@/lib/types';
import api from '@/lib/api';

interface DeviceState {
  devices: StarLineDevice[];
  currentDevice: DeviceWithState | null;
  history: HistoryResponse | null;
  isLoading: boolean;
  isHistoryLoading: boolean;
  error: string | null;
  
  // Actions
  fetchDevices: () => Promise<void>;
  fetchDeviceState: (deviceId: string) => Promise<void>;
  fetchDeviceHistory: (deviceId: string, start?: string, end?: string) => Promise<void>;
  addDevice: (data: CreateDeviceRequest) => Promise<StarLineDevice>;
  deleteDevice: (deviceId: string) => Promise<void>;
  clearCurrentDevice: () => void;
  clearError: () => void;
}

export const useDeviceStore = create<DeviceState>((set, get) => ({
  devices: [],
  currentDevice: null,
  history: null,
  isLoading: false,
  isHistoryLoading: false,
  error: null,

  fetchDevices: async () => {
    set({ isLoading: true, error: null });
    try {
      const devices = await api.getDevices();
      set({ devices, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch devices',
        isLoading: false,
      });
    }
  },

  fetchDeviceState: async (deviceId: string) => {
    set({ isLoading: true, error: null });
    try {
      const currentDevice = await api.getDeviceState(deviceId);
      set({ currentDevice, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch device state',
        isLoading: false,
      });
    }
  },

  fetchDeviceHistory: async (deviceId: string, start?: string, end?: string) => {
    set({ isHistoryLoading: true, error: null });
    try {
      const history = await api.getDeviceHistory(deviceId, { start, end });
      set({ history, isHistoryLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch device history',
        isHistoryLoading: false,
      });
    }
  },

  addDevice: async (data: CreateDeviceRequest) => {
    set({ isLoading: true, error: null });
    try {
      const device = await api.createDevice(data);
      const { devices } = get();
      set({
        devices: [...devices, device],
        isLoading: false,
      });
      return device;
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to add device',
        isLoading: false,
      });
      throw error;
    }
  },

  deleteDevice: async (deviceId: string) => {
    set({ isLoading: true, error: null });
    try {
      await api.deleteDevice(deviceId);
      const { devices } = get();
      set({
        devices: devices.filter((d) => d.id !== deviceId),
        isLoading: false,
      });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to delete device',
        isLoading: false,
      });
      throw error;
    }
  },

  clearCurrentDevice: () => set({ currentDevice: null, history: null }),

  clearError: () => set({ error: null }),
}));
