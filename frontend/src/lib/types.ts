// Auth Types
export interface User {
  id: string;
  email: string;
  name: string;
  created_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name: string;
}

export interface AuthResponse {
  token: string;
  user: User;
}

// Device Types
export interface DeviceState {
  id: string;
  device_id: string;
  arm_state: boolean | null;
  ign_state: boolean | null;
  temp_inner: number | null;
  temp_engine: number | null;
  balance: number | null;
  mileage: number | null;
  fuel_litres: number | null;
  motohrs: number | null;
  speed: number | null;
  battery_voltage: number | null;
  timestamp: string;
  created_at: string;
}

export interface Device {
  id: string;
  user_id: string;
  name: string;
  app_id: string;
  app_secret: string;
  starline_login: string;
  starline_password: string;
  created_at: string;
  updated_at: string;
  latest_state?: DeviceState | null;
}

export interface CreateDeviceRequest {
  name: string;
  app_id: string;
  app_secret: string;
  starline_login: string;
  starline_password: string;
}

// Statistics Types
export interface DeviceStats {
  mileage_diff: number;
  motohrs_diff: number;
  fuel_avg: number;
  fuel_min: number;
  fuel_max: number;
}

// Service Types
export interface ServiceType {
  id: string;
  name: string;
  description: string;
  interval_mileage: number | null;
  interval_motohrs: number | null;
  interval_months: number | null;
}

export interface MaintenanceRecord {
  id: string;
  device_id: string;
  service_type_id: string;
  service_type?: ServiceType;
  description: string;
  mileage_at_service: number;
  motohrs_at_service: number;
  service_date: string;
  next_service_mileage: number | null;
  next_service_motohrs: number | null;
  next_service_date: string | null;
  cost: number | null;
  notes: string | null;
  created_at: string;
}

export interface CreateMaintenanceRequest {
  service_type_id: string;
  description: string;
  mileage_at_service: number;
  motohrs_at_service: number;
  service_date: string;
  next_service_mileage?: number;
  next_service_motohrs?: number;
  cost?: number;
  notes?: string;
}

export interface UpdateMaintenanceRequest {
  service_type_id?: string;
  description?: string;
  mileage_at_service?: number;
  motohrs_at_service?: number;
  service_date?: string;
  next_service_mileage?: number;
  next_service_motohrs?: number;
  cost?: number;
  notes?: string;
}

export interface UpcomingMaintenance {
  id: string;
  device_id: string;
  service_type: ServiceType;
  last_service?: MaintenanceRecord;
  current_mileage: number;
  current_motohrs: number;
  next_service_mileage: number | null;
  next_service_motohrs: number | null;
  mileage_remaining: number | null;
  motohrs_remaining: number | null;
  status: 'ok' | 'warning' | 'overdue';
}

// API Response Types
export interface ApiError {
  detail: string;
}
