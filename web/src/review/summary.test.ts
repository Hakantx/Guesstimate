import { describe, expect, it } from "vitest";
import type { MoveReview } from "../api/client";
import { explain, explainProbe, perfectMoves, worstMove } from "./summary";

const move = (over: Partial<MoveReview>): MoveReview => ({
  turn: 1,
  guess: "1234",
  feedback: "+1-0",
  survivors_before: 3024,
  survivors_after: 500,
  eliminated: 2524,
  expected_remaining: 500,
  bits_gained: 2.5,
  best_candidate_remaining: 500,
  best_any_remaining: 500,
  best_candidate: "1234",
  best_any: "1234",
  probe_advantage: 0,
  probe_matters: false,
  loss: 0,
  grade: "best",
  ...over,
});

describe("worstMove", () => {
  it("is null when every move was the best available", () => {
    expect(worstMove([move({}), move({ turn: 2 })])).toBeNull();
  });

  it("picks the largest loss, not the first mistake", () => {
    const moves = [
      move({ turn: 1, loss: 3 }),
      move({ turn: 2, loss: 57 }),
      move({ turn: 3, loss: 9 }),
    ];
    expect(worstMove(moves)?.turn).toBe(2);
  });

  it("ignores moves that gave up nothing", () => {
    const moves = [move({ turn: 1, loss: 0 }), move({ turn: 2, loss: 0.5 })];
    expect(worstMove(moves)?.turn).toBe(2);
  });
});

describe("perfectMoves", () => {
  it("counts the moves that lost nothing", () => {
    expect(perfectMoves([move({}), move({ loss: 4 }), move({})])).toBe(2);
  });
});

describe("explain", () => {
  it("talks in candidates, not in metric units", () => {
    const text = explain(
      move({ guess: "5678", expected_remaining: 96.8, best_candidate_remaining: 39.5, best_candidate: "1234" }),
    );
    expect(text).toContain("5678");
    expect(text).toContain("96.8");
    expect(text).toContain("39.5");
    expect(text).not.toMatch(/loss|expected_remaining/i);
  });
});

describe("explainProbe", () => {
  it("says nothing when the probe was not meaningfully better", () => {
    expect(explainProbe(move({ probe_matters: false }))).toBeNull();
  });

  it("explains the case that teaches something", () => {
    const text = explainProbe(
      move({ probe_matters: true, best_any: "4321", best_any_remaining: 35.8 }),
    );
    expect(text).toContain("4321");
    expect(text).toContain("35.8");
    expect(text).toMatch(/could not have won/);
  });

  it("says nothing when the server sent no alternative", () => {
    expect(explainProbe(move({ probe_matters: true, best_any: null }))).toBeNull();
  });
});
