/**
 * Which cells die this turn, and when.
 *
 * Pure, and deliberately outside the render loop: deciding what the animation
 * shows is the part with behaviour worth testing, and it should not need a
 * canvas or a GPU to check.
 */
import { columnDelay } from "./timing";

export interface Collapse {
  /** Indices that were alive and are not any more. */
  readonly killed: readonly number[];
  /** Indices still alive after this turn. */
  readonly alive: readonly number[];
  /** For each killed index, when to start its fade, as a 0..1 fraction. */
  readonly startAt: ReadonlyMap<number, number>;
}

/**
 * Difference two candidate sets.
 *
 * Both come from the server as positions in `all_candidates(ruleset)`, which
 * is also the grid's layout order — so an index is a cell, with no lookup
 * table on either side.
 */
export function collapseBetween(
  previous: readonly number[],
  next: readonly number[],
  columns: number,
): Collapse {
  const surviving = new Set(next);
  const killed: number[] = [];
  for (const index of previous) {
    if (!surviving.has(index)) killed.push(index);
  }

  const startAt = new Map<number, number>();
  for (const index of killed) {
    startAt.set(index, columnDelay(index % columns, columns));
  }
  return { killed, alive: next, startAt };
}

/** Grid geometry for a candidate space, as square as it can be made. */
export function gridShape(total: number): { columns: number; rows: number } {
  if (total <= 0) return { columns: 0, rows: 0 };
  const columns = Math.ceil(Math.sqrt(total * 1.3));
  return { columns, rows: Math.ceil(total / columns) };
}
