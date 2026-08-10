import type { components } from "./types";

type Schemas = components["schemas"];
export type GameState = Schemas["GameStateSchema"];
export type TurnResult = Schemas["TurnResultSchema"];
export type SolverTurnResult = Schemas["SolverTurnResultSchema"];
export type Candidates = Schemas["CandidatesResponse"];
export type NewGame = Schemas["NewGameRequest"];

/**
 * The server's refusal codes, straight from the generated schema.
 *
 * Not written down here, and that is the point. The Python client keeps a
 * table mapping each code to one exception; a hand-copied twin in TypeScript
 * would be exactly the bug in `docs/notes/protocol-is-not-a-contract.md` — two
 * implementations agreeing on shape and disagreeing on behaviour — with a
 * comment where the fix should be. Because this type is generated, adding a
 * code on the server changes the union, and the exhaustive switch in
 * `describe` below stops compiling.
 */
export type ErrorCode = Schemas["ErrorResponse"]["error"];

export class ApiError extends Error {
  constructor(
    readonly code: ErrorCode,
    readonly detail: string,
    readonly status: number,
  ) {
    super(detail);
    this.name = "ApiError";
  }

  /** Whether the game survives this and can be played on. */
  get recoverable(): boolean {
    return this.code === "inconsistent_feedback";
  }
}

/** A sentence to show the player. Exhaustive over `ErrorCode` by construction. */
export function describe(code: ErrorCode): string {
  switch (code) {
    case "inconsistent_feedback":
      return "That answer contradicts an earlier one, so no code fits. Try again.";
    case "game_over":
      return "This game has already finished.";
    case "wrong_mode":
      return "This mode does not support that move.";
    case "not_found":
      return "That game has expired. Start a new one.";
    case "invalid":
      return "That input was not valid.";
    case "rate_limited":
      return "Too many requests. Give it a moment.";
  }
}

async function request<T>(
  path: string,
  init?: RequestInit & { json?: unknown },
): Promise<T> {
  const { json, ...rest } = init ?? {};
  const response = await fetch(path, {
    ...rest,
    headers: json ? { "content-type": "application/json" } : undefined,
    body: json ? JSON.stringify(json) : undefined,
  });

  if (!response.ok) {
    let code: ErrorCode = "invalid";
    let detail = response.statusText;
    try {
      const body = (await response.json()) as Partial<Schemas["ErrorResponse"]>;
      if (body.error) code = body.error;
      if (body.detail) detail = body.detail;
    } catch {
      // A refusal without a JSON body: keep the status text.
    }
    throw new ApiError(code, detail, response.status);
  }
  return (await response.json()) as T;
}

export const api = {
  start: (body: NewGame) =>
    request<GameState>("/game", { method: "POST", json: body }),

  state: (id: string) => request<GameState>(`/game/${id}/state`),

  candidates: (id: string) => request<Candidates>(`/game/${id}/candidates`),

  guess: (id: string, guess: string) =>
    request<TurnResult>(`/game/${id}/guess`, { method: "POST", json: { guess } }),

  solverGuess: (id: string) =>
    request<{ guess: string }>(`/game/${id}/solver-guess`),

  solverTurn: (id: string) =>
    request<Schemas["RaceTurnSchema"]>(`/game/${id}/solver-turn`, {
      method: "POST",
    }),

  feedback: (id: string, feedback: string) =>
    request<SolverTurnResult>(`/game/${id}/feedback`, {
      method: "POST",
      json: { feedback },
    }),
};
