/* @vitest-environment jsdom */
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { api } from "../lib/api";
import Experiments from "./Experiments";

vi.mock("../lib/api", () => ({
  api: {
    post: vi.fn(),
  },
}));

const apiPost = vi.mocked(api.post);

const baseline = {
  system: "BASELINE",
  avg_cpu: 61.2,
  avg_memory: 68.1,
  latency: 105.0,
  throughput: 65.0,
  scaling_actions: 2,
  reaction_time: 1,
  resource_wastage: 38.8,
  slo_violations: 0,
  estimated_cost: 0.2,
  estimated_energy: 0.36,
  prediction_accuracy: 82.5,
  unnecessary_actions: 0,
};

const proposed = {
  ...baseline,
  system: "PROPOSED",
  avg_cpu: 54.3,
  avg_memory: 62.4,
  latency: 92.0,
  throughput: 69.3,
  scaling_actions: 3,
  reaction_time: 0,
  resource_wastage: 45.7,
  estimated_cost: 0.3,
  estimated_energy: 0.42,
  prediction_accuracy: 88.2,
};

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("Experiments page", () => {
  it("runs a comparison and renders both systems", async () => {
    apiPost
      .mockResolvedValueOnce({ data: { id: 12 } } as never)
      .mockResolvedValueOnce({ data: [baseline, proposed] } as never);

    render(<Experiments />);
    fireEvent.click(screen.getByRole("button", { name: "Run Comparison" }));

    expect(await screen.findByText("Results: Sudden Spike")).toBeTruthy();
    expect(screen.getByText("BASELINE")).toBeTruthy();
    expect(screen.getByText("PROPOSED")).toBeTruthy();
    expect(screen.getByText("Avg Memory")).toBeTruthy();

    expect(apiPost).toHaveBeenNthCalledWith(
      1,
      "/api/experiments",
      {
        name: "Sudden Spike comparison",
        workload_type: "Sudden Spike",
        duration_seconds: 60,
        seed: 42,
      },
    );
    expect(apiPost).toHaveBeenNthCalledWith(
      2,
      "/api/experiments/12/start",
    );
  });

  it("shows a visible error when the comparison API fails", async () => {
    apiPost.mockRejectedValueOnce(new Error("backend unavailable"));

    render(<Experiments />);
    fireEvent.click(screen.getByRole("button", { name: "Run Comparison" }));

    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(
      screen.getByText(/Unable to run the comparison/i),
    ).toBeTruthy();
  });
});
