import type { GameState } from "../api/client";

/**
 * The turns played so far.
 *
 * Feedback is shown as pips as well as text, so it survives a screenshot, a
 * colourblind reader, and a terminal-style theme: a filled dot is a bull, a
 * hollow one a cow.
 */
export function Board({ state }: { state: GameState }) {
  return (
    <ol className="board">
      {state.turns.map((turn, index) => {
        const [bulls, cows] = turn.feedback
          .slice(1)
          .split("-")
          .map((n) => Number.parseInt(n, 10));
        return (
          <li key={`${turn.guess}-${index}`}>
            <span className="turn-number">{index + 1}</span>
            <span className="code">{turn.guess}</span>
            <span className="score">{turn.feedback}</span>
            <span className="pips" aria-hidden="true">
              {"●".repeat(bulls ?? 0)}
              {"○".repeat(cows ?? 0)}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
