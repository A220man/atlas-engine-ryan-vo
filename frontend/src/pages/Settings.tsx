import { useState, useEffect } from "react";
import { api, User } from "@/api/client";
import { Shield, Github, AlertCircle } from "lucide-react";

export default function Settings() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchUser = async () => {
      try {
        const userData = await api.getMe();
        setUser(userData);
      } catch {
        window.location.href = "/login";
      } finally {
        setLoading(false);
      }
    };
    fetchUser();
  }, []);

  if (loading) {
    return (
      <div className="page flex items-center justify-center py-12">
        <div className="empty-state">
          <div className="empty-state-icon">⏳</div>
          <p>Loading settings...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <div className="page max-w-4xl mx-auto">
      <header className="page-header">
        <div>
          <h1 className="page-title">Settings</h1>
          <p className="page-subtitle">Configure your Atlas Engine environment</p>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <div className="card">
            <div className="card-header">
              <h2 className="card-title">Profile</h2>
            </div>
            <div className="text-center py-6">
              <div className="w-20 h-20 rounded-full bg-[var(--color-primary-muted)] flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl font-bold" style={{ color: "var(--color-primary)" }}>
                  {user.name?.charAt(0) || user.email?.charAt(0) || "?"}
                </span>
              </div>
              <h3 className="font-bold text-lg">{user.name}</h3>
              <p className="text-[var(--color-text-muted)] text-sm">{user.email}</p>
              <div className="mt-4">
                <span className="badge badge-primary">
                  {user.roles[0] || "viewer"}
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="lg:col-span-2 space-y-6">
          <div className="card">
            <div className="card-header">
              <h2 className="card-title flex items-center gap-2">
                <Shield size={18} />
                Authentication
              </h2>
            </div>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">OIDC / Keycloak</p>
                  <p className="text-sm text-[var(--color-text-muted)]">
                    Single sign-on is configured via the backend Keycloak instance.
                  </p>
                </div>
                <span className="badge badge-success">Active</span>
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Session Security</p>
                  <p className="text-sm text-[var(--color-text-muted)]">
                    HttpOnly, SameSite cookies with CSRF protection
                  </p>
                </div>
                <span className="badge badge-success">Secure</span>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <h2 className="card-title flex items-center gap-2">
                <Github size={18} />
                GitHub Integration
              </h2>
            </div>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Token Status</p>
                  <p className="text-sm text-[var(--color-text-muted)]">
                    GitHub API token for issue synchronization
                  </p>
                </div>
                <span className="badge badge-muted">Not configured</span>
              </div>
              <p className="text-xs text-[var(--color-text-muted)]">
                Configure GITHUB_TOKEN in the backend .env to enable GitHub issue sync.
                Token is stored server-side only and never sent to the client.
              </p>
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <h2 className="card-title">AI Provider</h2>
            </div>
            <div className="space-y-4">
              <p className="text-sm text-[var(--color-text-muted)]">
                LLM providers (OpenAI, Anthropic, Gemini, Ollama) are configured on the backend.
                All LLM calls happen server-side with bounded timeouts. Set LLM_API_KEY and
                LLM_PROVIDER to enable AI-powered assistance.
              </p>
              <div className="flex items-center gap-2">
                <AlertCircle size={16} style={{ color: "var(--color-warning)" }} />
                <span className="text-sm text-[var(--color-text-muted)]">
                  No API keys are stored in the browser or frontend source code.
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}