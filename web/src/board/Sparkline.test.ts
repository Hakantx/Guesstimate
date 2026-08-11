import { describe, expect, it } from "vitest";
import { sparkline } from "./Sparkline";

describe("sparkline", () => {
  it("is empty with no data", () => {
    expect(sparkline([])).toBe("");
  });

  it("has one mark per turn", () => {
    expect(sparkline([3024, 240, 20, 1])).toHaveLength(4);
  });

  it("descends as the set collapses", () => {
    const marks = sparkline([3024, 240, 20, 1]);
    expect(marks).toBe([...marks].sort().reverse().join(""));
  });

  it("is log-scaled, so every order of magnitude is visible", () => {
    // On a linear scale the 3024 -> 240 drop uses the whole range and the rest
    // is flat. Each step should be distinguishable.
    expect(new Set(sparkline([3024, 240, 20, 2])).size).toBe(4);
  });

  it("handles a flat run", () => {
    expect(new Set(sparkline([5, 5, 5])).size).toBe(1);
  });
});
