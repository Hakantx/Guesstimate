"""Phase 4: the terminal game."""

import io

import pytest
from rich.console import Console

from guesstimate.cli import build_parser, main
from guesstimate.cli.display import sparkline
from guesstimate.cli.session import ScriptedInput, Session

# The original crashed on an empty line because it indexed a string before
# checking its length. Every one of these used to be a traceback.
BAD_INPUT = ["", "   ", "12", "12345", "1230", "12X4", "1123", "abcd", "-1"]


def run(script: list[str], argv: list[str] | None = None) -> str:
    """Play a scripted session and return everything printed."""
    buffer = io.StringIO()
    console = Console(file=buffer, width=80, force_terminal=False, no_color=True)
    session = Session(
        console=console,
        ask=ScriptedInput(script),
        args=build_parser().parse_args(argv or []),
    )
    session.play()
    return buffer.getvalue()


# --- sparkline -------------------------------------------------------------


def test_sparkline_is_empty_for_no_data():
    assert sparkline([]) == ""


def test_sparkline_has_one_mark_per_value():
    assert len(sparkline([100, 50, 10, 1])) == 4


def test_sparkline_descends_as_candidates_collapse():
    marks = sparkline([3024, 240, 20, 1])
    assert marks[0] > marks[-1]  # block characters sort by height
    assert marks == "".join(sorted(marks, reverse=True))


def test_sparkline_is_log_scaled():
    # Candidate counts fall by orders of magnitude. On a linear scale the drop
    # from 3024 to 240 uses the whole range and everything after it is flat.
    linear_would_flatten = sparkline([3024, 240, 20, 2])
    assert len(set(linear_would_flatten)) == 4, "each step should be visible"


def test_sparkline_handles_a_flat_run():
    assert len(set(sparkline([5, 5, 5]))) == 1


def test_sparkline_handles_a_single_value():
    assert len(sparkline([42])) == 1


# --- argument parsing ------------------------------------------------------


def test_default_ruleset_is_the_classic_game():
    args = build_parser().parse_args([])
    assert args.length == 4
    assert args.alphabet == "123456789"
    assert args.repeats is False


def test_flags_are_wired():
    args = build_parser().parse_args(
        ["--solver", "entropy", "--length", "3", "--alphabet", "abc", "--repeats"]
    )
    assert args.solver == "entropy"
    assert args.length == 3
    assert args.alphabet == "abc"
    assert args.repeats is True


def test_an_unknown_solver_is_rejected_by_the_parser():
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--solver", "psychic"])


def test_an_impossible_ruleset_exits_cleanly_rather_than_tracing_back():
    # length 5 from a 3-symbol alphabet with no repeats has no codes at all.
    code = main(["--length", "5", "--alphabet", "abc"])
    assert code != 0


# --- mode B: the player guesses -------------------------------------------


def test_a_won_game_says_so():
    output = run(["b", "1234", "n"], ["--seed", "7", "--secret", "1234"])
    assert "1234" in output
    assert "+4-0" in output
    assert "won" in output.lower()


def test_bad_guesses_are_rejected_without_crashing():
    output = run(["b", *BAD_INPUT, "1234", "n"], ["--seed", "7", "--secret", "1234"])
    assert "won" in output.lower()
    # Every bad line got an explanation rather than a traceback.
    assert output.lower().count("try again") >= len(BAD_INPUT)


def test_the_board_shows_every_guess_and_its_score():
    output = run(["b", "5678", "1234", "n"], ["--seed", "7", "--secret", "1234"])
    assert "5678" in output and "1234" in output


# --- mode A: the solver guesses -------------------------------------------


@pytest.mark.slow
def test_the_solver_wins_when_told_the_truth():
    # The player answers honestly; feedback is computed for them by --secret so
    # the script does not have to know what the solver will ask. Slow-marked
    # because the default solver pays a ~50s opening search on first use.
    output = run(["a", "n"], ["--seed", "7", "--secret", "4712", "--auto-answer"])
    assert "got it" in output.lower()
    assert "4712" in output


def test_the_solver_shows_the_surviving_count_and_a_sparkline():
    output = run(
        ["a", "n"],
        ["--seed", "7", "--secret", "4712", "--auto-answer", "--solver", "random"],
    )
    assert "3,024" in output  # the starting candidate count
    assert any(mark in output for mark in "▁▂▃▄▅▆▇█")


def test_malformed_feedback_is_re_prompted():
    output = run(
        ["a", "nonsense", "+9", "2-1", "+0-0", "n"],
        ["--seed", "7", "--solver", "random", "--stop-after", "1"],
    )
    assert output.lower().count("try again") >= 3


def test_contradictory_feedback_is_survivable():
    # Claiming a win and then denying it empties the candidate set. The session
    # must offer a correction rather than dying -- a human scoring by hand gets
    # this wrong regularly.
    # On a 3-of-5 ruleset "+0-0" is impossible: it claims none of three symbols
    # appear, leaving only two to fill three distinct positions. The solver's
    # candidate set empties and the session has to survive it.
    output = run(
        ["a", "+0-0", "+0-0", "n"],
        [
            "--seed",
            "7",
            "--solver",
            "random",
            "--stop-after",
            "3",
            "--length",
            "3",
            "--alphabet",
            "12345",
        ],
    )
    assert "contradic" in output.lower()
    assert "traceback" not in output.lower()


# --- play again ------------------------------------------------------------


def test_the_play_again_loop_starts_a_second_game():
    output = run(["b", "1234", "y", "1234", "n"], ["--seed", "7", "--secret", "1234"])
    assert output.lower().count("won") >= 2


def test_running_out_of_input_ends_the_session_quietly():
    # Ctrl-D at any prompt. Not a crash.
    output = run(["b"], ["--seed", "7", "--secret", "1234"])
    assert "traceback" not in output.lower()


def test_the_same_seed_gives_the_same_secret():
    first = run(["b", "1111", "n"], ["--seed", "99"])
    second = run(["b", "1111", "n"], ["--seed", "99"])
    assert first == second
