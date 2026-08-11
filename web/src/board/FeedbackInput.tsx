import { useMemo, useState } from "react";

interface Props {
  guess: string;
  /** Reachable answers for this ruleset, as `+B-C`. From the server. */
  outcomes: readonly string[];
  disabled: boolean;
  onAnswer(feedback: string): void;
}

interface Parsed {
  readonly text: string;
  readonly bulls: number;
  readonly cows: number;
}

function parse(outcome: string): Parsed | null {
  const match = /^\+(\d+)-(\d+)$/.exec(outcome);
  if (!match) return null;
  return {
    text: outcome,
    bulls: Number.parseInt(match[1]!, 10),
    cows: Number.parseInt(match[2]!, 10),
  };
}

/**
 * Answering the solver.
 *
 * Buttons rather than a text field: `+B-C` is the engine's format and the CLI
 * parses it from typing, but a player scoring by hand should not have to learn
 * a syntax.
 *
 * Which buttons exist comes from the server and is never computed here. Which
 * answers a ruleset can produce is not a function of the code length — it
 * depends on the alphabet too. Four positions over two symbols with repeats
 * reaches nine answers, not the fourteen a bulls-plus-cows triangle suggests,
 * so a rule written in this file would offer five buttons that can never be
 * correct. The server enumerates the set by brute force and has the tests to
 * prove it; the UI renders what it is told.
 */
export function FeedbackInput({ guess, outcomes, disabled, onAnswer }: Props) {
  const [bulls, setBulls] = useState<number | null>(null);

  const parsed = useMemo(
    () => outcomes.map(parse).filter((o): o is Parsed => o !== null),
    [outcomes],
  );
  const bullOptions = useMemo(
    () => [...new Set(parsed.map((o) => o.bulls))].sort((a, b) => a - b),
    [parsed],
  );
  const cowOptions = useMemo(
    () =>
      bulls === null
        ? []
        : parsed.filter((o) => o.bulls === bulls).sort((a, b) => a.cows - b.cows),
    [parsed, bulls],
  );

  // A bull count with only one possible cow count needs no second question.
  const answerDirectly = (count: number): string | null => {
    const matching = parsed.filter((o) => o.bulls === count);
    return matching.length === 1 ? matching[0]!.text : null;
  };

  return (
    <div className="feedback">
      <p>
        My guess is <strong className="code">{guess}</strong>. How did I do?
      </p>

      <fieldset disabled={disabled}>
        <legend>Right digit, right place</legend>
        {bullOptions.map((count) => (
          <button
            key={count}
            type="button"
            aria-pressed={bulls === count}
            onClick={() => {
              const direct = answerDirectly(count);
              if (direct) {
                onAnswer(direct);
                setBulls(null);
              } else {
                setBulls(count);
              }
            }}
          >
            {count}
          </button>
        ))}
      </fieldset>

      {cowOptions.length > 1 && (
        <fieldset disabled={disabled}>
          <legend>Right digit, wrong place</legend>
          {cowOptions.map((outcome) => (
            <button
              key={outcome.text}
              type="button"
              onClick={() => {
                onAnswer(outcome.text);
                setBulls(null);
              }}
            >
              {outcome.cows}
            </button>
          ))}
        </fieldset>
      )}
    </div>
  );
}
