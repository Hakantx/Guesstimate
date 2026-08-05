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
