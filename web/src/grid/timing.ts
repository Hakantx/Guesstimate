/**
 * How long a collapse should take, given how much of it dies.
 *
 * Driving this from the turn number is the obvious approach and it is wrong.
 * Measured over all 3024 secrets, the opening leaves anywhere from 1 to 840
 * candidates alive depending on which of its fourteen buckets the player's
 * secret falls into — so "turn one" is not one event. The same nominal turn
 * kills 2,184 cells in the modal case and 3,023 in the luckiest one, and a
 * fixed duration makes one of those crawl or the other flash past.
 *
 * The curve is sub-linear so that a 2,000-cell sweep reads as dramatic without
 * a 10-cell endgame taking a comparable time. A square root does that: four
 * times the kills is twice the duration.
 */
export const MIN_MS = 180;
export const MAX_MS = 1400;

/** Milliseconds the sweep should last when `killed` cells go dark. */
export function collapseDuration(killed: number, total: number): number {
  if (killed <= 0 || total <= 0) return 0;
  const share = Math.min(1, killed / total);
  return Math.round(MIN_MS + (MAX_MS - MIN_MS) * Math.sqrt(share));
}

/**
 * When each cell in a column-ordered sweep should start dying, as a fraction
 * of the total duration. Columns go dark left to right, which reads as a wipe
 * rather than as static noise.
 */
export function columnDelay(column: number, columns: number): number {
  if (columns <= 1) return 0;
  return Math.min(1, Math.max(0, column / (columns - 1))) * 0.55;
}
