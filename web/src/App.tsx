import { WatchMode } from "./modes/WatchMode";

/**
 * Watch mode only, for now.
 *
 * Built first on purpose: it is canvas, collapse timing, and the sub-linear
 * curve, which is where the problems are. Codebreaker is a form and a scored
 * board, and it will not teach us anything we do not already know.
 */
export function App() {
  return (
    <main>
      <h1>Guesstimate</h1>
      <p className="tagline">Think of a code. I will find it.</p>
      <WatchMode />
    </main>
  );
}
