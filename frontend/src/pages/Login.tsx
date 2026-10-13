import { useEffect } from "react";
import { useAuth } from "@/hooks/useAuth";
import { Shield, Sparkles, Terminal, ArrowRight } from "lucide-react";

export default function Login() {
  const { login, loading } = useAuth();

  useEffect(() => {
    if (!loading) {
      login();
    }
  }, [login, loading]);

  return (
    <div className="page flex items-center justify-center min-h-[calc(100vh-200px)]">
      <div className="card w-full max-w-md text-center">
        <div className="flex justify-center mb-6">
          <div className="w-16 h-16 rounded-xl bg-[var(--color-primary-muted)] flex items-center justify-center">
            <Shield size={32} style={{ color: "var(--color-primary)" }} />
          </div>
        </div>

        <h1 className="text-2xl font-bold mb-2">Welcome to Atlas Engine</h1>
        <p className="text-[var(--color-text-muted)] mb-8">
          Skills for Real Engineers. Traceable decisions from grill to verification.
        </p>

        <div className="grid grid-cols-3 gap-4 mb-8 text-left">
          <div className="p-3 bg-[var(--color-bg)] rounded-lg">
            <Terminal size={20} className="mb-2" style={{ color: "var(--color-primary)" }} />
            <h3 className="font-medium text-sm">Decision Ledger</h3>
            <p className="text-xs text-[var(--color-text-muted)]">Stable IDs, versioned</p>
          </div>
          <div className="p-3 bg-[var(--color-bg)] rounded-lg">
            <Sparkles size={20} className="mb-2" style={{ color: "var(--color-warning)" }} />
            <h3 className="font-medium text-sm">Frontier Gate</h3>
            <p className="text-xs text-[var(--color-text-muted)]">Pivot-first ordering</p>
          </div>
          <div className="p-3 bg-[var(--color-bg)] rounded-lg">
            <ArrowRight size={20} className="mb-2" style={{ color: "var(--color-success)" }} />
            <h3 className="font-medium text-sm">Coverage Check</h3>
            <p className="text-xs text-[var(--color-text-muted)]">PRD → Issue → Verify</p>
          </div>
        </div>

        {loading && (
          <div className="flex items-center justify-center gap-2 text-[var(--color-text-muted)]">
            <div className="w-5 h-5 border-2 border-[var(--color-primary)] border-t-transparent rounded-full animate-spin" />
            <span>Redirecting to Keycloak...</span>
          </div>
        )}
      </div>
    </div>
  );
}