import AsyncStorage from '@react-native-async-storage/async-storage';

const STORAGE_KEY = 'avtodozor.session';

export interface SessionUser {
  id: number;
  fullName: string;
  position: string;
  email: string | null;
}

export interface Session {
  token: string;
  user: SessionUser;
}

export async function saveSession(session: Session): Promise<void> {
  try {
    await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(session));
  } catch {
    // без сохранения придётся входить заново при следующем запуске
  }
}

export async function loadSession(): Promise<Session | null> {
  try {
    const raw = await AsyncStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as Session;
    if (parsed && typeof parsed.token === 'string' && parsed.user && typeof parsed.user.id === 'number') {
      return parsed;
    }
  } catch {
    // повреждённые данные считаем отсутствием сессии
  }
  return null;
}

export async function clearSession(): Promise<void> {
  try {
    await AsyncStorage.removeItem(STORAGE_KEY);
  } catch {
    // ничего страшного
  }
}
