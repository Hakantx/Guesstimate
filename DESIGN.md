# Guesstimate — Design Direction

Read this before writing any component. The goal is a site that could not be
mistaken for a template, built around one memorable element.

## The subject

A deduction game whose entire state space is 3024 numbers. The visual world it
belongs to is early code-breaking: tabulating machines, punched cards, ruled
worksheets, pencil annotations, elimination by hand. Not neon, not a terminal
aesthetic, not a casino.

## The direction: Tabulator

The candidate space is drawn as a punch card, and solving is watching holes get
punched out of it.

This is chosen over the two obvious alternatives on purpose. A dark background
with a bright accent is what every AI-built dev-tool page looks like right now,
and a warm-cream-plus-serif treatment is the other default. Both would bury the
one thing this project has that nothing else does: a 3024-cell grid that
visibly dies.

### Palette

```css
--field:    #E6E8E3;  /* pale card stock, faintly green-grey, not cream */
--ink:      #1B2027;  /* body text, near-black with a cold cast */
--rule:     #C3C7BF;  /* hairlines, grid separators, card edges */
--navy:     #23304A;  /* structural blocks, headers, the solver's side */
--teal:     #1B8F87;  /* alive: surviving candidates, bulls */
--mustard:  #C4901F;  /* partial: cows */
--oxblood:  #7A2233;  /* eliminated, errors, the adversary */
```

Teal and mustard are always paired with a shape difference — filled versus
hollow marker — so the game is playable without color perception.

### Type

IBM Plex, all three widths. The family was designed for exactly this world, it
is free, and it is not what everyone else reaches for.

- Display: **IBM Plex Sans Condensed**, 600, tight tracking, sentence case
- Body: **IBM Plex Sans**, 400
- Data: **IBM Plex Mono**, 400/500 — every digit, count, timing, and bit value
  on the site is set in mono, tabular figures on

Type scale: 12 / 14 / 16 / 20 / 28 / 44 / 72. The 72 is used exactly once per
page.

### The signature element

The candidate grid. 3024 cells, 63 columns by 48 rows, each cell 6px with a 1px
gutter — roughly 440px square, which fits a phone at reduced scale.

Cells are ordered by the candidate's index in the sorted permutation list,
filling left-to-right then top-to-bottom. Nothing is grouped by hand. Because
the list is sorted, each leading digit occupies one contiguous run of 336
candidates — 5⅓ rows at 63 columns — so leading digits still read as visible
horizontal bands without the layout having to encode them.

### Do not "fix" the sort order

That banding is not decoration and it is not an accident of the data. Rule out a
leading digit and its entire 336-cell run dies at once, which reads as a solid
horizontal stripe going dark — the player sees *which* deduction just happened,
not merely that something did. It costs nothing: the ordering is already the
canonical candidate order the engine, the API, and the benchmark all use, so the
grid gets a free explanatory channel by not shuffling.

Any later change that sorts by likelihood, groups by survival, or shuffles to
"spread the animation out" destroys this. If the layout ever needs to change,
the banding has to be replaced deliberately with something that carries the same
information, not dropped as a side effect.

### Render on canvas, not in the DOM

3024 individually animated DOM nodes will not hold a frame budget, and Framer
Motion per cell is the wrong tool at this count. A prototype confirmed canvas is
smooth at 3024 real permutations with real scoring and a staggered column sweep.
Framer Motion stays for page-level transitions where there are tens of elements,
not thousands.

### Collapse timing must vary, and not by turn number

Measured over all 3024 secrets, using the solver's canonical opening:

| After turn | Mean survivors | Cumulative eliminated |
|---|---|---|
| 1 | 537.6 | 82.2% |
| 2 | 88.6 | 97.1% |
| 3 | 12.2 | 99.6% |
| 4 | 1.9 | 99.9% |

So the first turn does most of the work and the rest is mopping up. A uniform
per-turn duration spends the same time on a turn that kills 2,400 cells as on
one that kills ten, which makes the endgame feel stalled.

But turn one is not one thing. The opening splits the space into fourteen
buckets whose sizes are 1, 6, 8, 9, 20, 60, 120, 120, 180, 220, 240, 480, 720
and 840, and which one a player lands in is the luck of their secret:

- median game: 720 survive, 76% eliminated
- lower quartile: 240 survive, 92% eliminated
- best case: 1 survives — the opening was the secret
- worst case: 840 survive, 72% eliminated

A single "turn one is slow and dramatic" duration is therefore wrong too: the
same nominal turn can kill 2,184 cells or 3,023 of them. **Drive the duration
from how many cells actually die, not from the turn index.** Something
sub-linear in the kill count — a square root, or a floor plus a scaled term —
keeps the big opening sweep dramatic without making a 6-cell endgame take the
same time as a 2,000-cell collapse.

The 840-survivor case is the one to design against: it is the modal outcome, it
leaves a quarter of the grid alive after the opening, and it is where the
animation has the most still to do.

- Alive: filled `--teal`, at 90% opacity
- Just eliminated: flashes `--oxblood` for 140ms, then drops to a 1px `--rule`
  outline with a transparent center. Punched out, not deleted. The card keeps
  its shape all game.
- The current guess: `--navy`, with a 1px ring, always visible above everything
- Elimination animates as a stagger sweeping left-to-right by column, ~600ms
  total. Not a single-frame flip. The sweep is the whole point.

Everything else on the page stays quiet so this lands. One bold thing, executed
well.

### Layout

Two-column on desktop: board and controls in a narrow left column, the
candidate card filling the right. Stacked on mobile with the card above the
board, because the card is the reason people are there.

Structural devices should encode something true. Turn numbers are a real
sequence, so number them. Nothing else gets numbered decoration.

## Copy

Write from the player's side of the screen. Say what happens.

- Buttons name their action and keep that name through the flow. "Reveal the
  number" produces a screen that says "Revealed."
- Errors state what's wrong and how to fix it, in one line, at the input:
  "Digits can't repeat — 4 is used twice." Not "Invalid input."
- Empty and pre-game states are invitations, not decoration: "Think of a
  four-digit number. I'll find it."
- No exclamation marks except when the solver wins, and then exactly one.
- Never explain the rules in a paragraph when the first turn can teach them.

## Quality floor

Not features, requirements:

- Responsive to 360px
- Fully keyboard playable, visible focus rings, logical tab order
- `prefers-reduced-motion`: cross-fade eliminations instead of staggering
- Live region announcing feedback and surviving count for screen readers
- Contrast at AA against `--field` for every text color used
- No layout shift when the candidate count changes — reserve the digits
