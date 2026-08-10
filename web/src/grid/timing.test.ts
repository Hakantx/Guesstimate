import { describe, expect, it } from "vitest";
import { MAX_MS, MIN_MS, collapseDuration, columnDelay } from "./timing";

describe("collapseDuration", () => {
  it("is zero when nothing dies", () => {
    expect(collapseDuration(0, 3024)).toBe(0);
  });

  it("gives a big sweep longer than a small one", () => {
    expect(collapseDuration(2184, 3024)).toBeGreaterThan(
      collapseDuration(10, 3024),
    );
  });

  it("is sub-linear, so the endgame does not crawl", () => {
    // Four times the kills should be about twice the duration, not four
    // times. Otherwise a 10-cell endgame is as slow as a 2000-cell collapse
    // in proportion, and the game feels stalled after the opening.
    const small = collapseDuration(100, 3024) - MIN_MS;
    const large = collapseDuration(400, 3024) - MIN_MS;
    expect(large / small).toBeCloseTo(2, 1);
  });

  it("stays inside its bounds", () => {
    for (const killed of [1, 10, 500, 2184, 3023, 3024]) {
      const ms = collapseDuration(killed, 3024);
      expect(ms).toBeGreaterThanOrEqual(MIN_MS);
      expect(ms).toBeLessThanOrEqual(MAX_MS);
    }
  });

  it("separates the turn-one cases the data actually produces", () => {
    // The opening splits 3024 into buckets of 1..840, so "turn one" is not one
    // event. The modal case kills 2184 and the luckiest kills 3023; those must
    // not look identical.
    const modal = collapseDuration(3024 - 840, 3024);
    const lucky = collapseDuration(3024 - 1, 3024);
    expect(lucky - modal).toBeGreaterThan(80);
  });

  it("gives a later turn much less time than the opening", () => {
    const opening = collapseDuration(2184, 3024); // 3024 -> 840
    const later = collapseDuration(840 - 89, 3024); // 840 -> ~89
    expect(later).toBeLessThan(opening);
  });
});

describe("columnDelay", () => {
  it("sweeps left to right", () => {
    expect(columnDelay(0, 63)).toBe(0);
    expect(columnDelay(62, 63)).toBeGreaterThan(columnDelay(31, 63));
  });

  it("leaves most of the duration for the fade itself", () => {
    expect(columnDelay(62, 63)).toBeLessThan(0.6);
  });

  it("handles a single column", () => {
    expect(columnDelay(0, 1)).toBe(0);
  });
});
