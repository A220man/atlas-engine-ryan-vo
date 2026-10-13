import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "@/api/client";
import { useAuth } from "@/hooks/useAuth";
import { Loader2, CheckCircle, AlertCircle } from "lucide-react";

export default function Callback() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { setUser } = useAuth();
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const handleCallback = async () => {
      const code = searchParams.get("code");
      const state = searchParams.get("state");
      const storedState = sessionStorage.getItem("oidc_state");
      const codeVerifier = sessionStorage.getItem("oidc_code_verifier");

      if (!code || !state || state !== storedState || !codeVerifier) {
        setStatus("error");
        setError("Invalid callback parameters");
        return;
      }

      try {
        await api.callback({ code, state, code_verifier: codeVerifier });
        const userData = await api.getMe();
        setUser(userData);

        sessionStorage.removeItem("oidc_state");
        sessionStorage.removeItem("oidc_nonce");
        sessionStorage.removeItem("oidc_code_verifier");

        setStatus("success");
        setTimeout(() => navigate("/"), 1000);
      } catch (err) {
        setStatus("error");
        setError(err instanceof Error ? err.message : "Authentication failed");
      }
    };

    handleCallback();
  }, [navigate, searchParams, setUser]);

  if (status === "loading") {
    return (
      <div className="page flex items-center justify-center">
        <div className="card text-center">
          <div className="flex justify-center mb-4">
            <Loader2 size={32} className="animate-spin" style={{ color: "var(--color-primary)" }} />
          </div>
          <p className="text-[var(--color-text-muted)]">Completing sign in...</p>
        </div>
      </div>
    );
  }

  if (status === "success") {
    return (
      <div className="page flex items-center justify-center">
        <div className="card text-center">
          <div className="flex justify-center mb-4">
            <CheckCircle size={48} style={{ color: "var(--color-success)" }} />
          </div>
          <h2 className="text-xl font-bold mb-2">Welcome back!</h2>
          <p className="text-[var(--color-text-muted)]">Redirecting to dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page flex items-center justify-center">
      <div className="card text-center max-w-md">
        <div className="flex justify-center mb-4">
          <AlertCircle size={48} style={{ color: "var(--color-error)" }} />
        </div>
        <h2 className="text-xl font-bold mb-2">Sign in failed</h2>
        <p className="text-[var(--color-text-muted)] mb-4">{error || "An unknown error occurred"}</p>
        <button onClick={() => navigate("/login")} className="btn btn-primary">
          Try again
        </button>
      </div>
    </div>
  );
}