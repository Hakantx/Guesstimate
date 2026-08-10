import { useState } from "react";

interface Props {
  guess: string;
  disabled: boolean;
  onAnswer(feedback: string): void;
}

const BULLS = [0, 1, 2, 3, 4];

/**
 * Answering the solver.
 *
 * Buttons rather than a text field. `+B-C` is the engine's format and the CLI
 * parses it from typing, but a player scoring by hand should not have to learn
 * a syntax to play — and the impossible combinations can simply not be
 * offered. `+3-1` is unreachable for a length-4 code, so it is not a button.
 */
export function FeedbackInput({ guess, disabled, onAnswer }: Props) {
  const [bulls, setBulls] = useState<number | null>(null);

  const cowsFor = (chosen: number): number[] => {
    const room = 4 - chosen;
    // One bull short of a win forces zero cows: the odd symbol cannot also be
    // somewhere else. See docs/notes/impossible-outcome.md.
    return chosen === 3 ? [0] : Array.from({ length: room + 1 }, (_, i) => i);
  };

  return (
    <div className="feedback">
      <p>
        My guess is <strong>{guess}</strong>. How did I do?
      </p>
      <fieldset disabled={disabled}>
        <legend>Correct and in place</legend>
        {BULLS.map((n) => (
          <button
            key={n}
            type="button"
            aria-pressed={bulls === n}
            onClick={() => (n === 4 ? onAnswer("+4-0") : setBulls(n))}
          >
            {n}
          </button>
        ))}
      </fieldset>
      {bulls !== null && bulls < 4 && (
        <fieldset disabled={disabled}>
          <legend>Correct but misplaced</legend>
          {cowsFor(bulls).map((c) => (
            <button
              key={c}
              type="button"
              onClick={() => {
                onAnswer(`+${bulls}-${c}`);
                setBulls(null);
              }}
            >
              {c}
            </button>
          ))}
        </fieldset>
      )}
    </div>
  );
}
