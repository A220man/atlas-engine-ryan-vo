import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { api, User } from "@/api/client";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: () => Promise<void>;
  logout: () => Promise<void>;
  setUser: (user: User | null) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const initAuth = async () => {
      try {
        const userData = await api.getMe();
        setUser(userData);
      } catch {
        setUser(null);
      }
      setLoading(false);
    };
    initAuth();
  }, []);

  const login = async () => {
    const { authorization_url, state, nonce, code_verifier } = await api.login();
    sessionStorage.setItem("oidc_state", state);
    sessionStorage.setItem("oidc_nonce", nonce);
    sessionStorage.setItem("oidc_code_verifier", code_verifier);
    window.location.href = authorization_url;
  };

  const logout = async () => {
    await api.logout();
    setUser(null);
    window.location.href = "/login";
  };

  const setAuthenticatedUser = (userData: User | null) => {
    setUser(userData);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, setUser: setAuthenticatedUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}