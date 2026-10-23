import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import {
  api,
  Verification,
  VerificationCreate,
  Decision,
  Issue,
  CoverageReport,
} from "@/api/client";
import {
  Plus, CheckCircle, XCircle, Clock, AlertTriangle,
  Loader2, BarChart3,
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { PageHeader } from "@/components/PageHeader";
import { FormDialog } from "@/components/FormDialog";

const evidenceTypeLabels: Record<Verification["evidence_type"], string> = {
  test_result: "Test Result",
  screenshot: "Screenshot",
  log: "Log",
  document: "Document",
  code_review: "Code Review",
  manual: "Manual",
};

const statusColors: Record<Verification["status"], string> = {
  passed: "var(--color-success)",
  failed: "var(--color-error)",
  pending: "var(--color-text-muted)",
  in_progress: "var(--color-warning)",
  blocked: "var(--color-error)",
};

const statusIcons: Record<Verification["status"], React.ReactNode> = {
  passed: <CheckCircle size={16} />,
  failed: <XCircle size={16} />,
  in_progress: <Clock size={16} />,
  blocked: <AlertTriangle size={16} />,
  pending: <Clock size={16} />,
};

export default function VerificationPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const currentSessionId = sessionId || "default-session";
  const queryClient = useQueryClient();

  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState<VerificationCreate>({
    session_id: currentSessionId,
    decision_id: "",
    evidence_type: "test_result",
    evidence_ref: "",
    evidence_content: "",
    criteria_covered: [],
    constraints_covered: [],
    notes: "",
  });

  const { data: verifications, isLoading } = useQuery({
    queryKey: ["verifications", currentSessionId],
    queryFn: () => api.listVerifications(currentSessionId),
    enabled: !!currentSessionId,
  });

  const { data: decisions } = useQuery({
    queryKey: ["decisions", currentSessionId],
    queryFn: () => api.listDecisions(currentSessionId),
    enabled: !!currentSessionId,
  });

  const { data: issues } = useQuery({
    queryKey: ["issues", currentSessionId],
    queryFn: () => api.listIssues(currentSessionId),
    enabled: !!currentSessionId,
  });

  const { data: coverage } = useQuery<CoverageReport>({
    queryKey: ["coverage", currentSessionId],
    queryFn: () => api.getCoverageReport(currentSessionId),
    enabled: !!currentSessionId,
  });

  const createMutation = useMutation({
    mutationFn: (data: VerificationCreate) => api.createVerification(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["verifications", currentSessionId] });
      queryClient.invalidateQueries({ queryKey: ["coverage", currentSessionId] });
      setShowForm(false);
      setFormData({
        session_id: currentSessionId,
        decision_id: "",
        evidence_type: "test_result",
        evidence_ref: "",
        evidence_content: "",
        criteria_covered: [],
        constraints_covered: [],
        notes: "",
      });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createMutation.mutate(formData);
  };

  const handleCloseForm = () => setShowForm(false);

  const decisionMap = new Map<string, Decision>(
    (decisions || []).map((d: Decision) => [d.id, d])
  );
  const issueMap = new Map<string, Issue>(
    (issues || []).map((i: Issue) => [i.id, i])
  );

  return (
    <div className="page">
      <PageHeader
        title="Verification"
        subtitle="Evidence that decisions, stories, and criteria are satisfied"
        action={
          <button
            onClick={() => setShowForm(true)}
            className="btn btn-primary"
            disabled={createMutation.isPending}
          >
            <Plus size={18} />
            Add Evidence
          </button>
        }
      />

      {coverage && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="card text-center">
            <div className="text-2xl font-bold" style={{ color: "var(--color-primary)" }}>
              {coverage.total_decisions}
            </div>
            <p className="text-xs text-[var(--color-text-muted)]">Total Decisions</p>
          </div>
          <div className="card text-center">
            <div className="text-2xl font-bold" style={{ color: "var(--color-success)" }}>
              {coverage.covered_decisions}
            </div>
            <p className="text-xs text-[var(--color-text-muted)]">Fully Covered</p>
          </div>
          <div className="card text-center">
            <div className="text-2xl font-bold">
              {Math.round(coverage.coverage_percent)}%
            </div>
            <p className="text-xs text-[var(--color-text-muted)]">Coverage Rate</p>
          </div>
          <div className="card text-center">
            <div className="text-2xl font-bold" style={{ color: coverage.gaps.length > 0 ? "var(--color-error)" : "var(--color-success)" }}>
              {coverage.gaps.length}
            </div>
            <p className="text-xs text-[var(--color-text-muted)]">Gaps</p>
          </div>
        </div>
      )}

      {coverage && coverage.gaps.length > 0 && (
        <div className="card mb-6">
          <div className="card-header">
            <h2 className="card-title flex items-center gap-2">
              <AlertTriangle size={18} style={{ color: "var(--color-warning)" }} />
              Coverage Gaps
            </h2>
          </div>
          <div className="space-y-3">
            {coverage.gaps.map((gap, i) => (
              <div key={i} className="p-3 bg-[var(--color-bg)] rounded-lg">
                <p className="font-medium text-sm">
                  Decision {gap.decision_id.slice(0, 12)}
                </p>
                <div className="flex flex-wrap gap-3 mt-1 text-xs">
                  {gap.missing_prd && <span className="badge badge-error">Missing PRD</span>}
                  {gap.missing_issue && <span className="badge badge-error">Missing Issue</span>}
                  {gap.missing_implementation && <span className="badge badge-error">Missing Impl</span>}
                  {gap.missing_verification && <span className="badge badge-error">Missing Verification</span>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <FormDialog
        isOpen={showForm}
        onClose={handleCloseForm}
        title="Add Verification Evidence"
        isSubmitting={createMutation.isPending}
        onSubmit={handleSubmit}
        submitLabel="Save Evidence"
      >
        <div>
          <label className="label">Decision ID <span className="text-[var(--color-error)]">*</span></label>
          <input
            className="input w-full font-mono text-sm"
            value={formData.decision_id}
            onChange={(e) => setFormData({ ...formData, decision_id: e.target.value })}
            placeholder="Decision ULID"
            required
          />
          {decisions && decisions.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-2">
              {decisions.map((d: Decision) => (
                <button
                  key={d.id}
                  type="button"
                  onClick={() => setFormData({ ...formData, decision_id: d.id })}
                  className="text-xs font-mono bg-[var(--color-bg-hover)] px-2 py-1 rounded hover:bg-[var(--color-bg-elevated)]"
                >
                  Q{d.question_number}: {d.question.slice(0, 40)}...
                </button>
              ))}
            </div>
          )}
        </div>

        <div>
          <label className="label">Evidence Type <span className="text-[var(--color-error)]">*</span></label>
          <select
            className="input w-full"
            value={formData.evidence_type}
            onChange={(e) => setFormData({ ...formData, evidence_type: e.target.value as Verification["evidence_type"] })}
          >
            {Object.entries(evidenceTypeLabels).map(([key, label]) => (
              <option key={key} value={key}>{label}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="label">Evidence Reference <span className="text-[var(--color-error)]">*</span></label>
          <input
            className="input w-full font-mono text-sm"
            value={formData.evidence_ref}
            onChange={(e) => setFormData({ ...formData, evidence_ref: e.target.value })}
            placeholder="e.g., test_report_001, commit abc123, URL"
            required
          />
        </div>

        <div>
          <label className="label">Evidence Content (optional)</label>
          <textarea
            className="input textarea font-mono text-sm"
            value={formData.evidence_content || ""}
            onChange={(e) => setFormData({ ...formData, evidence_content: e.target.value })}
            placeholder="Paste test output, log excerpt, or notes..."
            rows={6}
          />
        </div>

        <div>
          <label className="label">Criteria Covered</label>
          <input
            className="input w-full font-mono text-sm"
            value={formData.criteria_covered?.join(", ") || ""}
            onChange={(e) =>
              setFormData({
                ...formData,
                criteria_covered: e.target.value.split(",").map((s) => s.trim()).filter(Boolean),
              })
            }
            placeholder="Comma-separated criterion IDs"
          />
        </div>

        <div>
          <label className="label">Constraints Covered</label>
          <input
            className="input w-full font-mono text-sm"
            value={formData.constraints_covered?.join(", ") || ""}
            onChange={(e) =>
              setFormData({
                ...formData,
                constraints_covered: e.target.value.split(",").map((s) => s.trim()).filter(Boolean),
              })
            }
            placeholder="Comma-separated constraint keys"
          />
        </div>

        <div>
          <label className="label">Notes</label>
          <textarea
            className="input textarea"
            value={formData.notes || ""}
            onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
            placeholder="Additional context about this verification..."
            rows={3}
          />
        </div>
      </FormDialog>

      {isLoading ? (
        <div className="flex justify-center py-8">
          <Loader2 size={24} className="animate-spin" style={{ color: "var(--color-primary)" }} />
        </div>
      ) : !verifications || verifications.length === 0 ? (
        <div className="empty-state">
          <BarChart3 className="empty-state-icon" size={48} />
          <p>No verification evidence yet. Add evidence to close the traceability loop.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {verifications.map((v: Verification) => (
            <div key={v.id} className="card">
              <div className="p-4 flex items-start gap-3">
                <div className="flex flex-col items-center gap-1 min-w-[50px]">
                  <div style={{ color: statusColors[v.status] }}>
                    {statusIcons[v.status]}
                  </div>
                  <span className="text-xs font-medium">{v.evidence_type}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2">
                    <h3 className="font-medium">{v.evidence_ref}</h3>
                    <span className={`badge ${
                      v.status === "passed" ? "badge-success" :
                      v.status === "failed" ? "badge-error" :
                      v.status === "in_progress" ? "badge-warning" :
                      v.status === "blocked" ? "badge-error" : "badge-muted"
                    }`}>
                      {v.status}
                    </span>
                    {decisionMap.has(v.decision_id) && (
                      <span className="text-xs text-[var(--color-text-muted)]">
                        traces: Q{decisionMap.get(v.decision_id)!.question_number}
                      </span>
                    )}
                  </div>
                  {v.evidence_content && (
                    <pre className="text-xs bg-[var(--color-code-bg)] p-3 rounded overflow-auto mb-2">
                      {v.evidence_content.slice(0, 500)}
                      {v.evidence_content.length > 500 && "..."}
                    </pre>
                  )}
                  <div className="flex flex-wrap gap-3 text-xs text-[var(--color-text-muted)]">
                    {v.criteria_covered.length > 0 && (
                      <span>Criteria: {v.criteria_covered.length}</span>
                    )}
                    {v.constraints_covered.length > 0 && (
                      <span>Constraints: {v.constraints_covered.length}</span>
                    )}
                    {v.issue_id && issueMap.has(v.issue_id) && (
                      <span>Issue: {issueMap.get(v.issue_id)!.title.slice(0, 30)}</span>
                    )}
                    <span>
                      Created {formatDistanceToNow(new Date(v.created_at), { addSuffix: true })}
                    </span>
                  </div>
                  {v.notes && (
                    <p className="text-xs text-[var(--color-text-muted)] mt-2 italic">{v.notes}</p>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}