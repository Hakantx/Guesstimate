import type { components } from "../api/types";

type Ruleset = components["schemas"]["RulesetSchema"];

/**
 * Whether a typed code is playable, checked before it is sent.
 *
 * This reads the ruleset the server served -- its length, its alphabet, its
 * repeats flag -- and applies those parameters. It does not re-derive any rule
 * the server could have stated: `space_size` used to be computed here from a
 * falling factorial and is now served, because a formula rewritten in a second
 * language diverges somewhere no Python test can reach.
 *
 * The server validates again and is the authority. This exists so an obvious
 * typo gets an answer without a round trip, not so anything can rely on it.
 */
export function validate(guess: string, ruleset: Ruleset): string | null {
  const symbols = [...guess];

  if (symbols.length !== ruleset.length) {
    return `Needs ${ruleset.length} symbols.`;
  }
  for (const symbol of symbols) {
    if (!ruleset.alphabet.includes(symbol)) {
      return `${symbol} is not one of ${ruleset.alphabet}.`;
    }
  }
  if (!ruleset.allow_repeats && new Set(symbols).size !== symbols.length) {
    return "No repeated symbols.";
  }
  return null;
}
