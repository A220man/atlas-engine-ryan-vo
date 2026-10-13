import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { api, Decision, Prd, Issue } from "@/api/client";
import { FolderOpen, FileText, GitBranch, CheckCircle2, Users, Plus, Clock, AlertTriangle } from "lucide-react";
import { formatDistanceToNow } from "date-fns";

interface ActivityItem {
  type: "decision" | "prd" | "issue";
  title: string;
  subtitle: string;
  time: string;
  href: string;
}

export default function Dashboard() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const currentSessionId = sessionId || "default-session";

  const { data: decisions } = useQuery({
    queryKey: ["decisions", currentSessionId],
    queryFn: () => api.listDecisions(currentSessionId),
    enabled: !!currentSessionId,
  });

  const { data: prds } = useQuery({
    queryKey: ["prds", currentSessionId],
    queryFn: () => api.listPrds(currentSessionId),
    enabled: !!currentSessionId,
  });

  const { data: issues } = useQuery({
    queryKey: ["issues", currentSessionId],
    queryFn: () => api.listIssues(currentSessionId),
    enabled: !!currentSessionId,
  });

  const { data: coverage } = useQuery({
    queryKey: ["coverage", currentSessionId],
    queryFn: () => api.getSessionCoverage(currentSessionId),
    enabled: !!currentSessionId,
  });

  const stats = [
    {
      label: "Decisions",
      value: decisions?.length || 0,
      icon: FileText,
      color: "var(--color-primary)",
      href: `/session/${currentSessionId}/grill`,
    },
    {
      label: "PRDs",
      value: prds?.length || 0,
      icon: GitBranch,
      color: "var(--color-warning)",
      href: `/session/${currentSessionId}/prd`,
    },
    {
      label: "Issues",
      value: issues?.length || 0,
      icon: CheckCircle2,
      color: "var(--color-success)",
      href: `/session/${currentSessionId}/issues`,
    },
    {
      label: "Coverage",
      value: `${Math.round(coverage?.coverage_percent || 0)}%`,
      icon: Users,
      color: coverage && coverage.coverage_percent >= 80 ? "var(--color-success)" : "var(--color-warning)",
      href: `/session/${currentSessionId}/verification`,
    },
  ];

  const recentActivity: ActivityItem[] = [
    ...(decisions?.slice(0, 3).map((d: Decision) => ({
      type: "decision" as const,
      title: d.question,
      subtitle: `Decision #${d.question_number}`,
      time: d.created_at,
      href: `/session/${currentSessionId}/grill`,
    })) || []),
    ...(prds?.slice(0, 2).map((p: Prd) => ({
      type: "prd" as const,
      title: p.title,
      subtitle: p.type === "design" ? "Design Document" : "Product Requirements",
      time: p.created_at,
      href: `/session/${currentSessionId}/prd/${p.id}`,
    })) || []),
    ...(issues?.slice(0, 2).map((i: Issue) => ({
      type: "issue" as const,
      title: i.title,
      subtitle: i.status.replace("_", " "),
      time: i.created_at,
      href: `/session/${currentSessionId}/issues`,
    })) || []),
  ].sort((a, b) => new Date(b.time).getTime() - new Date(a.time).getTime()).slice(0, 5);

  return (
    <div className="page">
      <header className="page-header">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <h1 className="page-title">Dashboard</h1>
            <p className="page-subtitle">Session: <code className="px-2 py-0.5 bg-[var(--color-bg)] rounded">{currentSessionId}</code></p>
          </div>
          <Link to={`/session/${currentSessionId}/grill`} className="btn btn-primary">
            <Plus size={18} />
            New Grill Session
          </Link>
        </div>
      </header>

      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {stats.map((stat) => (
          <Link key={stat.label} to={stat.href} className="card hover:border-[var(--color-border-focus)] transition-colors">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-[var(--color-text-muted)]">{stat.label}</p>
                <p className="text-3xl font-bold mt-1" style={{ color: stat.color }}>{stat.value}</p>
              </div>
              <div className="p-2 rounded-lg" style={{ background: `${stat.color}20` }}>
                <stat.icon size={24} style={{ color: stat.color }} />
              </div>
            </div>
          </Link>
        ))}
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 card">
          <div className="card-header">
            <h2 className="card-title">Recent Activity</h2>
          </div>
          {recentActivity.length === 0 ? (
            <div className="empty-state">
              <FolderOpen className="empty-state-icon" size={48} />
              <p>No activity yet. Start a grill session to begin.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {recentActivity.map((activity, index) => (
                <Link key={index} to={activity.href} className="flex items-start gap-3 p-3 rounded-lg hover:bg-[var(--color-bg-hover)] transition-colors">
                  <div className="p-2 rounded-lg" style={{
                    background: activity.type === "decision" ? "var(--color-primary-muted)" :
                              activity.type === "prd" ? "#854d0e33" : "#16653433",
                  }}>
                    {activity.type === "decision" && <FileText size={18} style={{ color: "var(--color-primary)" }} />}
                    {activity.type === "prd" && <GitBranch size={18} style={{ color: "var(--color-warning)" }} />}
                    {activity.type === "issue" && <CheckCircle2 size={18} style={{ color: "var(--color-success)" }} />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium truncate">{activity.title}</p>
                    <p className="text-sm text-[var(--color-text-muted)]">{activity.subtitle}</p>
                  </div>
                  <span className="text-xs text-[var(--color-text-muted)] whitespace-nowrap">
                    {formatDistanceToNow(new Date(activity.time), { addSuffix: true })}
                  </span>
                </Link>
              ))}
            </div>
          )}
        </div>

        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Coverage Overview</h2>
          </div>
          {coverage ? (
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span>Overall Coverage</span>
                  <span className="font-bold" style={{ color: coverage.coverage_percent >= 80 ? "var(--color-success)" : "var(--color-warning)" }}>
                    {Math.round(coverage.coverage_percent)}%
                  </span>
                </div>
                <div className="h-2 bg-[var(--color-bg)] rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{
                      width: `${coverage.coverage_percent}%`,
                      background: coverage.coverage_percent >= 80 ? "var(--color-success)" : "var(--color-warning)",
                    }}
                  />
                </div>
              </div>

              <div className="space-y-2">
                {Object.entries(coverage.by_category).map(([cat, count]) => (
                  <div key={cat} className="flex items-center justify-between text-sm">
                    <span className="capitalize">{cat.replace("_", " ")}</span>
                    <span className="font-medium">{count} / {coverage.total}</span>
                  </div>
                ))}
              </div>

              {coverage.gaps.length > 0 && (
                <div className="p-3 bg-[var(--color-warning)]/10 border border-[var(--color-warning)]/30 rounded-lg">
                  <div className="flex items-center gap-2 text-sm mb-2">
                    <AlertTriangle size={16} style={{ color: "var(--color-warning)" }} />
                    <span className="font-medium">Gaps detected</span>
                  </div>
                  <p className="text-xs text-[var(--color-text-muted)]">
                    {coverage.gaps.length} decision(s) missing coverage in one or more categories
                  </p>
                  <Link
                    to={`/session/${currentSessionId}/verification`}
                    className="btn btn-sm btn-secondary mt-2"
                  >
                    View details
                  </Link>
                </div>
              )}
            </div>
          ) : (
            <div className="empty-state">
              <Clock className="empty-state-icon" size={48} />
              <p>No coverage data</p>
            </div>
          )}
        </div>
      </div>

      <section className="mt-6">
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Quick Actions</h2>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <Link to={`/session/${currentSessionId}/grill`} className="btn btn-secondary h-24 flex-col justify-center gap-2">
              <FileText size={28} style={{ color: "var(--color-primary)" }} />
              <span>Start Grill Session</span>
              <span className="text-xs text-[var(--color-text-muted)]">Record decisions</span>
            </Link>
            <Link to={`/session/${currentSessionId}/prd`} className="btn btn-secondary h-24 flex-col justify-center gap-2">
              <GitBranch size={28} style={{ color: "var(--color-warning)" }} />
              <span>Create PRD</span>
              <span className="text-xs text-[var(--color-text-muted)]">Map decisions</span>
            </Link>
            <Link to={`/session/${currentSessionId}/issues`} className="btn btn-secondary h-24 flex-col justify-center gap-2">
              <CheckCircle2 size={28} style={{ color: "var(--color-success)" }} />
              <span>Generate Issues</span>
              <span className="text-xs text-[var(--color-text-muted)]">Track work</span>
            </Link>
            <Link to={`/session/${currentSessionId}/verification`} className="btn btn-secondary h-24 flex-col justify-center gap-2">
              <Users size={28} style={{ color: "var(--color-primary)" }} />
              <span>Verify Coverage</span>
              <span className="text-xs text-[var(--color-text-muted)]">Close gaps</span>
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}