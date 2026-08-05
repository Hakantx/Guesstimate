"""Guesstimate: a Bulls and Cows solver, game, and research toy.

The layers are strictly ordered by dependency. ``core`` and ``solvers`` are
pure functions over data with no I/O of any kind; everything else builds on
them and they build on nothing.
"""

__version__ = "0.1.0"
