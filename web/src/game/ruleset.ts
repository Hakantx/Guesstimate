import type { components } from "../api/types";

type Ruleset = components["schemas"]["RulesetSchema"];

/**
 * How many codes a ruleset allows.
 *
 * Mirrors `Ruleset.space_size` in the engine, written as the same explicit
 * loop rather than a factorial or a power: with repeats every position is a
 * free choice, without them each consumes a symbol. Duplicated across the
 * language boundary because the grid needs it before any request completes,
 * and it is four lines that the cross-language test suite in MOBILE.md will
 * eventually cover.
 */
export function spaceSize(ruleset: Ruleset): number {
  const symbols = ruleset.alphabet?.length ?? 0;
  const length = ruleset.length ?? 0;
  let size = 1;
  for (let taken = 0; taken < length; taken += 1) {
    size *= ruleset.allow_repeats ? symbols : symbols - taken;
  }
  return size;
}

/** Whether a typed code is playable, without asking the server. */
export function validate(guess: string, ruleset: Ruleset): string | null {
  const alphabet = ruleset.alphabet ?? "";
  const length = ruleset.length ?? 0;
  const symbols = [...guess];

  if (symbols.length !== length) {
    return `Needs ${length} symbols.`;
  }
  for (const symbol of symbols) {
    if (!alphabet.includes(symbol)) {
      return `${symbol} is not one of ${alphabet}.`;
    }
  }
  if (!ruleset.allow_repeats && new Set(symbols).size !== symbols.length) {
    return "No repeated symbols.";
  }
  return null;
}
