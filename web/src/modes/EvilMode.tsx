import { Board } from "../board/Board";
import { GuessInput } from "../board/GuessInput";
import { useCodebreakerGame } from "../game/useCodebreakerGame";
import { CandidateGrid } from "../grid/CandidateGrid";
import { gridShape } from "../grid/collapse";

/**
 * Evil mode: there is no code.
 *
 * The component is the small half. Everything that makes this mode what it is
 * lives on the server -- the adversary that answers with whichever reply keeps
 * the most codes alive and commits to nothing until cornered. Here it is a
 * codebreaker game with different words around it, which is the point: the
 * player cannot tell from the outside, and that is exactly the experience.
 */
export function EvilMode() {
  const columns = gridShape(3024).columns;
  const game = useCodebreakerGame(columns, "evil");

  if (!game.state) {
    return <p className="waiting">{game.error ?? "Thinking of nothing…"}</p>;
  }

  const forced = game.state.finished && game.alive.length === 1;

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
        <p className="aside">
          I have not picked a code. Every answer I give is true of something
          still on the board — I am simply choosing the least helpful one.
        </p>

        <Board state={game.state} />

        {game.state.finished ? (
          <div className="done">
            <p>
              You cornered me in {game.state.turns.length}
              {forced
                ? ` — ${game.state.turns[game.state.turns.length - 1]?.guess} was the only code left.`
                : "."}
            </p>
            <p className="aside">There was never a code. You forced one.</p>
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
