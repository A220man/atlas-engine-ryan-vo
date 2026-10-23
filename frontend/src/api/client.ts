import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from "axios";

const API_BASE = import.meta.env.VITE_API_BASE || "/api/v1";

class ApiClient {
  private client: AxiosInstance;
  private accessToken: string | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE,
      withCredentials: true,
      headers: {
        "Content-Type": "application/json",
      },
    });

    this.client.interceptors.request.use((config: InternalAxiosRequestConfig) => {
      if (this.accessToken && config.headers) {
        config.headers.Authorization = `Bearer ${this.accessToken}`;
      }
      return config;
    });

    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        if (error.response?.status === 401) {
          this.accessToken = null;
          if (window.location.pathname !== "/login") {
            window.location.href = "/login";
          }
        }
        return Promise.reject(error);
      }
    );
  }

  setToken(token: string | null) {
    this.accessToken = token;
  }

  getToken() {
    return this.accessToken;
  }

  async login() {
    const response = await this.client.get("/auth/login");
    return response.data;
  }

  async callback(data: { code: string; state: string; code_verifier: string }) {
    const response = await this.client.post("/auth/callback", data);
    if (response.data.access_token) {
      this.setToken(response.data.access_token);
    }
    return response.data;
  }

  async logout() {
    await this.client.post("/auth/logout");
    this.setToken(null);
  }

  async getMe() {
    const response = await this.client.get("/auth/me");
    return response.data;
  }

  async listDecisions(sessionId: string) {
    const response = await this.client.get(`/decisions/session/${sessionId}`);
    return response.data;
  }

  async getDecision(id: string) {
    const response = await this.client.get(`/decisions/${id}`);
    return response.data;
  }

  async createDecision(data: DecisionCreate) {
    const response = await this.client.post("/decisions", data);
    return response.data;
  }

  async supersedeDecision(id: string, data: DecisionCreate) {
    const response = await this.client.post(`/decisions/${id}/supersede`, data);
    return response.data;
  }

  async getDecisionCoverage(id: string) {
    const response = await this.client.get(`/decisions/${id}/coverage`);
    return response.data;
  }

  async getSessionCoverage(sessionId: string) {
    const response = await this.client.get(`/decisions/session/${sessionId}/coverage`);
    return response.data;
  }

  async getFrontier(sessionId: string, settledIds: string[]) {
    const response = await this.client.post(`/decisions/session/${sessionId}/frontier`, {
      settled_decision_ids: settledIds,
    });
    return response.data;
  }

  async listPrds(sessionId: string) {
    const response = await this.client.get(`/prds/session/${sessionId}`);
    return response.data;
  }

  async getPrd(id: string) {
    const response = await this.client.get(`/prds/${id}`);
    return response.data;
  }

  async createPrd(data: PrdCreate) {
    const response = await this.client.post("/prds", data);
    return response.data;
  }

  async addPrdMapping(prdId: string, data: PrdMappingCreate) {
    const response = await this.client.post(`/prds/${prdId}/mappings`, data);
    return response.data;
  }

  async checkPrdStaleness(prdId: string) {
    const response = await this.client.get(`/prds/${prdId}/staleness`);
    return response.data;
  }

  async listIssues(sessionId: string, status?: string) {
    const params = status ? { status } : {};
    const response = await this.client.get(`/issues/session/${sessionId}`, { params });
    return response.data;
  }

  async getIssue(id: string) {
    const response = await this.client.get(`/issues/${id}`);
    return response.data;
  }

  async createIssue(data: IssueCreate) {
    const response = await this.client.post("/issues", data);
    return response.data;
  }

  async updateIssue(id: string, data: IssueUpdate) {
    const response = await this.client.patch(`/issues/${id}`, data);
    return response.data;
  }

  async completeIssue(id: string, data: IssueCompletion) {
    const response = await this.client.post(`/issues/${id}/complete`, data);
    return response.data;
  }

  async getUnblockedIssues(sessionId: string) {
    const response = await this.client.get(`/issues/session/${sessionId}/frontier`);
    return response.data;
  }

  async listVerifications(sessionId: string, decisionId?: string) {
    const params = decisionId ? { decision_id: decisionId } : {};
    const response = await this.client.get(`/verifications/session/${sessionId}`, { params });
    return response.data;
  }

  async getVerification(id: string) {
    const response = await this.client.get(`/verifications/${id}`);
    return response.data;
  }

  async createVerification(data: VerificationCreate) {
    const response = await this.client.post("/verifications", data);
    return response.data;
  }

  async updateVerification(id: string, data: VerificationUpdate) {
    const response = await this.client.patch(`/verifications/${id}`, data);
    return response.data;
  }

  async getCoverageReport(sessionId: string) {
    const response = await this.client.get(`/verifications/session/${sessionId}/coverage`);
    return response.data;
  }
}

export const api = new ApiClient();

export interface User {
  id: string;
  email: string;
  name: string;
  roles: string[];
}

export interface Decision {
  id: string;
  session_id: string;
  question_number: number;
  assumption_number: number | null;
  question: string;
  answer: string;
  normalized_requirement: string;
  constraints: Record<string, any>;
  is_pivot: boolean;
  status: string;
  version: number;
  superseded_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface DecisionCreate {
  session_id: string;
  question: string;
  answer: string;
  normalized_requirement: string;
  constraints?: Record<string, any>;
  is_pivot?: boolean;
  assumption_number?: number;
}

export interface Prd {
  id: string;
  session_id: string;
  type: "product" | "design";
  title: string;
  content: string;
  decision_versions: Record<string, number>;
  created_at: string;
  updated_at: string;
}

export interface PrdMapping {
  decision_id: string;
  decision_question: string | null;
  decision_version: number;
  user_story_refs: string[];
  acceptance_criteria_refs: string[];
  constraint_refs: string[];
}

export interface PrdCreate {
  session_id: string;
  type: "product" | "design";
  title: string;
  content: string;
  decision_versions?: Record<string, number>;
}

export interface PrdMappingCreate {
  decision_id: string;
  user_story_refs?: string[];
  acceptance_criteria_refs?: string[];
  constraint_refs?: string[];
}

export interface AcceptanceCriterion {
  id: string;
  description: string;
  verified: boolean;
  verified_at?: string;
  verified_by?: string;
}

export interface Issue {
  id: string;
  session_id: string;
  type: "github" | "local";
  external_id: string | null;
  external_url: string | null;
  title: string;
  description: string;
  status: "open" | "in_progress" | "ready_for_review" | "done" | "wont_fix";
  decision_ids: string[];
  acceptance_criteria: AcceptanceCriterion[];
  blocked_by: string[];
  pr_workflow: boolean;
  closed_at: string | null;
  closed_by: string | null;
  resolution_commit: string | null;
  created_at: string;
  updated_at: string;
}

export interface IssueCreate {
  session_id: string;
  type?: "github" | "local";
  external_id?: string;
  external_url?: string;
  title: string;
  description: string;
  decision_ids?: string[];
  acceptance_criteria?: AcceptanceCriterion[];
  blocked_by?: string[];
  pr_workflow?: boolean;
}

export interface IssueUpdate {
  title?: string;
  description?: string;
  status?: Issue["status"];
  acceptance_criteria?: AcceptanceCriterion[];
  blocked_by?: string[];
}

export interface IssueCompletion {
  resolution_commit: string;
  verified_criteria?: string[];
  close?: boolean;
}

export interface Verification {
  id: string;
  session_id: string;
  decision_id: string;
  issue_id: string | null;
  status: "pending" | "in_progress" | "passed" | "failed" | "blocked";
  evidence_type: "test_result" | "screenshot" | "log" | "document" | "code_review" | "manual";
  evidence_ref: string;
  evidence_content: string | null;
  criteria_covered: string[];
  constraints_covered: string[];
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface VerificationCreate {
  session_id: string;
  decision_id: string;
  issue_id?: string;
  evidence_type: Verification["evidence_type"];
  evidence_ref: string;
  evidence_content?: string;
  criteria_covered?: string[];
  constraints_covered?: string[];
  notes?: string;
}

export interface VerificationUpdate {
  status?: Verification["status"];
  evidence_content?: string;
  criteria_covered?: string[];
  constraints_covered?: string[];
  notes?: string;
}

export interface CoverageReport {
  session_id: string;
  total_decisions: number;
  covered_decisions: number;
  coverage_percent: number;
  by_category: Record<string, number>;
  gaps: Array<Record<string, any>>;
}