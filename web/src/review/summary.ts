import type { MoveReview } from "../api/client";

/**
 * Which move to lead with.
 *
 * The one that gave up the most, not the first one. A review that opens with a
 * list of eight rows where six say "best" has buried its only useful sentence
 * at position seven; chess engines open on the blunder for the same reason.
 *
 * Null when nothing was given up at all, which is a different and much shorter
 * thing to say.
 */
export function worstMove(moves: readonly MoveReview[]): MoveReview | null {
  let worst: MoveReview | null = null;
  for (const move of moves) {
    if (move.loss <= 0) continue;
    if (worst === null || move.loss > worst.loss) worst = move;
  }
  return worst;
}

/** How many moves were the best available. */
export function perfectMoves(moves: readonly MoveReview[]): number {
  return moves.filter((move) => move.loss <= 0).length;
}

const ROUNDED = new Intl.NumberFormat("en", { maximumFractionDigits: 1 });

export function count(value: number): string {
  return ROUNDED.format(value);
}

/**
 * The sentence under the headline move.
 *
 * Phrased in candidates rather than in the metric's units. "Left 97 where 40
 * was available" is something a player can picture; "expected remaining 96.8,
 * loss 57.3" has to be taught first.
 */
export function explain(move: MoveReview): string {
  const played = count(move.expected_remaining);
  const best = count(move.best_candidate_remaining);
  return (
    `${move.guess} left about ${played} codes standing on average. ` +
    `${move.best_candidate ?? "another guess"} would have left ${best}.`
  );
}

/**
 * The extra line, shown only when a guess that could not win was the better
 * play.
 *
 * The server decides when that is worth saying, using the same threshold that
 * decides whether a move loses its perfect grade. On most turns the best guess
 * overall *is* the best candidate, the two numbers are identical, and a column
 * repeating that is a column nobody reads.
 */
export function explainProbe(move: MoveReview): string | null {
  if (!move.probe_matters || move.best_any === null) return null;
  return (
    `${move.best_any} could not have won this turn, but would have left ` +
    `${count(move.best_any_remaining)} — fewer than any guess that could. ` +
    `Spending a turn on information sometimes beats trying to finish.`
  );
}
