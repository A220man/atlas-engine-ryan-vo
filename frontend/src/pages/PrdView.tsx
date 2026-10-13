import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams, Link } from "react-router-dom";
import { api, Prd, PrdMapping, PrdCreate, PrdMappingCreate, Decision } from "@/api/client";
import { Plus, Save, FileText, GitBranch, AlertTriangle, Loader2 } from "lucide-react";
import { formatDistanceToNow } from "date-fns";

export default function PrdView() {
  const { sessionId, prdId } = useParams<{ sessionId: string; prdId?: string }>();
  const currentSessionId = sessionId || "default-session";
  const queryClient = useQueryClient();

  const [showCreateForm, setShowCreateForm] = useState(false);
  const [createForm, setCreateForm] = useState<PrdCreate>({
    session_id: currentSessionId,
    type: "product",
    title: "",
    content: "",
    decision_versions: {},
  });

  const { data: prds } = useQuery({
    queryKey: ["prds", currentSessionId],
    queryFn: () => api.listPrds(currentSessionId),
    enabled: !!currentSessionId,
  });

  const { data: currentPrd } = useQuery({
    queryKey: ["prd", prdId],
    queryFn: () => api.getPrd(prdId!),
    enabled: !!prdId,
  });

  const { data: staleness } = useQuery({
    queryKey: ["prd-staleness", prdId],
    queryFn: () => api.checkPrdStaleness(prdId!),
    enabled: !!prdId,
  });

  const { data: decisions } = useQuery({
    queryKey: ["decisions", currentSessionId],
    queryFn: () => api.listDecisions(currentSessionId),
    enabled: !!currentSessionId,
  });

  const createMutation = useMutation({
    mutationFn: (data: PrdCreate) => api.createPrd(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["prds", currentSessionId] });
      setShowCreateForm(false);
      setCreateForm({ session_id: currentSessionId, type: "product", title: "", content: "", decision_versions: {} });
    },
  });

  const addMappingMutation = useMutation({
    mutationFn: ({ prdId, data }: { prdId: string; data: PrdMappingCreate }) => api.addPrdMapping(prdId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["prd", prdId] });
      queryClient.invalidateQueries({ queryKey: ["decisions", currentSessionId] });
    },
  });

  if (!prdId && !showCreateForm) {
    return (
      <div className="page">
        <header className="page-header">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div>
              <h1 className="page-title">PRDs & Design Documents</h1>
              <p className="page-subtitle">Map decisions to requirements, user stories, and acceptance criteria</p>
            </div>
            <button onClick={() => setShowCreateForm(true)} className="btn btn-primary">
              <Plus size={18} />
              Create PRD
            </button>
          </div>
        </header>

        <div className="card">
          {prds && prds.length > 0 ? (
            <div className="table-container">
              <table className="table">
                <thead>
                  <tr>
                    <th>Title</th>
                    <th>Type</th>
                    <th>Decisions Mapped</th>
                    <th>Created</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {prds.map((prd: Prd) => (
                    <tr key={prd.id}>
                      <td className="font-medium">{prd.title}</td>
                      <td>
                        <span className={`badge ${prd.type === "design" ? "badge-warning" : "badge-primary"}`}>
                          {prd.type}
                        </span>
                      </td>
                      <td>{Object.keys(prd.decision_versions || {}).length}</td>
                      <td className="text-[var(--color-text-muted)]">
                        {formatDistanceToNow(new Date(prd.created_at), { addSuffix: true })}
                      </td>
                      <td>
                        <Link to={`/session/${currentSessionId}/prd/${prd.id}`} className="btn btn-ghost btn-sm">
                          View
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty-state">
              <FileText className="empty-state-icon" size={48} />
              <p>No PRDs yet. Create your first PRD to map decisions.</p>
            </div>
          )}
        </div>
      </div>
    );
  }

  if (showCreateForm && !prdId) {
    return (
      <div className="page">
        <header className="page-header">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div>
              <h1 className="page-title">Create PRD</h1>
              <p className="page-subtitle">Create a new Product Requirements Document or Design Document</p>
            </div>
            <button onClick={() => setShowCreateForm(false)} className="btn btn-ghost">
              Cancel
            </button>
          </div>
        </header>

        <div className="card max-w-3xl">
          <form onSubmit={(e) => { e.preventDefault(); createMutation.mutate(createForm); }} className="space-y-4">
            <div>
              <label className="label">Type</label>
              <select
                className="input"
                value={createForm.type}
                onChange={(e) => setCreateForm({ ...createForm, type: e.target.value as "product" | "design" })}
              >
                <option value="product">Product Requirements Document</option>
                <option value="design">Design Document</option>
              </select>
            </div>

            <div>
              <label className="label">Title <span className="text-[var(--color-error)]">*</span></label>
              <input
                className="input"
                value={createForm.title}
                onChange={(e) => setCreateForm({ ...createForm, title: e.target.value })}
                placeholder="e.g., User Authentication System"
                required
              />
            </div>

            <div>
              <label className="label">Content (Markdown) <span className="text-[var(--color-error)]">*</span></label>
              <textarea
                className="input textarea font-mono text-sm"
                value={createForm.content}
                onChange={(e) => setCreateForm({ ...createForm, content: e.target.value })}
                placeholder="# PRD Title\n\n## Overview\n\n## Requirements\n\n## Acceptance Criteria"
                required
                rows={20}
              />
            </div>

            <div>
              <label className="label">Decision Versions (JSON)</label>
              <textarea
                className="input textarea font-mono text-sm"
                value={JSON.stringify(createForm.decision_versions, null, 2)}
                onChange={(e) => {
                  try {
                    setCreateForm({ ...createForm, decision_versions: JSON.parse(e.target.value) });
                  } catch {}
                }}
                placeholder='{"decision-id": 1}'
                rows={4}
              />
            </div>

            <div className="flex justify-end gap-2 pt-4 border-t border-[var(--color-border)]">
              <button type="button" onClick={() => setShowCreateForm(false)} className="btn btn-secondary">
                Cancel
              </button>
              <button type="submit" className="btn btn-primary" disabled={createMutation.isPending}>
                {createMutation.isPending ? <><Loader2 size={16} className="animate-spin" /> Creating...</> : <><Save size={16} /> Create PRD</>}
              </button>
            </div>
          </form>
        </div>
      </div>
    );
  }

  if (!currentPrd) {
    return (
      <div className="page flex items-center justify-center">
        <div className="empty-state">
          <Loader2 size={48} className="animate-spin" style={{ color: "var(--color-primary)" }} />
          <p>Loading PRD...</p>
        </div>
      </div>
    );
  }

  const handleAddMapping = (decisionId: string) => {
    addMappingMutation.mutate({
      prdId: currentPrd.id,
      data: { decision_id: decisionId, user_story_refs: [], acceptance_criteria_refs: [], constraint_refs: [] },
    });
  };

  const mappedDecisionIds = new Set(currentPrd.mappings.map((m: PrdMapping) => m.decision_id));
  const unmappedDecisions = decisions?.filter((d: Decision) => !mappedDecisionIds.has(d.id)) || [];

  return (
    <div className="page">
      <header className="page-header">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <Link to={`/session/${currentSessionId}/prd`} className="btn btn-ghost btn-sm mb-2">
              ← Back to PRDs
            </Link>
            <div className="flex items-center gap-3">
              <h1 className="page-title">{currentPrd.title}</h1>
              <span className={`badge ${currentPrd.type === "design" ? "badge-warning" : "badge-primary"}`}>
                {currentPrd.type}
              </span>
              {staleness?.is_stale && (
                <span className="badge badge-error flex items-center gap-1">
                  <AlertTriangle size={12} /> Stale
                </span>
              )}
            </div>
          </div>
        </div>
      </header>

      {staleness?.is_stale && (
        <div className="mb-4 p-3 bg-[var(--color-error)]/10 border border-[var(--color-error)]/30 rounded-lg">
          <div className="flex items-center gap-2 text-sm mb-2">
            <AlertTriangle size={16} style={{ color: "var(--color-error)" }} />
            <span className="font-medium">PRD is stale</span>
          </div>
          <p className="text-sm text-[var(--color-text-muted)]">
            {staleness.stale_mappings.length} decision(s) have been updated since this PRD was mapped.
          </p>
          <ul className="text-xs text-[var(--color-text-muted)] mt-2 space-y-1">
            {staleness.stale_mappings.map((m: { decision_id: string; decision_version: number; mapped_version: number }, i: number) => (
              <li key={i}>Decision {m.decision_id.slice(0, 8)}: v{m.mapped_version} → v{m.decision_version}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 card">
          <div className="card-header">
            <h2 className="card-title">Content</h2>
          </div>
          <div className="prose prose-invert max-w-none">
            {currentPrd.content.split("\n").map((line: string, i: number) => (
              <p key={i} className="whitespace-pre-wrap">{line}</p>
            ))}
          </div>
        </div>

        <div className="space-y-4">
          <div className="card">
            <div className="card-header">
              <h2 className="card-title">Decision Mappings</h2>
            </div>
            {currentPrd.mappings.length === 0 ? (
              <div className="empty-state py-8">
                <GitBranch className="empty-state-icon" size={32} />
                <p>No decisions mapped yet</p>
              </div>
            ) : (
              <div className="space-y-3">
                {currentPrd.mappings.map((mapping: PrdMapping, index: number) => (
                  <div key={index} className="border border-[var(--color-border)] rounded-lg p-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-sm">{mapping.decision_question || `Decision ${mapping.decision_id.slice(0, 8)}`}</p>
                        <p className="text-xs text-[var(--color-text-muted)]">
                          Version: {mapping.decision_version}
                        </p>
                      </div>
                    </div>
                    <div className="mt-2 grid grid-cols-3 gap-2 text-xs">
                      <div>
                        <span className="text-[var(--color-text-muted)]">User Stories:</span>
                        <span className="ml-1 font-medium">{mapping.user_story_refs.length}</span>
                      </div>
                      <div>
                        <span className="text-[var(--color-text-muted)]">Criteria:</span>
                        <span className="ml-1 font-medium">{mapping.acceptance_criteria_refs.length}</span>
                      </div>
                      <div>
                        <span className="text-[var(--color-text-muted)]">Constraints:</span>
                        <span className="ml-1 font-medium">{mapping.constraint_refs.length}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="card">
            <div className="card-header">
              <h2 className="card-title">Map Decisions</h2>
            </div>
            {unmappedDecisions.length === 0 ? (
              <p className="text-sm text-[var(--color-text-muted)]">All decisions mapped</p>
            ) : (
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {unmappedDecisions.map((d: Decision) => (
                  <button
                    key={d.id}
                    onClick={() => handleAddMapping(d.id)}
                    className="w-full text-left p-3 border border-[var(--color-border)] rounded-lg hover:bg-[var(--color-bg-hover)] transition-colors flex items-center justify-between"
                    disabled={addMappingMutation.isPending}
                  >
                    <div>
                      <p className="font-medium text-sm">Q{d.question_number}: {d.question.slice(0, 60)}</p>
                      <p className="text-xs text-[var(--color-text-muted)]">v{d.version}</p>
                    </div>
                    <Plus size={16} style={{ color: "var(--color-primary)" }} />
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}