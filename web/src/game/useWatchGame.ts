import { useCallback, useEffect, useState } from "react";
import { ApiError, api } from "../api/client";
import type { GameState } from "../api/client";
import { collapseBetween } from "../grid/collapse";
import type { Collapse } from "../grid/collapse";

export interface WatchGame {
  readonly state: GameState | null;
  readonly guess: string | null;
  readonly alive: readonly number[];
  readonly collapse: Collapse | null;
  readonly history: readonly number[];
  readonly total: number;
  readonly error: string | null;
  readonly busy: boolean;
  answer(feedback: string): Promise<void>;
  restart(): Promise<void>;
}

/**
 * Watch mode: the solver guesses, the player scores.
 *
 * One round trip per turn. The server returns the next guess alongside the
 * answer to the last one, because the mode strictly alternates and asking
 * separately would double the latency for nothing.
 */
export function useWatchGame(columns: number): WatchGame {
  const [state, setState] = useState<GameState | null>(null);
  const [guess, setGuess] = useState<string | null>(null);
  const [alive, setAlive] = useState<readonly number[]>([]);
  const [collapse, setCollapse] = useState<Collapse | null>(null);
  const [history, setHistory] = useState<readonly number[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const restart = useCallback(async () => {
    setBusy(true);
    setError(null);
    setCollapse(null);
    setHistory([]);
    try {
      const started = await api.start({ mode: "watch", solver: "entropy" });
      const [candidates, opening] = await Promise.all([
        api.candidates(started.id),
        api.solverGuess(started.id),
      ]);
      setState(started);
      setAlive(candidates.indices);
      setHistory([candidates.indices.length]);
      setGuess(opening.guess);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : String(caught));
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    void restart();
  }, [restart]);

  const answer = useCallback(
    async (feedback: string) => {
      if (!state || busy) return;
      setBusy(true);
      setError(null);
      try {
        const result = await api.feedback(state.id, feedback);
        const candidates = await api.candidates(state.id);
        // Diff before storing, so the painter is handed what died rather than
        // having to work it out from two snapshots mid-frame.
        setCollapse(collapseBetween(alive, candidates.indices, columns));
        setAlive(candidates.indices);
        setHistory((past) => [...past, candidates.indices.length]);
        setGuess(result.next_guess ?? null);
        setState(await api.state(state.id));
      } catch (caught) {
        // A contradiction leaves the game exactly as it was, so the board and
        // the grid stay put and the player simply answers again.
        setError(caught instanceof ApiError ? caught.detail : String(caught));
      } finally {
        setBusy(false);
      }
    },
    [state, busy, alive, columns],
  );

  return {
    state,
    guess,
    alive,
    collapse,
    history,
    total: state?.space_size ?? 0,
    error,
    busy,
    answer,
    restart,
  };
}
