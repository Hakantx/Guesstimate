import { useEffect, useRef, useState } from "react";
import type { Collapse } from "./collapse";
import { gridShape } from "./collapse";
import { useGridPainter } from "./useGridPainter";

interface Props {
  total: number;
  alive: readonly number[];
  collapse: Collapse | null;
}

/** Reads the OS setting once and follows it. */
function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(query.matches);
    const listen = (event: MediaQueryListEvent) => setReduced(event.matches);
    query.addEventListener("change", listen);
    return () => query.removeEventListener("change", listen);
  }, []);
  return reduced;
}

/**
 * Every candidate, as one cell, in candidate order.
 *
 * The ordering is the engine's own, which is what makes the grid explanatory:
 * each leading digit is a contiguous run, so ruling one out darkens a solid
 * horizontal band and the player sees *which* deduction happened. DESIGN.md
 * says not to re-sort this, and it means it.
 */
export function CandidateGrid({ total, alive, collapse }: Props) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const { columns, rows } = gridShape(total);
  const reduced = usePrefersReducedMotion();

  useEffect(() => {
    const element = canvas.current;
    if (!element) return;
    const resize = () => {
      const box = element.getBoundingClientRect();
      const scale = window.devicePixelRatio || 1;
      element.width = Math.floor(box.width * scale);
      element.height = Math.floor(box.height * scale);
    };
    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  useGridPainter(canvas, { total, columns, rows, alive, collapse }, reduced);

  // `img` with a label, because that is the most a canvas can honestly claim:
  // its contents are pixels and there is nothing inside for a reader to walk.
  // The numbers it depicts are announced by `Announcer` through a live region,
  // so nothing here is the only route to the information.
  return (
    <canvas
      ref={canvas}
      className="candidate-grid"
      role="img"
      aria-label={
        `Candidate grid: ${alive.length.toLocaleString()} of ` +
        `${total.toLocaleString()} codes still possible. Each cell is one code; ` +
        `cells go dark as codes are ruled out.`
      }
    />
  );
}
