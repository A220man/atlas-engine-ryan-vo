import { type ReactElement } from "react";
import { render, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, it, expect, vi } from "vitest";
import Dashboard from "../Dashboard";

vi.mock("@/api/client", () => ({
  api: {
    getDecisions: vi.fn().mockResolvedValue([]),
    getPrds: vi.fn().mockResolvedValue([]),
    getUnblockedIssues: vi.fn().mockResolvedValue([]),
  },
}));

vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => ({
    user: { oidc_sub: "test", email: "test@test.com", name: "Test", roles: ["viewer"] },
    loading: false,
    login: vi.fn(),
    logout: vi.fn(),
  }),
}));

function renderWithClient(ui: ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("Dashboard", () => {
  it("renders the dashboard page title", async () => {
    const { container } = renderWithClient(<Dashboard />);
    await waitFor(() => {
      expect(container.querySelector(".page-title")?.textContent).toBe("Dashboard");
    });
  });

  it("renders overview cards with counts", async () => {
    const { container } = renderWithClient(<Dashboard />);
    await waitFor(() => {
      expect(container.textContent).toContain("PRDs");
      expect(container.textContent).toContain("New Grill Session");
    });
  });
});