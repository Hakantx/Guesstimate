import { useState } from "react";
import { EvilMode } from "./modes/EvilMode";
import { RaceMode } from "./modes/RaceMode";
import { CodebreakerMode } from "./modes/CodebreakerMode";
import { WatchMode } from "./modes/WatchMode";
import { MODE_ORDER, isImplemented } from "./game/modes";
import type { Mode } from "./game/modes";

const LABELS: Record<Mode, string> = {
  codebreaker: "You guess",
  watch: "Watch the solver",
  race: "Race the solver",
  evil: "Evil mode",
};

export function App() {
  const [mode, setMode] = useState<Mode>("watch");

  return (
    <main>
      <h1>Guesstimate</h1>
      <p className="tagline">Bulls and cows, and a solver that is very good at it.</p>

      <nav aria-label="Game mode">
        {MODE_ORDER.map((option) => (
          <button
            key={option}
            type="button"
            aria-pressed={mode === option}
            disabled={!isImplemented(option) || !BUILT.has(option)}
            onClick={() => setMode(option)}
          >
            {LABELS[option]}
          </button>
        ))}
      </nav>

      {mode === "watch" && <WatchMode />}
      {mode === "codebreaker" && <CodebreakerMode />}
      {mode === "race" && <RaceMode />}
      {mode === "evil" && <EvilMode />}
    </main>
  );
}

/** Modes with a component. Race and evil are specced, not built. */
const BUILT = new Set<Mode>(["watch", "codebreaker", "race", "evil"]);
