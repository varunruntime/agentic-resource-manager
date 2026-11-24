/* @vitest-environment jsdom */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { api } from "../lib/api";
import Optimization from "./Optimization";

vi.mock("../lib/api", () => ({
  api: { get: vi.fn(), post: vi.fn() },
}));

const apiGet = vi.mocked(api.get);
const apiPost = vi.mocked(api.post);

const state = {
  cpu_percent: 86,
  memory_percent: 72,
  disk_percent: 40,
  network_usage: 45,
  active_workloads: 2,
  instances: 2,
  latency_ms: 140,
  estimated_cost: 0.2,
  estimated_energy: 0.36,
};

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("Optimization page", () => {
  beforeEach(() => {
    apiGet
      .mockResolvedValueOnce({ data: state } as never)
      .mockResolvedValueOnce({ data: [state] } as never);
    apiPost.mockResolvedValueOnce({
      data: {
        decision_id: "decision-123",
        selected_action: "ADD_INSTANCE",
        reason: "Predicted capacity pressure.",
        safety: { approved: true, reason: "Action is within policy." },
        candidate_actions: [{
          action: "ADD_INSTANCE",
          reason: "Add capacity.",
          expected_effect: "Reduce CPU pressure.",
          estimated_cost: 0.2,
          score: 0.8,
        }],
      },
    } as never);
  });

  it("sends observed state, history, weights and recommendation-only mode", async () => {
    render(<Optimization />);
    fireEvent.click(screen.getByRole("button", { name: "Score candidate actions" }));

    expect(await screen.findByText("ADD_INSTANCE")).toBeTruthy();
    expect(apiGet).toHaveBeenNthCalledWith(1, "/api/resources/current");
    expect(apiGet).toHaveBeenNthCalledWith(2, "/api/resources/history");
    expect(apiPost).toHaveBeenCalledWith("/api/agents/run", {
      state,
      history: [state],
      weights: {
        performance: 0.4,
        cost: 0.25,
        energy: 0.2,
        utilization: 0.15,
      },
      mode: "recommendation",
    });
    expect(screen.getByText(/no resource action is executed/i)).toBeTruthy();
  });
});
