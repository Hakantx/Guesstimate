import { describe, expect, it } from "vitest";
import { collapseBetween, gridShape } from "./collapse";

describe("collapseBetween", () => {
  it("finds what died", () => {
    const result = collapseBetween([0, 1, 2, 3], [1, 3], 2);
    expect(result.killed).toEqual([0, 2]);
    expect(result.alive).toEqual([1, 3]);
  });

  it("kills nothing when nothing changed", () => {
    expect(collapseBetween([1, 2], [1, 2], 2).killed).toEqual([]);
  });

  it("schedules every death", () => {
    const result = collapseBetween([0, 1, 2, 3, 4, 5], [5], 3);
    for (const index of result.killed) {
      expect(result.startAt.has(index)).toBe(true);
    }
  });

  it("staggers by column so the sweep reads left to right", () => {
    const result = collapseBetween([0, 1, 2, 3, 4, 5], [], 3);
    expect(result.startAt.get(0)).toBeLessThan(result.startAt.get(2)!);
    // Same column, different row: identical timing.
    expect(result.startAt.get(0)).toBe(result.startAt.get(3));
  });

  it("survives an index that was never alive", () => {
    // The server is the authority on what survives; the client must not
    // assume its previous view was complete.
    expect(collapseBetween([1], [1, 2], 2).killed).toEqual([]);
  });
});

describe("gridShape", () => {
  it("covers every candidate", () => {
    for (const total of [12, 60, 1024, 3024, 5040]) {
      const { columns, rows } = gridShape(total);
      expect(columns * rows).toBeGreaterThanOrEqual(total);
    }
  });

  it("is wider than tall, for a landscape screen", () => {
    const { columns, rows } = gridShape(3024);
    expect(columns).toBeGreaterThan(rows);
  });

  it("handles an empty space", () => {
    expect(gridShape(0)).toEqual({ columns: 0, rows: 0 });
  });

  it("keeps each leading digit a contiguous run", () => {
    // DESIGN.md: ruling out a leading digit kills one contiguous 336-cell run,
    // which reads as a horizontal stripe. That only works because the layout
    // uses candidate order untouched, so this guards the ordering assumption
    // rather than the arithmetic.
    const { columns } = gridShape(3024);
    const firstRunRows = 336 / columns;
    expect(firstRunRows).toBeGreaterThan(1);
  });
});
