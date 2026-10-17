import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import * as api from '../api';
import { getErrorMessage, setAuthToken, setUnauthorizedHandler } from '../api/client';
import { clearSession, loadSession, saveSession, SessionUser } from '../session';
import { loadServerHost } from '../server';
import { notify } from '../utils/notify';

type Status = 'loading' | 'signedOut' | 'signedIn';

interface AuthContextValue {
  status: Status;
  user: SessionUser | null;
  token: string | null;
  signIn: (login: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<Status>('loading');
  const [user, setUser] = useState<SessionUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const statusRef = useRef<Status>('loading');
  statusRef.current = status;

  const finishSignOut = useCallback(async () => {
    setAuthToken(null);
    setToken(null);
    setUser(null);
    setStatus('signedOut');
    await clearSession();
  }, []);

  const signOut = useCallback(async () => {
    await finishSignOut();
  }, [finishSignOut]);

  // токен истёк: сервер ответил 401
  useEffect(() => {
    setUnauthorizedHandler(() => {
      if (statusRef.current === 'signedIn') {
        notify('Сессия истекла. Войдите заново', true);
        finishSignOut();
      }
    });
    return () => setUnauthorizedHandler(null);
  }, [finishSignOut]);

  // при запуске: адрес сервера и сохранённая сессия
  useEffect(() => {
    let cancelled = false;
    (async () => {
      await loadServerHost();
      const session = await loadSession();
      if (!session) {
        if (!cancelled) {
          setStatus('signedOut');
        }
        return;
      }
      setAuthToken(session.token);
      try {
        const profile = await api.fetchProfile(); // проверяем, что токен ещё действует
        if (cancelled) {
          return;
        }
        setToken(session.token);
        setUser({ ...session.user, fullName: profile.full_name, email: profile.email });
        setStatus('signedIn');
      } catch {
        // токен недействителен или сервер недоступен: показываем вход
        setAuthToken(null);
        if (!cancelled) {
          setStatus('signedOut');
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const signIn = useCallback(async (login: string, password: string) => {
    try {
      const data = await api.login(login, password);
      const sessionUser: SessionUser = {
        id: data.user_id,
        fullName: data.full_name,
        position: data.position,
        email: data.email,
      };
      setAuthToken(data.access_token);
      await saveSession({ token: data.access_token, user: sessionUser });
      setToken(data.access_token);
      setUser(sessionUser);
      setStatus('signedIn');
    } catch (error) {
      throw new Error(getErrorMessage(error));
    }
  }, []);

  const value = useMemo(
    () => ({ status, user, token, signIn, signOut }),
    [status, user, token, signIn, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth нужно вызывать внутри AuthProvider');
  }
  return ctx;
}
