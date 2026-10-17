/** Типы ответов backend (см. backend/app/schemas.py). */

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user_id: number;
  full_name: string;
  position: string;
  email: string | null;
}

export interface Employee {
  id: number;
  login: string;
  full_name: string;
  birth_date: string | null;
  phone: string | null;
  email: string | null;
  position: string | null;
  hire_date: string | null;
  department_name: string | null;
  is_active: boolean;
}

export interface WantedRow {
  id: number;
  plate: string;
  model: string | null;
  color: string | null;
  status: string;
  fix_time: string | null;
  fix_date: string | null;
  fix_address: string | null;
  employee_name: string | null;
  reaction_status: string | null;
  found_status: string | null;
}

export interface AlertRow {
  id: number;
  vehicle_plate: string;
  alert_date: string;
  alert_time: string;
  address: string;
  camera_id: number | null;
  reaction_status: string | null;
  found_status: string | null;
  wanted_status: string | null;
  is_viewed: boolean;
}

export interface PendingAlert {
  id: number;
  plate: string;
  address: string;
  date: string;
  time: string;
}

/** Сообщение WebSocket «обнаружен разыскиваемый автомобиль». */
export interface DetectionPayload {
  alert_id: number;
  plate: string;
  address: string;
  date: string;
  time: string;
  /** Номер камеры на карте (1-15). У напоминаний о старых оповещениях его нет. */
  camera_number: number | null;
}

export type HistoryPeriod = 'today' | 'week' | 'month' | 'all';
export type ExportFormat = 'docx' | 'xlsx';
