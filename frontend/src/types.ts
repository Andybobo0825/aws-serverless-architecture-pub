export type Role = 'admin' | 'teacher' | 'student';

export interface Me {
  username: string;
  role: Role;
  status: 'active' | 'inactive';
  classes: string[];
  device_bound: boolean;
}

export interface WeekSummary {
  week_id: string;
  week_number: number;
  title: string;
  class_id?: string | null;
  is_open?: boolean;
}
