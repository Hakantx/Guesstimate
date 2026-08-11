import { useEffect, useRef } from "react";
import type { Collapse } from "./collapse";
import { cellState, sweepDuration } from "./painter";
import { collapseDuration } from "./timing";

/** Punch-card palette. Kept here so the paint loop never reads CSS. */
const ALIVE = "#2f9e8f";
const DYING = "#7d2b2f";
const DEAD = "#1c1f24";
const BACKDROP = "#0f1115";

export interface GridView {
  readonly total: number;
  readonly columns: number;
  readonly rows: number;
  readonly alive: readonly number[];
  readonly collapse: Collapse | null;
}

/**
 * Paints the candidate grid onto a canvas.
 *
 * Canvas rather than 3024 DOM nodes, and the reason is arithmetic: an element
 * per candidate is three thousand layout objects to animate at once, which no
 * amount of `will-change` rescues. Here the whole grid is one node and one
 * fill per cell per frame.
 *
 * The loop is imperative and lives outside React on purpose. Sixty state
 * updates a second through a reconciler is the same mistake in a different
 * costume; React owns *which game* is on screen, and this owns the pixels.
 */
export function useGridPainter(
  canvas: React.RefObject<HTMLCanvasElement | null>,
  view: GridView,
  reducedMotion: boolean,
): void {
  const frame = useRef(0);
  const started = useRef(0);

  useEffect(() => {
    const element = canvas.current;
    if (!element || view.total === 0) return;
    const context = element.getContext("2d", { alpha: false });
    if (!context) return;

    const { columns, rows, total } = view;
    const aliveNow = new Set(view.alive);
    const collapse = view.collapse;
    const duration = sweepDuration(
      collapseDuration(collapse?.killed.length ?? 0, total),
      reducedMotion,
    );

    const paint = (elapsed: number) => {
      const width = element.width;
      const height = element.height;
      const cell = Math.max(1, Math.floor(Math.min(width / columns, height / rows)));
      const gap = cell > 3 ? 1 : 0;
      const originX = Math.floor((width - cell * columns) / 2);
      const originY = Math.floor((height - cell * rows) / 2);

      context.fillStyle = BACKDROP;
      context.fillRect(0, 0, width, height);

      const progress = duration === 0 ? 1 : Math.min(1, elapsed / duration);
      for (let index = 0; index < total; index += 1) {
        const column = index % columns;
        const row = Math.floor(index / columns);

        const state = cellState(index, { alive: aliveNow, collapse, progress });
        context.fillStyle =
          state === "alive" ? ALIVE : state === "dying" ? DYING : DEAD;
        context.fillRect(
          originX + column * cell,
          originY + row * cell,
          cell - gap,
          cell - gap,
        );
      }
      return progress >= 1;
    };

    started.current = performance.now();
    const tick = (now: number) => {
      const done = paint(now - started.current);
      if (!done) frame.current = requestAnimationFrame(tick);
    };
    frame.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame.current);
  }, [canvas, view, reducedMotion]);
}
