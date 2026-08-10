import { Board } from "../board/Board";
import { GuessInput } from "../board/GuessInput";
import { useRaceGame } from "../game/useRaceGame";
import { CandidateGrid } from "../grid/CandidateGrid";
import { gridShape } from "../grid/collapse";

/** You and the solver, same secret, turn for turn. */
export function RaceMode() {
  const columns = gridShape(3024).columns;
  const game = useRaceGame(columns);

  if (!game.state) {
    return <p className="waiting">{game.error ?? "Dealing…"}</p>;
  }

  const revealed =
    game.state.secret.kind === "revealed" ? game.state.secret.code : null;

  return (
    <div className="race">
      <CandidateGrid
        total={game.total}
        alive={game.alive}
        collapse={game.collapse}
      />

      <div className="sidebar">
        <div className="two-boards">
          <section>
            <h2>You</h2>
            <Board state={game.state} />
          </section>
          <section>
            <h2>Solver</h2>
            <ol className="board">
              {game.solverTurns.map((turn, index) => (
                <li key={`${turn.guess}-${index}`}>
                  <span className="turn-number">{index + 1}</span>
                  <span className="code">{turn.guess}</span>
                  <span className="score">{turn.feedback}</span>
                </li>
              ))}
            </ol>
          </section>
        </div>

        {game.winner ? (
          <div className="done">
            <p>
              {game.winner === "you" ? "You got it first" : "The solver got it first"}
              {revealed ? ` — the code was ${revealed}` : ""}.
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
