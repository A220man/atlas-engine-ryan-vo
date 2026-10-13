import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi } from "vitest";
import Settings from "../Settings";

vi.mock("@/api/client", () => ({
  api: {
    getMe: vi.fn().mockResolvedValue({
      oidc_sub: "user-1",
      email: "test@example.com",
      name: "Test User",
      roles: ["viewer"],
    }),
  },
}));

describe("Settings", () => {
  it("renders the settings page title", async () => {
    render(
      <MemoryRouter>
        <Settings />
      </MemoryRouter>,
    );
    expect(await screen.findByText("Settings")).toBeInTheDocument();
  });

  it("displays user profile information", async () => {
    render(
      <MemoryRouter>
        <Settings />
      </MemoryRouter>,
    );
    await waitFor(() => {
      expect(screen.getByText("test@example.com")).toBeInTheDocument();
    });
  });
});