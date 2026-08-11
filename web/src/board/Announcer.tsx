import { useEffect, useRef, useState } from "react";
import type { GameState } from "../api/client";

interface Props {
  state: GameState;
  surviving: number;
  /** What the solver just played, in modes where it moves. */
  solverGuess?: string | null;
}

function spell(feedback: string): string {
  const match = /^\+(\d+)-(\d+)$/.exec(feedback);
  if (!match) return feedback;
  const bulls = Number.parseInt(match[1]!, 10);
  const cows = Number.parseInt(match[2]!, 10);
  const parts = [
    `${bulls} in the right place`,
    `${cows} in the wrong place`,
  ];
  return parts.join(", ");
}

/**
 * Everything the grid shows, said out loud.
 *
 * The candidate grid is a canvas: to a screen reader it is one image with a
 * label and nothing inside it, and no amount of ARIA on a canvas element makes
 * three thousand rectangles legible. So the information the grid carries —
 * how much was eliminated, and by what — is announced here instead, and the
 * game is fully playable without it.
 *
 * `polite` rather than `assertive`: a turn is not an emergency, and
 * interrupting someone mid-sentence to tell them a number is worse than
 * waiting for a pause.
 */
export function Announcer({ state, surviving, solverGuess }: Props) {
  const [message, setMessage] = useState("");
  const lastTurn = useRef(0);

  useEffect(() => {
    const turns = state.turns.length;
    const latest = turns > 0 ? state.turns[turns - 1] : null;

    if (turns === lastTurn.current && !state.finished) return;
    lastTurn.current = turns;

    if (state.finished) {
      const revealed =
        state.secret.kind === "revealed" ? `, the code was ${state.secret.code}` : "";
      const never =
        state.secret.kind === "never"
          ? ", and there was never a code — you forced one"
          : "";
      setMessage(`Finished in ${turns} guesses${revealed}${never}.`);
      return;
    }

    const eliminated = state.space_size - surviving;
    const parts: string[] = [];
    if (latest) {
      parts.push(`${latest.guess.split("").join(" ")}: ${spell(latest.feedback)}`);
    }
    parts.push(
      `${surviving.toLocaleString()} of ${state.space_size.toLocaleString()} codes still possible`,
    );
    if (latest && eliminated > 0) {
      parts.push(`${eliminated.toLocaleString()} ruled out so far`);
    }
    if (solverGuess) {
      parts.push(`Next guess: ${solverGuess.split("").join(" ")}`);
    }
    setMessage(`${parts.join(". ")}.`);
  }, [state, surviving, solverGuess]);

  return (
    <p className="visually-hidden" role="status" aria-live="polite">
      {message}
    </p>
  );
}
