const BLOCKS = "▁▂▃▄▅▆▇█";

/**
 * The collapse so far, in one line.
 *
 * Log-scaled, for the same reason the CLI's is: the classic game goes 3024 to
 * 240 to 20 to 1, and on a linear scale the first guess uses the entire height
 * and every later step sits on the floor. Taking logs turns "divided by about
 * ten, four times" into four even steps, which is what the collapse is.
 */
export function sparkline(counts: readonly number[]): string {
  if (counts.length === 0) return "";
  const scaled = counts.map((n) => Math.log10(Math.max(1, n)));
  const low = Math.min(...scaled);
  const high = Math.max(...scaled);
  if (high - low < 1e-9) return BLOCKS[Math.floor(BLOCKS.length / 2)]!.repeat(counts.length);

  return scaled
    .map((value) => {
      const position = (value - low) / (high - low);
      return BLOCKS[Math.min(BLOCKS.length - 1, Math.floor(position * BLOCKS.length))]!;
    })
    .join("");
}

export function Sparkline({ counts }: { counts: readonly number[] }) {
  if (counts.length < 2) return null;
  return (
    <p className="sparkline">
      <span aria-hidden="true">{sparkline(counts)}</span>
      <span className="visually-hidden">
        Candidates after each guess: {counts.join(", ")}.
      </span>
    </p>
  );
}
