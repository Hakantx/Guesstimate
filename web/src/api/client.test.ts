import { describe as suite, expect, it } from "vitest";
import { ApiError, describe as explain } from "./client";
import type { ErrorCode } from "./client";

suite("error codes", () => {
  // Listed once, here, so that a code added on the server fails this file as
  // well as the switch — the list is checked against the generated union.
  const codes = [
    "inconsistent_feedback",
    "game_over",
    "wrong_mode",
    "not_found",
    "invalid",
    "rate_limited",
  ] as const satisfies readonly ErrorCode[];

  it("explains every one", () => {
    for (const code of codes) {
      expect(explain(code).length).toBeGreaterThan(10);
    }
  });

  it("marks only a contradiction as recoverable", () => {
    // The one mistake a player makes by hand and should be able to correct
    // without losing the game.
    for (const code of codes) {
      const error = new ApiError(code, "x", 409);
      expect(error.recoverable).toBe(code === "inconsistent_feedback");
    }
  });

  it("is an Error, so it can be thrown and caught normally", () => {
    const error = new ApiError("game_over", "already over", 409);
    expect(error).toBeInstanceOf(Error);
    expect(error.message).toBe("already over");
  });
});
