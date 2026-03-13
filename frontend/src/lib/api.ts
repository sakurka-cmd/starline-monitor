import type {
  User,
  LoginRequest,
  RegisterRequest,
  AuthResponse,
  Device,
  DeviceState,
  CreateDeviceRequest,
  DeviceStats,
  ServiceType,
  MaintenanceRecord,
  CreateMaintenanceRequest,
  UpdateMaintenanceRequest,
  UpcomingMaintenance,
} from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class ApiClient {
  private getToken(): string | null {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem('token');
  }

  private setToken(token: string): void {
    if (typeof window === 'undefined') return;
    localStorage.setItem('token', token);
  }

  private removeToken(): void {
    if (typeof window === 'undefined') return;
    localStorage.removeItem('token');
  }

  private async fetch<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const token = this.getToken();
    
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
      ...options.headers,
    };

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  // Auth
  async login(data: LoginRequest): Promise<AuthResponse> {
    const response = await this.fetch<AuthResponse>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    this.setToken(response.token);
    return response;
  }

  async register(data: RegisterRequest): Promise<AuthResponse> {
    const response = await this.fetch<AuthResponse>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    this.setToken(response.token);
    return response;
  }

  async getMe(): Promise<User> {
    return this.fetch<User>('/api/auth/me');
  }

  logout(): void {
    this.removeToken();
  }

  // Devices
  async getDevices(): Promise<Device[]> {
    return this.fetch<Device[]>('/api/devices');
  }

  async getDevice(id: string): Promise<Device> {
    return this.fetch<Device>(`/api/devices/${id}`);
  }

  async getDeviceLatest(id: string): Promise<Device> {
    return this.fetch<Device>(`/api/devices/${id}/latest`);
  }

  async createDevice(data: CreateDeviceRequest): Promise<Device> {
    return this.fetch<Device>('/api/devices', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async deleteDevice(id: string): Promise<void> {
    await this.fetch(`/api/devices/${id}`, {
      method: 'DELETE',
    });
  }

  async getDeviceState(id: string, hours: number = 24): Promise<DeviceState[]> {
    return this.fetch<DeviceState[]>(`/api/devices/${id}/state?hours=${hours}`);
  }

  async getDeviceStats(id: string, days: number = 7): Promise<DeviceStats> {
    return this.fetch<DeviceStats>(`/api/devices/${id}/stats?days=${days}`);
  }

  // Service Types
  async getServiceTypes(): Promise<ServiceType[]> {
    return this.fetch<ServiceType[]>('/api/service-types');
  }

  // Maintenance
  async getMaintenance(deviceId: string): Promise<MaintenanceRecord[]> {
    return this.fetch<MaintenanceRecord[]>(`/api/devices/${deviceId}/maintenance`);
  }

  async createMaintenance(deviceId: string, data: CreateMaintenanceRequest): Promise<MaintenanceRecord> {
    return this.fetch<MaintenanceRecord>(`/api/devices/${deviceId}/maintenance`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateMaintenance(deviceId: string, maintenanceId: string, data: UpdateMaintenanceRequest): Promise<MaintenanceRecord> {
    return this.fetch<MaintenanceRecord>(`/api/devices/${deviceId}/maintenance/${maintenanceId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteMaintenance(deviceId: string, maintenanceId: string): Promise<void> {
    await this.fetch(`/api/devices/${deviceId}/maintenance/${maintenanceId}`, {
      method: 'DELETE',
    });
  }

  async getUpcomingMaintenance(deviceId: string): Promise<UpcomingMaintenance[]> {
    return this.fetch<UpcomingMaintenance[]>(`/api/devices/${deviceId}/maintenance/upcoming`);
  }
}

export const api = new ApiClient();
export { ApiClient };
