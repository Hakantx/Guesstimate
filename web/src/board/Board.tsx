import type { GameState } from "../api/client";

/**
 * The turns played so far.
 *
 * Feedback is shown as pips as well as text, so it survives a screenshot, a
 * colourblind reader, and a printout: a filled dot is a bull, a hollow one a
 * cow. DESIGN.md requires teal and mustard to be paired with a shape
 * difference, and this is where that lands.
 */
export function Board({ state }: { state: GameState }) {
  return (
    <ol className="board">
      {state.turns.map((turn, index) => {
        const match = /^\+(\d+)-(\d+)$/.exec(turn.feedback);
        const bulls = match ? Number.parseInt(match[1]!, 10) : 0;
        const cows = match ? Number.parseInt(match[2]!, 10) : 0;
        return (
          <li key={`${turn.guess}-${index}`}>
            <span className="turn-number">{index + 1}</span>
            <span className="code">{turn.guess}</span>
            <span className="score">{turn.feedback}</span>
            <span className="pips">
              <span className="bull" aria-hidden="true">{"\u25cf".repeat(bulls)}</span>
              <span className="cow" aria-hidden="true">{"\u25cb".repeat(cows)}</span>
              <span className="visually-hidden">
                {bulls} in place, {cows} misplaced
              </span>
            </span>
          </li>
        );
      })}
    </ol>
  );
}
