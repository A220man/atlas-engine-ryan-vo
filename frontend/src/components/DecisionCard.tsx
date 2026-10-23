import { Decision } from "@/api/client";
import { Zap, ChevronUp, ChevronDown, Check } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { useState } from "react";

interface DecisionCardProps {
  decision: Decision;
  isPivot: boolean;
  onEdit: (d: Decision) => void;
  isAssumption: boolean;
}

export function DecisionCard({ decision, isPivot, onEdit, isAssumption }: DecisionCardProps) {
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