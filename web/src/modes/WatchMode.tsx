import { Board } from "../board/Board";
import { FeedbackInput } from "../board/FeedbackInput";
import { useWatchGame } from "../game/useWatchGame";
import { CandidateGrid } from "../grid/CandidateGrid";
import { gridShape } from "../grid/collapse";

/**
 * Watch the solver: it guesses, you score.
 *
 * The original game, and the mode the whole design is arranged around — the
 * candidate grid collapsing is the thing worth showing, and this is where it
 * is visible turn by turn.
 */
export function WatchMode() {
  const columns = gridShape(3024).columns;
  const game = useWatchGame(columns);

  if (!game.state) {
    return <p className="waiting">{game.error ?? "Dealing…"}</p>;
  }

  return (
    <div className="watch">
      <CandidateGrid
        total={game.total}
        alive={game.alive}
        collapse={game.collapse}
      />

      <div className="sidebar">
        <p className="count">
          <strong>{game.alive.length.toLocaleString()}</strong> of{" "}
          {game.total.toLocaleString()} still possible
        </p>

        <Board state={game.state} />

        {game.state.finished ? (
          <div className="done">
            <p>Got it in {game.state.turns.length}.</p>
            <button type="button" onClick={() => void game.restart()}>
              Again
            </button>
          </div>
        ) : (
          game.guess && (
            <FeedbackInput
              guess={game.guess}
              disabled={game.busy}
              onAnswer={(feedback) => void game.answer(feedback)}
            />
          )
        )}

        {game.error && (
          <p className="error" role="alert">
            {game.error}
          </p>
        )}
      </div>
    </div>
  );
}
