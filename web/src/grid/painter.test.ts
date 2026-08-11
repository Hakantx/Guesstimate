import { describe, expect, it } from "vitest";
import { collapseBetween } from "./collapse";
import { cellState, sweepDuration } from "./painter";

const frameAt = (progress: number) => ({
  alive: new Set([3]),
  collapse: collapseBetween([0, 1, 2, 3], [3], 2),
  progress,
});

describe("cellState", () => {
  it("keeps survivors alive throughout", () => {
    expect(cellState(3, frameAt(0))).toBe("alive");
    expect(cellState(3, frameAt(1))).toBe("alive");
  });

  it("walks a doomed cell from alive to dying to dead", () => {
    const seen = new Set(
      [0, 0.3, 0.6, 1].map((p) => cellState(0, frameAt(p))),
    );
    expect(seen.has("dead")).toBe(true);
  });

  it("treats a cell with no collapse record as already dead", () => {
    expect(cellState(9, { alive: new Set(), collapse: null, progress: 0.5 })).toBe(
      "dead",
    );
  });

  it("has everything settled once the sweep completes", () => {
    for (const index of [0, 1, 2, 3]) {
      const state = cellState(index, frameAt(1));
      expect(state === "alive" || state === "dead").toBe(true);
    }
  });
});

describe("sweepDuration", () => {
  it("animates normally by default", () => {
    expect(sweepDuration(900, false)).toBe(900);
  });

  it("does not animate at all under prefers-reduced-motion", () => {
    // Zero, not "faster". The setting asks for things not to move; a quick
    // animation is still an animation.
    expect(sweepDuration(900, true)).toBe(0);
  });

  it("settles immediately when reduced, so nothing is mid-transition", () => {
    const duration = sweepDuration(900, true);
    const progress = duration === 0 ? 1 : 0;
    expect(cellState(0, { ...frameAt(progress), progress })).toBe("dead");
  });
});
