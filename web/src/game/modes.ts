import type { components } from "../api/types";

/**
 * What each mode can do, mirroring the Python protocol split.
 *
 * The server enforces this — asking a watch game to score a guess is a 409 —
 * but the UI should never offer a control that cannot work. Two independent
 * capabilities, not one hierarchy:
 *
 *   - `scores`: the game can score a code the player submits. True when the
 *     game knows the answer, either by holding a secret or by being entitled
 *     to invent one consistent with what it has already said.
 *   - `solver`: the game has a solver that proposes moves.
 *
 * Watch has the second without the first, which is why `guess` is not a
 * capability every mode has: there the secret is in the player's head, so
 * there is nothing on the server to check a guess against.
 */
export const MODES = {
  codebreaker: { scores: true, solver: false, answers: false },
  watch: { scores: false, solver: true, answers: true },
  race: { scores: true, solver: true, answers: false },
  evil: { scores: true, solver: false, answers: false },
} as const satisfies Record<string, Capabilities>;

export interface Capabilities {
  /** The player submits codes and the game scores them. */
  readonly scores: boolean;
  /** The game proposes moves of its own. */
  readonly solver: boolean;
  /** The player scores the game's guesses, rather than the other way round. */
  readonly answers: boolean;
}

export type Mode = keyof typeof MODES;

/** Modes the server accepts today. `evil` is specced but not yet built. */
export type ServerMode = NonNullable<
  components["schemas"]["NewGameRequest"]["mode"]
>;

export const MODE_ORDER = ["codebreaker", "watch", "race", "evil"] as const;

export function capabilities(mode: Mode): Capabilities {
  return MODES[mode];
}

/**
 * Whether the server can start this mode yet.
 *
 * All four are now served. This stays as the one place the client and the API
 * could disagree about what exists, so a mode added to the taxonomy before the
 * server accepts it has somewhere to be declared rather than failing at
 * runtime.
 */
export function isImplemented(mode: Mode): mode is Mode & ServerMode {
  return MODE_ORDER.includes(mode as (typeof MODE_ORDER)[number]);
}
