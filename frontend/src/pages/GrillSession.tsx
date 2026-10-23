import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { api, Decision, DecisionCreate } from "@/api/client";
import { Plus, Zap, Lightbulb, Loader2, ArrowUpDown } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { FormDialog } from "@/components/FormDialog";
import { DecisionCard } from "@/components/DecisionCard";

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

  const isSubmitting = createMutation.isPending || supersedeMutation.isPending;

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

  const handleCloseForm = () => {
    setShowForm(false);
    setEditingId(null);
  };

  const pivotIds = new Set(frontier?.pivots.map((p: Decision) => p.id) || []);

  const questions = decisions?.filter((d: Decision) => d.assumption_number === null) || [];
  const assumptions = decisions?.filter((d: Decision) => d.assumption_number !== null) || [];

  return (
    <div className="page">
      <PageHeader
        title="Grill Session"
        subtitle="Record decisions with stable IDs, versioning, and frontier tracking"
        action={
          <button onClick={() => setShowForm(true)} className="btn btn-primary" disabled={isSubmitting}>
            <Plus size={18} />
            {editingId ? "Update Decision" : "Add Decision"}
          </button>
        }
      />

      <FormDialog
        isOpen={showForm}
        onClose={handleCloseForm}
        title={editingId ? "Edit Decision" : "New Decision"}
        isSubmitting={isSubmitting}
        onSubmit={handleSubmit}
        submitLabel={editingId ? "Update" : "Create"}
      >
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
      </FormDialog>

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