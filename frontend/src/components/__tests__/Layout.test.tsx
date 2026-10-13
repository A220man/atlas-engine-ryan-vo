import { render, screen, cleanup } from "@testing-library/react";
import { describe, it, expect, afterEach, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import Layout from "../Layout";

vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => ({
    user: { oidc_sub: "test", email: "test@test.com", name: "Test", roles: ["viewer"] },
    loading: false,
    login: vi.fn(),
    logout: vi.fn(),
  }),
}));

afterEach(() => cleanup());

describe("Layout", () => {
  it("renders children content within the page wrapper", () => {
    render(
      <MemoryRouter>
        <Layout>
          <div data-testid="child-content">Hello World</div>
        </Layout>
      </MemoryRouter>,
    );

    expect(screen.getByTestId("child-content")).toBeInTheDocument();
    expect(screen.getByText("Hello World")).toBeInTheDocument();
  });

  it("renders the application footer with version and contact", () => {
    render(
      <MemoryRouter>
        <Layout>
          <div />
        </Layout>
      </MemoryRouter>,
    );

    expect(screen.getByText("Atlas Engine v1.0.0")).toBeInTheDocument();
    expect(screen.getByText(/Ryan Vo/)).toBeInTheDocument();
  });
});