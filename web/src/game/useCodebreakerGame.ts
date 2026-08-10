import { useCallback, useEffect, useState } from "react";
import { ApiError, api } from "../api/client";
import type { GameState } from "../api/client";
import { collapseBetween } from "../grid/collapse";
import type { Collapse } from "../grid/collapse";

export interface CodebreakerGame {
  readonly state: GameState | null;
  readonly alive: readonly number[];
  readonly collapse: Collapse | null;
  readonly total: number;
  readonly error: string | null;
  readonly busy: boolean;
  submit(guess: string): Promise<void>;
  restart(): Promise<void>;
}

/**
 * Codebreaker: the player guesses, the server scores.
 *
 * Evil mode reuses this unchanged. From the client's side the two are the same
 * conversation -- submit a code, be told how close it was -- and the only
 * difference is whether anything was ever committed to on the other end. That
 * the component cannot tell is the whole design of the mode.
 *
 * Same shape as `useWatchGame` — start, hold the state, diff the candidate set
 * on each turn — because the two modes differ only in who moves. The grid is
 * driven identically, which is the point of the API returning indices rather
 * than codes.
 */
export function useCodebreakerGame(
  columns: number,
  mode: "codebreaker" | "evil" = "codebreaker",
): CodebreakerGame {
  const [state, setState] = useState<GameState | null>(null);
  const [alive, setAlive] = useState<readonly number[]>([]);
  const [collapse, setCollapse] = useState<Collapse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const restart = useCallback(async () => {
    setBusy(true);
    setError(null);
    setCollapse(null);
    try {
      const started = await api.start({ mode, solver: "entropy" });
      const candidates = await api.candidates(started.id);
      setState(started);
      setAlive(candidates.indices);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : String(caught));
    } finally {
      setBusy(false);
    }
  }, [mode]);

  useEffect(() => {
    void restart();
  }, [restart]);

  const submit = useCallback(
    async (guess: string) => {
      if (!state || busy) return;
      setBusy(true);
      setError(null);
      try {
        await api.guess(state.id, guess);
        const candidates = await api.candidates(state.id);
        setCollapse(collapseBetween(alive, candidates.indices, columns));
        setAlive(candidates.indices);
        setState(await api.state(state.id));
      } catch (caught) {
        // A rejected guess leaves the game untouched: the board and the grid
        // stay as they were and the player edits and resubmits.
        setError(caught instanceof ApiError ? caught.detail : String(caught));
      } finally {
        setBusy(false);
      }
    },
    [state, busy, alive, columns],
  );

  return {
    state,
    alive,
    collapse,
    total: state?.space_size ?? 0,
    error,
    busy,
    submit,
    restart,
  };
}
