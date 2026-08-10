import { Board } from "../board/Board";
import { GuessInput } from "../board/GuessInput";
import { useCodebreakerGame } from "../game/useCodebreakerGame";
import { CandidateGrid } from "../grid/CandidateGrid";
import { gridShape } from "../grid/collapse";

/**
 * You guess, the app scores.
 *
 * The grid shows what your own guesses have ruled out, which is the same
 * collapse the solver produces and a decent way to see how much a guess was
 * actually worth.
 */
export function CodebreakerMode() {
  const columns = gridShape(3024).columns;
  const game = useCodebreakerGame(columns);

  if (!game.state) {
    return <p className="waiting">{game.error ?? "Dealing\u2026"}</p>;
  }

  const revealed =
    game.state.secret.kind === "revealed" ? game.state.secret.code : null;

  return (
    <div className="codebreaker">
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
            <p>
              Got it in {game.state.turns.length}
              {revealed ? ` \u2014 the code was ${revealed}` : ""}.
            </p>
            <button className="primary" type="button" onClick={() => void game.restart()}>
              Again
            </button>
          </div>
        ) : (
          <GuessInput
            ruleset={game.state.ruleset}
            disabled={game.busy}
            onSubmit={(guess) => void game.submit(guess)}
          />
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
