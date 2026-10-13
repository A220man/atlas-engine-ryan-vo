import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { api, Decision, DecisionCreate } from "@/api/client";
import { Plus, Save, ArrowUpDown, Zap, Lightbulb, Loader2, Check, X, ChevronDown, ChevronUp } from "lucide-react";
import { formatDistanceToNow } from "date-fns";

interface QuestionForm {
  question: string;
  answer: string;
  normalized_requirement: string;
  constraints: Record<string, any>;
  is_pivot: boolean;
  is_assumption: boolean;
}

export default function GrillSession() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const currentSessionId = sessionId || "default-session";
  const queryClient = useQueryClient();

  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formData, setFormData] = useState<QuestionForm>({
    question: "",
    answer: "",
    normalized_requirement: "",
    constraints: {},
    is_pivot: false,
    is_assumption: false,
  });

  const { data: decisions, isLoading } = useQuery({
    queryKey: ["decisions", currentSessionId],
    queryFn: () => api.listDecisions(currentSessionId),
    enabled: !!currentSessionId,
  });

  const { data: frontier } = useQuery({
    queryKey: ["frontier", currentSessionId],
    queryFn: () => api.getFrontier(currentSessionId, []),
    enabled: !!currentSessionId,
  });

  const createMutation = useMutation({
    mutationFn: (data: DecisionCreate) => api.createDecision(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["decisions", currentSessionId] });
      queryClient.invalidateQueries({ queryKey: ["frontier", currentSessionId] });
      setShowForm(false);
      setFormData({ question: "", answer: "", normalized_requirement: "", constraints: {}, is_pivot: false, is_assumption: false });
    },
  });

  const supersedeMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: DecisionCreate }) => api.supersedeDecision(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["decisions", currentSessionId] });
      setEditingId(null);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const data: DecisionCreate = {
      session_id: currentSessionId,
      question: formData.question,
      answer: formData.answer,
      normalized_requirement: formData.normalized_requirement,
      constraints: formData.constraints,
      is_pivot: formData.is_pivot,
      assumption_number: formData.is_assumption ? undefined : undefined,
    };
    if (editingId) {
      supersedeMutation.mutate({ id: editingId, data });
    } else {
      createMutation.mutate(data);
    }
  };

  const handleEdit = (decision: Decision) => {
    setEditingId(decision.id);
    setFormData({
      question: decision.question,
      answer: decision.answer,
      normalized_requirement: decision.normalized_requirement,
      constraints: decision.constraints,
      is_pivot: decision.is_pivot,
      is_assumption: decision.assumption_number !== null,
    });
    setShowForm(true);
  };

  const pivotIds = new Set(frontier?.pivots.map((p: Decision) => p.id) || []);

  const questions = decisions?.filter((d: Decision) => d.assumption_number === null) || [];
  const assumptions = decisions?.filter((d: Decision) => d.assumption_number !== null) || [];

  return (
    <div className="page">
      <header className="page-header">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <h1 className="page-title">Grill Session</h1>
            <p className="page-subtitle">Record decisions with stable IDs, versioning, and frontier tracking</p>
          </div>
          <button onClick={() => setShowForm(true)} className="btn btn-primary" disabled={createMutation.isPending}>
            <Plus size={18} />
            {editingId ? "Update Decision" : "Add Decision"}
          </button>
        </div>
      </header>

      {showForm && (
        <div className="card mb-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="flex items-center gap-2 mb-4">
              <h2 className="card-title">{editingId ? "Edit Decision" : "New Decision"}</h2>
              <button
                type="button"
                onClick={() => { setShowForm(false); setEditingId(null); }}
                className="btn btn-ghost btn-sm ml-auto"
              >
                <X size={16} /> Cancel
              </button>
            </div>

            <div>
              <label className="label">Question <span className="text-[var(--color-error)]">*</span></label>
              <textarea
                className="input textarea"
                value={formData.question}
                onChange={(e) => setFormData({ ...formData, question: e.target.value })}
                placeholder="What decision needs to be made?"
                required
              />
            </div>

            <div>
              <label className="label">Answer <span className="text-[var(--color-error)]">*</span></label>
              <textarea
                className="input textarea"
                value={formData.answer}
                onChange={(e) => setFormData({ ...formData, answer: e.target.value })}
                placeholder="The resolved answer"
                required
              />
            </div>

            <div>
              <label className="label">Normalized Requirement <span className="text-[var(--color-error)]">*</span></label>
              <textarea
                className="input textarea"
                value={formData.normalized_requirement}
                onChange={(e) => setFormData({ ...formData, normalized_requirement: e.target.value })}
                placeholder="Testable, verifiable requirement extracted from the answer"
                required
              />
            </div>

            <div>
              <label className="label">Constraints (JSON)</label>
              <textarea
                className="input textarea font-mono text-sm"
                value={JSON.stringify(formData.constraints, null, 2)}
                onChange={(e) => {
                  try {
                    setFormData({ ...formData, constraints: JSON.parse(e.target.value) });
                  } catch {}
                }}
                placeholder='{"environment": "production", "cost": "managed"}'
              />
            </div>

            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.is_pivot}
                  onChange={(e) => setFormData({ ...formData, is_pivot: e.target.checked })}
                />
                <span>Pivot decision (reshapes the design tree)</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={formData.is_assumption}
                  onChange={(e) => setFormData({ ...formData, is_assumption: e.target.checked })}
                />
                <span>Assumption (auto-accepted unless vetoed)</span>
              </label>
            </div>

            <div className="flex justify-end gap-2 pt-4 border-t border-[var(--color-border)]">
              <button type="button" onClick={() => { setShowForm(false); setEditingId(null); }} className="btn btn-secondary">
                Cancel
              </button>
              <button type="submit" className="btn btn-primary" disabled={createMutation.isPending || supersedeMutation.isPending}>
                {createMutation.isPending || supersedeMutation.isPending ? (
                  <>
                    <Loader2 size={16} className="animate-spin" /> Saving...
                  </>
                ) : (
                  <>
                    <Save size={16} /> {editingId ? "Update" : "Create"}
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="card mb-6">
        <div className="card-header">
          <h2 className="card-title">Frontier & Pivots</h2>
        </div>
        {frontier && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <h3 className="font-medium mb-2 flex items-center gap-2">
                <Zap size={16} style={{ color: "var(--color-warning)" }} />
                Pivots ({frontier.pivots.length}) - Ask First
              </h3>
              {frontier.pivots.length === 0 ? (
                <p className="text-sm text-[var(--color-text-muted)]">No pivot decisions in frontier</p>
              ) : (
                <ul className="space-y-2">
                  {frontier.pivots.map((d: Decision) => (
                    <li key={d.id} className="text-sm p-2 bg-[var(--color-bg)] rounded">
                      <span className="font-medium">Q{d.question_number}</span>: {d.question.slice(0, 80)}...
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <div>
              <h3 className="font-medium mb-2 flex items-center gap-2">
                <ArrowUpDown size={16} style={{ color: "var(--color-primary)" }} />
                Frontier ({frontier.frontier.length}) - Ready to Ask
              </h3>
              {frontier.frontier.length === 0 ? (
                <p className="text-sm text-[var(--color-text-muted)]">Frontier empty - all settled</p>
              ) : (
                <ul className="space-y-2">
                  {frontier.frontier.map((d: Decision) => (
                    <li key={d.id} className="text-sm p-2 bg-[var(--color-bg)] rounded">
                      <span className={pivotIds.has(d.id) ? "font-medium text-[var(--color-warning)]" : "font-medium"}>
                        Q{d.question_number}
                      </span>: {d.question.slice(0, 80)}...
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}
      </div>

      <div className="card mb-6">
        <div className="card-header">
          <h2 className="card-title">Questions ({questions.length})</h2>
        </div>
        {isLoading ? (
          <div className="flex justify-center py-8">
            <Loader2 size={24} className="animate-spin" style={{ color: "var(--color-primary)" }} />
          </div>
        ) : questions.length === 0 ? (
          <div className="empty-state">
            <Lightbulb className="empty-state-icon" size={48} />
            <p>No questions yet. Add your first decision above.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {questions.map((d: Decision) => (
              <DecisionCard
                key={d.id}
                decision={d}
                isPivot={pivotIds.has(d.id)}
                onEdit={handleEdit}
                isAssumption={false}
              />
            ))}
          </div>
        )}
      </div>

      {assumptions.length > 0 && (
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Assumptions ({assumptions.length})</h2>
          </div>
          <div className="space-y-3">
            {assumptions.map((d: Decision) => (
              <DecisionCard
                key={d.id}
                decision={d}
                isPivot={false}
                onEdit={handleEdit}
                isAssumption={true}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function DecisionCard({ decision, isPivot, onEdit, isAssumption }: {
  decision: Decision;
  isPivot: boolean;
  onEdit: (d: Decision) => void;
  isAssumption: boolean;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border border-[var(--color-border)] rounded-lg overflow-hidden">
      <div className="p-4 flex items-start gap-3">
        <div className="flex flex-col items-center gap-1 min-w-[60px]">
          <span className="font-mono text-sm font-medium text-[var(--color-text-muted)]">
            {isAssumption ? `A${decision.assumption_number}` : `Q${decision.question_number}`}
          </span>
          {isPivot && <Zap size={12} style={{ color: "var(--color-warning)" }} />}
          <span className={`badge badge-xs ${decision.status === "superseded" ? "badge-muted" : "badge-success"}`}>
            v{decision.version}
          </span>
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <h3 className="font-medium truncate">{isAssumption ? "Assumption" : "Question"}: {decision.question}</h3>
            {decision.status === "superseded" && (
              <span className="badge badge-muted">Superseded</span>
            )}
          </div>
          <p className="text-sm text-[var(--color-text-muted)] mb-2">{decision.answer}</p>
          <p className="text-sm font-mono text-[var(--color-primary)]/80">
            Requirement: {decision.normalized_requirement.slice(0, 120)}...
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setExpanded(!expanded)}
            className="btn btn-ghost btn-sm"
            aria-expanded={expanded}
          >
            {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
          <button onClick={() => onEdit(decision)} className="btn btn-ghost btn-sm" aria-label="Edit">
            <Check size={16} />
          </button>
        </div>
      </div>

      {expanded && (
        <div className="p-4 border-t border-[var(--color-border)] bg-[var(--color-bg)] space-y-3">
          <div>
            <h4 className="text-xs font-medium text-[var(--color-text-muted)] mb-1">Constraints</h4>
            <pre className="text-xs bg-[var(--color-code-bg)] p-3 rounded overflow-auto">
              {JSON.stringify(decision.constraints, null, 2) || "{}"}
            </pre>
          </div>
          <div className="flex items-center gap-2 text-xs text-[var(--color-text-muted)]">
            <span>Created: {formatDistanceToNow(new Date(decision.created_at), { addSuffix: true })}</span>
            <span>•</span>
            <span>Updated: {formatDistanceToNow(new Date(decision.updated_at), { addSuffix: true })}</span>
            {decision.superseded_by && (
              <>
                <span>•</span>
                <span className="text-[var(--color-warning)]">Superseded by {decision.superseded_by.slice(0, 8)}</span>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}