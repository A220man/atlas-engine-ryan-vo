import { NavLink, useLocation } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { Layout as LucideLayout, LogOut, Settings, Users, BookOpen, GitBranch, CheckCircle2, Menu, X } from "lucide-react";
import { useState } from "react";

const navigation = [
  { path: "/", label: "Dashboard", icon: LucideLayout },
  { path: "/session/current/grill", label: "Grill Session", icon: BookOpen },
  { path: "/session/current/prd", label: "PRDs", icon: GitBranch },
  { path: "/session/current/issues", label: "Issues", icon: CheckCircle2 },
  { path: "/session/current/verification", label: "Verification", icon: Users },
  { path: "/settings", label: "Settings", icon: Settings },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const currentSessionId = "current";

  const navItems = navigation.map((item) => ({
    ...item,
    path: item.path.replace("/current", `/${currentSessionId}`),
  }));

  return (
    <div className="page">
      <header className="border-b border-[var(--color-border)] bg-[var(--color-bg-elevated)] sticky top-0 z-10">
        <div className="container flex items-center justify-between h-16">
          <NavLink to="/" className="flex items-center gap-2 font-bold text-lg" aria-label="Atlas Engine Home">
            <span style={{ color: "var(--color-primary)" }}>▲</span>
            <span>Atlas Engine</span>
          </NavLink>

          <nav className="hidden md:flex items-center gap-1" aria-label="Main navigation">
            {navItems.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  `flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-[var(--color-primary-muted)] text-[var(--color-primary)]"
                      : "text-[var(--color-text-muted)] hover:text-[var(--color-text)] hover:bg-[var(--color-bg-hover)]"
                  }`
                }
                aria-current={location.pathname === item.path ? "page" : undefined}
              >
                <item.icon size={16} aria-hidden="true" />
                {item.label}
              </NavLink>
            ))}
          </nav>

          <div className="flex items-center gap-3">
            <div className="hidden md:flex items-center gap-3 text-sm">
              <span className="text-[var(--color-text-muted)]">{user?.email}</span>
              <span className="badge badge-primary">{user?.roles[0] || "viewer"}</span>
            </div>

            <button
              onClick={logout}
              className="btn btn-ghost btn-sm hidden md:flex"
              aria-label="Log out"
            >
              <LogOut size={18} aria-hidden="true" />
            </button>

            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="btn btn-ghost btn-sm md:hidden"
              aria-label={mobileMenuOpen ? "Close menu" : "Open menu"}
              aria-expanded={mobileMenuOpen}
            >
              {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
          </div>
        </div>

        {mobileMenuOpen && (
          <div className="md:hidden border-t border-[var(--color-border)] p-4">
            <nav className="flex flex-col gap-2" aria-label="Mobile navigation">
              {navItems.map((item) => (
                <NavLink
                  key={item.path}
                  to={item.path}
                  onClick={() => setMobileMenuOpen(false)}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium ${
                      isActive
                        ? "bg-[var(--color-primary-muted)] text-[var(--color-primary)]"
                        : "text-[var(--color-text-muted)] hover:text-[var(--color-text)] hover:bg-[var(--color-bg-hover)]"
                    }`
                  }
                >
                  <item.icon size={18} aria-hidden="true" />
                  {item.label}
                </NavLink>
              ))}
              <button
                onClick={logout}
                className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-[var(--color-text-muted)] hover:text-[var(--color-text)] hover:bg-[var(--color-bg-hover)]"
              >
                <LogOut size={18} aria-hidden="true" />
                Log out
              </button>
            </nav>
          </div>
        )}
      </header>

      <main className="flex-1 container py-6">
        {children}
      </main>

      <footer className="border-t border-[var(--color-border)] py-4">
        <div className="container flex items-center justify-between text-sm text-[var(--color-text-muted)]">
          <span>Atlas Engine v1.0.0</span>
          <span>Ryan Vo {String.fromCharCode(60)}ryandtvo@gmail.com{String.fromCharCode(62)}</span>
        </div>
      </footer>
    </div>
  );
}