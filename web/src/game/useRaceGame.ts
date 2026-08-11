import { useCallback, useEffect, useState } from "react";
import { ApiError, api } from "../api/client";
import type { GameState } from "../api/client";
import { collapseBetween } from "../grid/collapse";
import type { Collapse } from "../grid/collapse";
import type { components } from "../api/types";

type RaceTurn = components["schemas"]["RaceTurnSchema"];

export interface RaceGame {
  readonly state: GameState | null;
  readonly alive: readonly number[];
  readonly collapse: Collapse | null;
  readonly history: readonly number[];
  readonly solverTurns: readonly RaceTurn[];
  readonly total: number;
  readonly error: string | null;
  readonly busy: boolean;
  readonly winner: "you" | "solver" | null;
  submit(guess: string): Promise<void>;
  restart(): Promise<void>;
}

/**
 * Race the solver: both sides work on the same secret, turn for turn.
 *
 * Composed from what codebreaker and watch already do — the player's move is a
 * codebreaker turn, the solver's is a watch turn scored by the server instead
 * of by a human. The only thing genuinely new is that a turn is a pair, so the
 * solver answers immediately after the player and the two boards stay apart.
 *
 * The grid follows the *player's* candidate set. Showing the solver's would be
 * showing them the answer.
 */
export function useRaceGame(columns: number): RaceGame {
  const [state, setState] = useState<GameState | null>(null);
  const [alive, setAlive] = useState<readonly number[]>([]);
  const [collapse, setCollapse] = useState<Collapse | null>(null);
  const [solverTurns, setSolverTurns] = useState<readonly RaceTurn[]>([]);
  const [history, setHistory] = useState<readonly number[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const restart = useCallback(async () => {
    setBusy(true);
    setError(null);
    setCollapse(null);
    setHistory([]);
    setSolverTurns([]);
    try {
      const started = await api.start({ mode: "race", solver: "entropy" });
      const candidates = await api.candidates(started.id);
      setState(started);
      setAlive(candidates.indices);
      setHistory([candidates.indices.length]);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : String(caught));
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    void restart();
  }, [restart]);

  const submit = useCallback(
    async (guess: string) => {
      if (!state || busy) return;
      setBusy(true);
      setError(null);
      try {
        const mine = await api.guess(state.id, guess);
        const candidates = await api.candidates(state.id);
        setCollapse(collapseBetween(alive, candidates.indices, columns));
        setAlive(candidates.indices);
        setHistory((past) => [...past, candidates.indices.length]);

        // The solver only replies if the player has not already won: once the
        // game is over the server refuses further moves, and asking anyway
        // would surface a 409 the player did nothing to deserve.
        if (!mine.finished) {
          const theirs = await api.solverTurn(state.id);
          setSolverTurns((played) => [...played, theirs]);
        }
        setState(await api.state(state.id));
      } catch (caught) {
        setError(caught instanceof ApiError ? caught.detail : String(caught));
      } finally {
        setBusy(false);
      }
    },
    [state, busy, alive, columns],
  );

  const solverWon = solverTurns.some((turn) => turn.finished);
  return {
    state,
    alive,
    collapse,
    history,
    solverTurns,
    total: state?.space_size ?? 0,
    error,
    busy,
    winner: state?.won ? "you" : solverWon ? "solver" : null,
    submit,
    restart,
  };
}
