/**
 * What colour each cell is at a given moment.
 *
 * Split out of the paint loop so it can be tested without a canvas. The loop
 * owns pixels; this owns the decision, including the one that matters for
 * accessibility — whether any of it animates at all.
 */
import type { Collapse } from "./collapse";

export type CellState = "alive" | "dying" | "dead";

export interface Frame {
  readonly alive: ReadonlySet<number>;
  readonly collapse: Collapse | null;
  /** 0..1 through the sweep. */
  readonly progress: number;
}

export function cellState(index: number, frame: Frame): CellState {
  if (frame.alive.has(index)) return "alive";
  const start = frame.collapse?.startAt.get(index);
  if (start === undefined) return "dead";

  const local = (frame.progress - start) / Math.max(0.001, 1 - start);
  if (local <= 0) return "alive";
  return local < 1 ? "dying" : "dead";
}

/**
 * How long the sweep runs, honouring the OS setting.
 *
 * `prefers-reduced-motion` means no sweep at all rather than a faster one: the
 * grid snaps to its new state. A shortened animation is still animation, and
 * the setting is a request not to move things, not a request to move them
 * briskly.
 */
export function sweepDuration(base: number, reducedMotion: boolean): number {
  return reducedMotion ? 0 : base;
}
