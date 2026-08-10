import { useState } from "react";
import type { components } from "../api/types";
import { validate } from "../game/ruleset";

type Ruleset = components["schemas"]["RulesetSchema"];

interface Props {
  ruleset: Ruleset;
  disabled: boolean;
  onSubmit(guess: string): void;
}

/**
 * Typing a code.
 *
 * Validated here before it is sent, so an obvious mistake gets an answer with
 * no round trip. The server validates again and is the authority — this is a
 * convenience, not a check anything relies on.
 */
export function GuessInput({ ruleset, disabled, onSubmit }: Props) {
  const [value, setValue] = useState("");
  const [touched, setTouched] = useState(false);
  const problem = validate(value, ruleset);

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        setTouched(true);
        if (!problem) {
          onSubmit(value);
          setValue("");
          setTouched(false);
        }
      }}
    >
      <label htmlFor="guess">
        Your guess — {ruleset.length} of {ruleset.alphabet}
        {ruleset.allow_repeats ? ", repeats allowed" : ", no repeats"}
      </label>
      <input
        id="guess"
        type="text"
        inputMode="numeric"
        autoComplete="off"
        autoFocus
        value={value}
        disabled={disabled}
        aria-invalid={touched && problem !== null}
        aria-describedby={touched && problem ? "guess-problem" : undefined}
        onChange={(event) => setValue(event.target.value.trim())}
      />
      {touched && problem && (
        <p className="error" id="guess-problem">
          {problem}
        </p>
      )}
      <button className="primary" type="submit" disabled={disabled || !value}>
        Guess
      </button>
    </form>
  );
}
