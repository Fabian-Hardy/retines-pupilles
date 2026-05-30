import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import {
  ApiError,
  type CurrentUser,
  type LoginRequest,
  loginUser,
  readCurrentUser,
} from "./api";

type SessionStatus = "loading" | "authenticated" | "unauthenticated";

type SessionContextValue = {
  status: SessionStatus;
  user: CurrentUser | null;
  login: (payload: LoginRequest) => Promise<void>;
  logout: () => void;
};

const ACCESS_TOKEN_STORAGE_KEY = "retines-pupilles.access-token";
const SessionContext = createContext<SessionContextValue | null>(null);

function readStoredAccessToken(): string | null {
  try {
    return window.sessionStorage.getItem(ACCESS_TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

function storeAccessToken(accessToken: string): void {
  try {
    window.sessionStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, accessToken);
  } catch {
    return;
  }
}

function clearStoredAccessToken(): void {
  try {
    window.sessionStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
  } catch {
    return;
  }
}

export function SessionProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<SessionStatus>("loading");
  const [user, setUser] = useState<CurrentUser | null>(null);

  useEffect(() => {
    let isCurrent = true;
    const accessToken = readStoredAccessToken();

    if (!accessToken) {
      setStatus("unauthenticated");
      return () => {
        isCurrent = false;
      };
    }

    const currentAccessToken = accessToken;

    async function restoreSession(): Promise<void> {
      try {
        const currentUser = await readCurrentUser(currentAccessToken);

        if (isCurrent) {
          setUser(currentUser);
          setStatus("authenticated");
        }
      } catch (error) {
        clearStoredAccessToken();

        if (isCurrent) {
          setUser(null);
          setStatus("unauthenticated");
        }
      }
    }

    void restoreSession();

    return () => {
      isCurrent = false;
    };
  }, []);

  const login = useCallback(async (payload: LoginRequest) => {
    const token = await loginUser(payload);
    const currentUser = await readCurrentUser(token.access_token);

    storeAccessToken(token.access_token);
    setUser(currentUser);
    setStatus("authenticated");
  }, []);

  const logout = useCallback(() => {
    clearStoredAccessToken();
    setUser(null);
    setStatus("unauthenticated");
  }, []);

  const value = useMemo<SessionContextValue>(
    () => ({
      status,
      user,
      login,
      logout,
    }),
    [login, logout, status, user],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionContextValue {
  const value = useContext(SessionContext);

  if (value === null) {
    throw new Error("useSession must be used within SessionProvider");
  }

  return value;
}

export function isAuthenticationError(error: unknown): boolean {
  return error instanceof ApiError && (error.status === 400 || error.status === 401);
}
