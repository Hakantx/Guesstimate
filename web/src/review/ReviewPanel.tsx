import { useEffect, useState } from "react";
import { ApiError, api } from "../api/client";
import type { Analysis, MoveReview } from "../api/client";
import { count, explain, explainProbe, perfectMoves, worstMove } from "./summary";

const LABELS: Record<string, string> = {
  best: "Best",
  good: "Good",
  inaccuracy: "Inaccuracy",
  mistake: "Mistake",
  blunder: "Blunder",
};

/**
 * How the game went, opening on the move that cost the most.
 *
 * Not a table of every turn with the interesting one buried in the middle. Six
 * rows saying "best" teach nothing; the one that gave something up is the only
 * part that is actionable, so it goes first, in a sentence, with the full list
 * underneath for anyone who wants it.
 */
export function ReviewPanel({ gameId }: { gameId: string }) {
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    let live = true;
    api
      .analysis(gameId)
      .then((body) => live && setAnalysis(body))
      .catch((caught) =>
        live && setError(caught instanceof ApiError ? caught.detail : String(caught)),
      );
    return () => {
      live = false;
    };
  }, [gameId]);

  if (error) return <p className="error">{error}</p>;
  if (!analysis || analysis.moves.length === 0) return null;

  const moves = analysis.moves;
  const worst = worstMove(moves);
  const perfect = perfectMoves(moves);
  const probeLine = worst ? explainProbe(worst) : null;

  return (
    <section className="review" aria-labelledby="review-heading">
      <h2 id="review-heading">How that went</h2>

      {worst === null ? (
        <p className="verdict">
          Every guess was the best available. There was nothing better to play.
        </p>
      ) : (
        <div className="verdict">
          <p>
            <span className={`grade grade-${worst.grade}`}>
              {LABELS[worst.grade] ?? worst.grade}
            </span>{" "}
            Your costliest move was <strong>turn {worst.turn}</strong>.
          </p>
          <p>{explain(worst)}</p>
          {probeLine && <p className="probe">{probeLine}</p>}
          <p className="tally">
            {perfect} of {moves.length} moves were the best available.
          </p>
        </div>
      )}

      <button
        type="button"
        aria-expanded={expanded}
        onClick={() => setExpanded((open) => !open)}
      >
        {expanded ? "Hide every move" : "Show every move"}
      </button>

      {expanded && <MoveTable moves={moves} />}
    </section>
  );
}

function MoveTable({ moves }: { moves: readonly MoveReview[] }) {
  // The probe column exists only if some move actually has one worth showing.
  // A column of identical numbers is a column that gets ignored, and then the
  // one row where it differs gets ignored with it.
  const anyProbe = moves.some((move) => move.probe_matters);

  return (
    <table className="moves">
      <thead>
        <tr>
          <th scope="col">#</th>
          <th scope="col">Guess</th>
          <th scope="col">Score</th>
          <th scope="col">Left</th>
          <th scope="col">Best</th>
          {anyProbe && <th scope="col">Probe</th>}
          <th scope="col">Grade</th>
        </tr>
      </thead>
      <tbody>
        {moves.map((move) => (
          <tr key={move.turn}>
            <td>{move.turn}</td>
            <td className="code">{move.guess}</td>
            <td className="score">{move.feedback}</td>
            <td>{count(move.expected_remaining)}</td>
            <td>
              {count(move.best_candidate_remaining)}
              {move.best_candidate && move.loss > 0 && (
                <span className="hint"> {move.best_candidate}</span>
              )}
            </td>
            {anyProbe && (
              <td>
                {move.probe_matters ? (
                  <>
                    {count(move.best_any_remaining)}
                    <span className="hint"> {move.best_any}</span>
                  </>
                ) : (
                  <span className="hint" aria-label="no better probe">
                    —
                  </span>
                )}
              </td>
            )}
            <td>
              <span className={`grade grade-${move.grade}`}>
                {LABELS[move.grade] ?? move.grade}
              </span>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
