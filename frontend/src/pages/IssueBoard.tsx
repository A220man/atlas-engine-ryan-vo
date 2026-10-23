import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { api, Issue, IssueCreate, IssueCompletion } from "@/api/client";
import {
  Plus, CheckCircle, Clock, AlertCircle, X,
  Loader2, GripVertical,
} from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { FormDialog } from "@/components/FormDialog";

const statusLabels: Record<Issue["status"], string> = {
  open: "Open",
  in_progress: "In Progress",
  ready_for_review: "Review",
  done: "Done",
  wont_fix: "Won't Fix",
};

const statusIcons: Record<Issue["status"], React.ReactNode> = {
  done: <CheckCircle size={16} style={{ color: "var(--color-success)" }} />,
  in_progress: <Clock size={16} style={{ color: "var(--color-warning)" }} />,
  ready_for_review: <AlertCircle size={16} style={{ color: "var(--color-info)" }} />,
  wont_fix: <X size={16} style={{ color: "var(--color-error)" }} />,
  open: <Clock size={16} style={{ color: "var(--color-text-muted)" }} />,
};

const initialFormData: IssueCreate = {
  session_id: "",
  title: "",
  description: "",
  decision_ids: [],
  acceptance_criteria: [],
  blocked_by: [],
  pr_workflow: false,
};

export default function IssueBoard() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const currentSessionId = sessionId || "default-session";
  const queryClient = useQueryClient();

  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState<IssueCreate>({
    ...initialFormData,
    session_id: currentSessionId,
  });
  const [newCriterion, setNewCriterion] = useState("");

  const { data: issues, isLoading } = useQuery({
    queryKey: ["issues", currentSessionId],
    queryFn: () => api.listIssues(currentSessionId),
    enabled: !!currentSessionId,
  });
  const { data: unblocked } = useQuery({
    queryKey: ["unblocked-issues", currentSessionId],
    queryFn: () => api.getUnblockedIssues(currentSessionId),
    enabled: !!currentSessionId,
  });

  const createMutation = useMutation({
    mutationFn: (data: IssueCreate) => api.createIssue(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["issues", currentSessionId] });
      queryClient.invalidateQueries({ queryKey: ["unblocked-issues", currentSessionId] });
      setShowForm(false);
      setFormData({ ...initialFormData, session_id: currentSessionId });
    },
  });

  const completeMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: IssueCompletion }) =>
      api.completeIssue(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["issues", currentSessionId] });
      queryClient.invalidateQueries({ queryKey: ["unblocked-issues", currentSessionId] });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createMutation.mutate(formData);
  };

  const handleAddCriterion = () => {
    if (newCriterion.trim()) {
      const newCriteria = [...(formData.acceptance_criteria || []), {
        id: `ac-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        description: newCriterion.trim(),
        verified: false,
      }];
      setFormData({ ...formData, acceptance_criteria: newCriteria });
      setNewCriterion("");
    }
  };

  const handleComplete = (issue: Issue) => {
    const unverified = (issue.acceptance_criteria || [])
      .filter((c) => !c.verified)
      .map((c) => c.id);
    if (unverified.length > 0) {
      completeMutation.mutate({
        id: issue.id,
        data: { resolution_commit: "pending-completion", verified_criteria: unverified, close: true },
      });
    }
  };

  const handleCloseForm = () => setShowForm(false);

  const unblockedIds = new Set(unblocked?.map((i: Issue) => i.id) || []);

  return (
    <div className="page">
      <PageHeader
        title="Issue Board"
        subtitle="Trace decisions through issues to implementation"
        action={
          <button
            onClick={() => setShowForm(true)}
            className="btn btn-primary"
            disabled={createMutation.isPending}
          >
            <Plus size={18} />
            Create Issue
          </button>
        }
      />

      <FormDialog
        isOpen={showForm}
        onClose={handleCloseForm}
        title="New Issue"
        isSubmitting={createMutation.isPending}
        onSubmit={handleSubmit}
        submitLabel="Create Issue"
      >
        <div>
          <label className="label">Title <span className="text-[var(--color-error)]">*</span></label>
          <input
            className="input w-full"
            value={formData.title}
            onChange={(e) => setFormData({ ...formData, title: e.target.value })}
            placeholder="Issue title"
            required
          />
        </div>

        <div>
          <label className="label">Description <span className="text-[var(--color-error)]">*</span></label>
          <textarea
            className="input textarea"
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            placeholder="Describe the issue and which decisions it traces..."
            rows={6}
            required
          />
        </div>

        <div>
          <label className="label">Decision IDs</label>
          <input
            className="input w-full font-mono text-sm"
            value={formData.decision_ids?.join(", ") || ""}
            onChange={(e) =>
              setFormData({
                ...formData,
                decision_ids: e.target.value.split(",").map((s) => s.trim()).filter(Boolean),
              })
            }
            placeholder="Comma-separated decision ULIDs"
          />
          <p className="text-xs text-[var(--color-text-muted)] mt-1">
            Associate this issue with specific decisions from the decision ledger
          </p>
        </div>

        <div>
          <label className="label">Blocked By</label>
          <input
            className="input w-full font-mono text-sm"
            value={formData.blocked_by?.join(", ") || ""}
            onChange={(e) =>
              setFormData({
                ...formData,
                blocked_by: e.target.value.split(",").map((s) => s.trim()).filter(Boolean),
              })
            }
            placeholder="Comma-separated issue ULIDs that must be done first"
          />
        </div>

        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={formData.pr_workflow || false}
              onChange={(e) => setFormData({ ...formData, pr_workflow: e.target.checked })}
            />
            <span>PR-based workflow (closing handled by merge)</span>
          </label>
        </div>

        <div>
          <label className="label">Acceptance Criteria</label>
          <div className="space-y-2">
            {(formData.acceptance_criteria || []).map((c, idx) => (
              <div key={c.id || idx} className="flex items-center gap-2">
                <input
                  className="input flex-1 text-sm"
                  value={c.description}
                  onChange={(e) => {
                    const updated = [...(formData.acceptance_criteria || [])];
                    updated[idx] = { ...updated[idx], description: e.target.value };
                    setFormData({ ...formData, acceptance_criteria: updated });
                  }}
                  placeholder={`Criterion ${idx + 1}`}
                />
                <button
                  type="button"
                  onClick={() => {
                    const updated = [...(formData.acceptance_criteria || [])];
                    updated.splice(idx, 1);
                    setFormData({ ...formData, acceptance_criteria: updated });
                  }}
                  className="btn btn-ghost btn-sm"
                  aria-label="Remove criterion"
                >
                  <X size={14} />
                </button>
              </div>
            ))}
          </div>
          <div className="flex gap-2 mt-2">
            <input
              className="input flex-1 text-sm"
              value={newCriterion}
              onChange={(e) => setNewCriterion(e.target.value)}
              placeholder="Add a criterion..."
              onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), handleAddCriterion())}
            />
            <button
              type="button"
              onClick={handleAddCriterion}
              className="btn btn-secondary btn-sm"
            >
              Add
            </button>
          </div>
        </div>
      </FormDialog>

      {isLoading ? (
        <div className="flex justify-center py-8">
          <Loader2 size={24} className="animate-spin" style={{ color: "var(--color-primary)" }} />
        </div>
      ) : !issues || issues.length === 0 ? (
        <div className="empty-state">
          <GripVertical className="empty-state-icon" size={48} />
          <p>No issues yet. Create your first issue to trace decisions through implementation.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {issues.map((issue: Issue) => (
            <div key={issue.id} className="card">
              <div className="flex items-start gap-3 p-4">
                <div className="flex flex-col items-center gap-1 min-w-[80px]">
                  {statusIcons[issue.status]}
                  <span className={`badge ${
                    issue.status === "done" ? "badge-success" :
                    issue.status === "in_progress" || issue.status === "ready_for_review" ? "badge-warning" :
                    issue.status === "wont_fix" ? "badge-error" : "badge-muted"
                  }`}>
                    {statusLabels[issue.status]}
                  </span>
                  {unblockedIds.has(issue.id) && issue.status !== "done" && (
                    <span className="badge badge-xs badge-primary" title="Unblocked">●</span>
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-medium">{issue.title}</h3>
                  <p className="text-sm text-[var(--color-text-muted)] mt-1 line-clamp-2">
                    {issue.description}
                  </p>
                  {issue.decision_ids && issue.decision_ids.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {issue.decision_ids.map((did) => (
                        <span key={did} className="text-xs font-mono bg-[var(--color-bg-hover)] px-2 py-0.5 rounded">
                          D:{did.slice(0, 8)}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {issue.acceptance_criteria && issue.acceptance_criteria.length > 0 && (
                <div className="px-4 pb-3 border-t border-[var(--color-border)]">
                  <p className="text-xs font-medium text-[var(--color-text-muted)] mb-2">
                    Acceptance Criteria ({issue.acceptance_criteria.filter((c) => c.verified).length}/{issue.acceptance_criteria.length})
                  </p>
                  <div className="space-y-1">
                    {issue.acceptance_criteria.map((c) => (
                      <div key={c.id} className="flex items-center gap-2 text-sm">
                        <div className={`w-3 h-3 rounded-full flex items-center justify-center ${
                          c.verified ? "bg-[var(--color-success)]" : "border border-[var(--color-border)]"
                        }`}>
                          {c.verified && <CheckCircle size={10} color="white" />}
                        </div>
                        <span className={c.verified ? "line-through text-[var(--color-text-muted)]" : ""}>
                          {c.description}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {issue.blocked_by && issue.blocked_by.length > 0 && (
                <div className="px-4 pb-3 border-t border-[var(--color-border)]">
                  <p className="text-xs text-[var(--color-text-muted)]">
                    Blocked by: {issue.blocked_by.map((b) => b.slice(0, 8)).join(", ")}
                  </p>
                </div>
              )}

              {issue.status !== "done" && !issue.pr_workflow && (
                <div className="px-4 pb-4 border-t border-[var(--color-border)]">
                  <button
                    onClick={() => handleComplete(issue)}
                    className="btn btn-success btn-sm w-full"
                    disabled={completeMutation.isPending}
                  >
                    {completeMutation.isPending ? "Completing..." : "Mark Verified & Close"}
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}