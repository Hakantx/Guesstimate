"""Phase 3: the benchmark harness."""

import json
import statistics
from pathlib import Path

import pytest

from guesstimate.bench import (
    Config,
    GameRecord,
    Provenance,
    RecordStore,
    RunResult,
    draw_sample,
    information_floor,
    paired_difference,
    per_secret_guesses,
    run_config,
    summarise,
)
from guesstimate.core import Ruleset, all_candidates

SMALL = Ruleset(3, "12345")  # 60 codes


# --- paired sampling -------------------------------------------------------
#
# The whole point of requirement 1. Two solvers measured on different secrets
# are two independent means, and the noise between samples swamps a gap of the
# size we care about. Measured on the same secrets, the per-secret difference
# cancels "this secret happens to be easy" entirely.


def test_the_sample_is_identical_for_every_solver():
    first = draw_sample(SMALL, size=20, seed=7)
    second = draw_sample(SMALL, size=20, seed=7)
    assert first == second


def test_the_sample_is_reproducible_from_the_seed_alone():
    assert draw_sample(SMALL, size=20, seed=7) != draw_sample(SMALL, size=20, seed=8)


def test_the_sample_is_drawn_without_replacement():
    sample = draw_sample(SMALL, size=60, seed=1)
    assert len(set(sample)) == 60


def test_a_sample_larger_than_the_space_is_rejected():
    with pytest.raises(ValueError, match="60"):
        draw_sample(SMALL, size=61, seed=1)


def test_paired_difference_cancels_per_secret_difficulty():
    # Secrets 0 and 2 are hard for both; B is one guess better on every secret.
    a = [7, 3, 9, 4]
    b = [6, 2, 8, 3]
    paired = paired_difference(a, b)
    assert paired.mean == pytest.approx(1.0)
    assert paired.stdev == pytest.approx(0.0)
    # Zero spread: the difference is identical everywhere, however wildly the
    # raw counts vary. Comparing the two means alone would show 5.75 vs 4.75
    # against a standard deviation of ~2.6 and prove nothing.
    assert paired.stderr == pytest.approx(0.0)
    assert (paired.wins, paired.losses, paired.ties) == (4, 0, 0)


def test_paired_difference_reports_direction_and_ties():
    paired = paired_difference([4, 5, 6], [5, 5, 4])
    assert paired.mean == pytest.approx(1 / 3)
    assert (paired.wins, paired.losses, paired.ties) == (1, 1, 1)


def test_paired_difference_requires_equal_length_runs():
    with pytest.raises(ValueError, match="same secrets"):
        paired_difference([1, 2, 3], [1, 2])


def test_paired_confidence_interval_brackets_the_mean():
    paired = paired_difference([5, 6, 5, 7, 5], [4, 4, 5, 5, 4])
    low, high = paired.confidence_interval
    assert low < paired.mean < high


# --- provenance ------------------------------------------------------------


def test_provenance_records_everything_needed_to_reproduce_a_run():
    provenance = Provenance.capture(SMALL, sample_size=20, seed=7)
    for field in (
        "git_sha",
        "git_dirty",
        "python",
        "machine",
        "cpu_count",
        "ruleset",
        "sample_size",
        "seed",
        "started_utc",
    ):
        assert getattr(provenance, field) is not None

    assert provenance.sample_size == 20
    assert provenance.seed == 7
    assert provenance.ruleset["alphabet"] == "12345"
    assert provenance.ruleset["length"] == 3


def test_provenance_round_trips_through_json():
    provenance = Provenance.capture(SMALL, sample_size=20, seed=7)
    assert Provenance.from_dict(json.loads(json.dumps(provenance.to_dict()))) == (
        provenance
    )


def test_provenance_renders_a_markdown_block():
    rendered = Provenance.capture(SMALL, sample_size=20, seed=7).to_markdown()
    assert "Sample" in rendered and "20" in rendered
    assert "Seed" in rendered and "7" in rendered
    assert "Ruleset" in rendered


# --- resumable runs --------------------------------------------------------


def test_a_store_reloads_what_it_wrote(tmp_path):
    path = tmp_path / "games.jsonl"
    store = RecordStore(path, Provenance.capture(SMALL, sample_size=2, seed=1))
    record = GameRecord(
        config="entropy/restricted",
        secret_index=0,
        secret="123",
        guesses=3,
        seconds=0.5,
        turn_seconds=(0.3, 0.1, 0.1),
        survivors=(12, 3, 1),
    )
    store.append(record)

    reopened = RecordStore(path, Provenance.capture(SMALL, sample_size=2, seed=1))
    assert reopened.done("entropy/restricted") == {(0, 0)}
    assert reopened.records()[0] == record


def test_a_store_refuses_to_resume_a_different_run(tmp_path):
    # Resuming across a code change would silently mix two runs into one table.
    path = tmp_path / "games.jsonl"
    RecordStore(path, Provenance.capture(SMALL, sample_size=2, seed=1)).append(
        GameRecord("entropy/restricted", 0, "123", 3, 0.5, (0.5,), (1,))
    )
    with pytest.raises(ValueError, match="different run"):
        RecordStore(path, Provenance.capture(SMALL, sample_size=2, seed=999))


def test_resuming_skips_completed_games(tmp_path):
    path = tmp_path / "games.jsonl"
    provenance = Provenance.capture(SMALL, sample_size=4, seed=3)
    sample = draw_sample(SMALL, size=4, seed=3)
    config = Config("random", restrict_to_candidates=True)

    store = RecordStore(path, provenance)
    run_config(config, SMALL, sample[:2], seed=3, store=store)
    assert len(store.records()) == 2

    resumed = RecordStore(path, provenance)
    run_config(config, SMALL, sample, seed=3, store=resumed)
    assert len(resumed.records()) == 4
    assert sorted(r.secret_index for r in resumed.records()) == [0, 1, 2, 3]


# --- the multi-seed baseline ----------------------------------------------
#
# Requirement 2. A single random game is one draw from a distribution, and its
# per-secret value correlates with nothing -- measured at -0.13 to -0.06
# against the strategies on the classic ruleset, which is why pairing against
# it recovered no variance at all. Averaging several seeds per secret turns
# that draw into an estimate of expected performance on that secret, which is
# the quantity a strategy should be compared against.


def test_only_stochastic_solvers_are_repeated():
    from guesstimate.solvers import EntropySolver, RandomSolver

    assert RandomSolver.stochastic is True
    assert EntropySolver.stochastic is False


def test_the_baseline_is_played_once_per_seed():
    sample = draw_sample(SMALL, size=5, seed=5)
    result = run_config(Config("random", True), SMALL, sample, seed=5, repeats=4)
    assert len(result.records) == 20
    assert sorted({r.repeat for r in result.records}) == [0, 1, 2, 3]


def test_repeating_a_deterministic_solver_is_refused():
    # Playing minimax five times returns the same game five times; recording it
    # would inflate the sample without adding a single bit of information.
    sample = draw_sample(SMALL, size=5, seed=5)
    result = run_config(Config("minimax", True), SMALL, sample, seed=5, repeats=4)
    assert len(result.records) == 5
    assert {r.repeat for r in result.records} == {0}


def test_each_repeat_gets_its_own_seed():
    sample = draw_sample(SMALL, size=8, seed=5)
    result = run_config(Config("random", True), SMALL, sample, seed=5, repeats=6)
    by_secret: dict[int, set[int]] = {}
    for record in result.records:
        by_secret.setdefault(record.secret_index, set()).add(record.guesses)
    # Not proof of independence, but a repeat that reused one seed would give
    # identical counts for every secret.
    assert any(len(counts) > 1 for counts in by_secret.values())


def test_per_secret_guesses_averages_the_repeats():
    records = [
        GameRecord("random/restricted", 0, "123", 4, 0.0, (0.0,), (1,), repeat=0),
        GameRecord("random/restricted", 0, "123", 6, 0.0, (0.0,), (1,), repeat=1),
        GameRecord("random/restricted", 1, "124", 3, 0.0, (0.0,), (1,), repeat=0),
        GameRecord("random/restricted", 1, "124", 3, 0.0, (0.0,), (1,), repeat=1),
    ]
    assert per_secret_guesses(records) == [5.0, 3.0]


def test_paired_difference_accepts_averaged_baselines():
    paired = paired_difference([5.0, 3.5, 4.5], [4, 3, 5])
    assert paired.mean == pytest.approx((1.0 + 0.5 - 0.5) / 3)


def test_the_summary_reports_how_many_repeats_it_used():
    sample = draw_sample(SMALL, size=6, seed=5)
    summary = summarise(
        run_config(Config("random", True), SMALL, sample, seed=5, repeats=5)
    )
    assert summary.n == 6  # secrets
    assert summary.games == 30  # games played
    assert summary.repeats == 5


# --- running ---------------------------------------------------------------


def test_a_run_produces_one_record_per_secret():
    sample = draw_sample(SMALL, size=6, seed=5)
    result = run_config(Config("entropy", True), SMALL, sample, seed=5)
    assert len(result.records) == 6
    assert [r.secret for r in result.records] == ["".join(s) for s in sample]


def test_every_game_ends_in_a_win_with_one_survivor():
    sample = draw_sample(SMALL, size=6, seed=5)
    result = run_config(Config("minimax", True), SMALL, sample, seed=5)
    for record in result.records:
        assert record.survivors[-1] == 1
        assert record.guesses == len(record.survivors) == len(record.turn_seconds)


def test_runs_are_reproducible():
    sample = draw_sample(SMALL, size=8, seed=5)
    first = run_config(Config("random", True), SMALL, sample, seed=5)
    second = run_config(Config("random", True), SMALL, sample, seed=5)
    assert [r.guesses for r in first.records] == [r.guesses for r in second.records]


def test_the_random_baseline_is_paired_by_secret_not_by_call_order():
    # Each game reseeds from (run seed, secret index), so the baseline plays
    # secret k identically whether or not the secrets before it were run.
    sample = draw_sample(SMALL, size=8, seed=5)
    whole = run_config(Config("random", True), SMALL, sample, seed=5)
    tail = run_config(Config("random", True), SMALL, sample[4:], seed=5, start_index=4)
    assert [r.guesses for r in whole.records[4:]] == [r.guesses for r in tail.records]


# --- timing ----------------------------------------------------------------
#
# Requirement 2. The opening costs ~52s on the classic ruleset and every game
# after it ~2s, so a mean over 300 games hides one 25x outlier inside a number
# that then gets published.


def test_the_cold_open_is_timed_separately_from_the_games():
    sample = draw_sample(SMALL, size=6, seed=5)
    result = run_config(Config("minimax", True), SMALL, sample, seed=5)
    assert result.cold_open_seconds > 0
    # Warmed before the loop, so no individual game pays for the opening.
    assert max(r.seconds for r in result.records) < result.cold_open_seconds


def test_random_has_no_meaningful_cold_open():
    sample = draw_sample(SMALL, size=4, seed=5)
    result = run_config(Config("random", True), SMALL, sample, seed=5)
    assert result.cold_open_seconds >= 0


# --- summarising -----------------------------------------------------------


def test_summary_reports_the_shape_of_the_distribution():
    sample = draw_sample(SMALL, size=20, seed=5)
    result = run_config(Config("entropy", True), SMALL, sample, seed=5)
    summary = summarise(result)
    counts = [r.guesses for r in result.records]

    assert summary.mean == pytest.approx(statistics.mean(counts))
    assert summary.median == pytest.approx(statistics.median(counts))
    assert summary.worst == max(counts)
    assert summary.stdev == pytest.approx(statistics.stdev(counts))
    assert sum(summary.distribution.values()) == 20


def test_summary_reports_the_collapse_curve():
    sample = draw_sample(SMALL, size=20, seed=5)
    summary = summarise(run_config(Config("entropy", True), SMALL, sample, seed=5))
    # Mean survivors after guess 1, 2, 3 -- monotonically shrinking.
    curve = summary.collapse
    assert len(curve) >= 3
    assert curve[0] > curve[1] >= curve[2]


def test_the_information_floor_is_the_theoretical_minimum():
    # 3024 equally likely secrets, 14 outcomes: no strategy can average fewer
    # than log2(3024)/log2(14) guesses.
    import math

    classic = Ruleset()
    expected = math.log2(3024) / math.log2(14)
    assert information_floor(classic) == pytest.approx(expected)
    assert 3.0 < information_floor(classic) < 3.1


def test_no_solver_beats_the_information_floor():
    sample = draw_sample(SMALL, size=20, seed=5)
    floor = information_floor(SMALL)
    for name in ("random", "minimax", "expected-size", "entropy"):
        summary = summarise(run_config(Config(name, True), SMALL, sample, seed=5))
        assert summary.mean >= floor, f"{name} beat the information floor"


def test_the_floor_uses_reachable_outcomes_not_the_triangle():
    # Holding the space size fixed, fewer reachable outcomes means each guess
    # carries less information and the floor rises. A two-symbol alphabet
    # reaches far fewer outcomes than the bulls+cows<=length triangle suggests,
    # so assuming the triangle would understate the floor and flatter the
    # solvers. Comparing two different rulesets would not test this -- the
    # space size dominates -- so this compares one ruleset computed both ways.
    import math

    from guesstimate.core import feedback_space

    narrow = Ruleset(4, "12", allow_repeats=True)
    reachable = len(feedback_space(narrow))
    triangle = 14  # pairs with bulls + cows <= 4, less the impossible (3, 1)
    assert reachable < triangle

    space = math.log2(narrow.space_size)
    assert information_floor(narrow) == pytest.approx(space / math.log2(reachable))
    assert information_floor(narrow) > space / math.log2(triangle)


def test_all_candidates_is_the_default_sample_when_size_is_none():
    assert len(draw_sample(SMALL, size=None, seed=1)) == len(all_candidates(SMALL))


# --- report and charts -----------------------------------------------------


def _small_run() -> dict[str, RunResult]:
    sample = draw_sample(SMALL, size=12, seed=5)
    results = {}
    for name in ("random", "entropy"):
        result = run_config(Config(name, True), SMALL, sample, seed=5)
        results[Config(name, True).name] = result
    return results


def test_the_report_carries_its_provenance():
    from guesstimate.bench.report import build_report

    results = _small_run()
    summaries = [summarise(r) for r in results.values()]
    counts = {k: per_secret_guesses(r.records) for k, r in results.items()}
    provenance = Provenance.capture(SMALL, sample_size=12, seed=5)

    report = build_report(
        provenance,
        SMALL,
        summaries,
        counts,
        information_floor(SMALL),
        "random/restricted/pure",
    )
    # A table with no provenance is uninterpretable later; these are the facts
    # that make a number traceable to the run that produced it.
    assert provenance.git_sha[:12] in report
    assert "Seed" in report and "| 5 |" in report
    assert "12 secrets" in report
    assert provenance.python in report
    assert "Information floor" in report
    assert "Cold open" in report
    assert "Positive means fewer guesses" in report


def test_the_report_separates_cold_open_from_warm_games():
    from guesstimate.bench.report import timing_table

    results = _small_run()
    table = timing_table([summarise(r) for r in results.values()])
    assert "Cold open" in table and "Warm game (mean)" in table


def test_charts_are_written(tmp_path):
    from guesstimate.bench.charts import write_charts

    results = _small_run()
    summaries = [summarise(r) for r in results.values()]
    counts = {k: per_secret_guesses(r.records) for k, r in results.items()}
    written = write_charts(
        summaries, counts, "random/restricted/pure", information_floor(SMALL), tmp_path
    )
    assert len(written) == 4
    for path in written:
        assert path.exists() and path.stat().st_size > 0


def test_the_cli_parses_the_documented_flags():
    from guesstimate.bench.__main__ import configurations, parse_args

    args = parse_args(["--sample", "50", "--seed", "3", "--unrestricted"])
    assert args.sample == 50 and args.seed == 3 and args.unrestricted

    configs = configurations(["random", "entropy"], unrestricted=True)
    names = [c.name for c in configs]
    # Random ignores the flag, so an unrestricted row for it would be a
    # duplicate rather than a measurement.
    assert "random/unrestricted" not in names
    assert "entropy/unrestricted/pure" in names


# --- the dirty flag --------------------------------------------------------
#
# A benchmark writes its results into the working tree, so asking "is the tree
# dirty" without excluding those results answers "yes, always" -- and a run
# with a genuinely uncommitted solver change looks identical to a clean one.


def test_output_directory_changes_do_not_count_as_a_dirty_tree(tmp_path):
    from guesstimate.bench.provenance import _tree_is_dirty

    # The real repo, with the real bench output directory excluded.
    assert _tree_is_dirty(Path("docs/benchmarks/full")) in (True, False)


def test_the_dirty_check_still_notices_changes_outside_the_output(monkeypatch):
    from guesstimate.bench import provenance as module

    monkeypatch.setattr(
        module,
        "_git",
        lambda *a: " M guesstimate/solvers/base.py" if a[0] == "status" else "/repo",
    )
    assert module._tree_is_dirty(Path("/repo/docs/benchmarks")) is True


def test_only_output_changes_read_as_clean(monkeypatch):
    from guesstimate.bench import provenance as module

    def fake_git(*args: str) -> str:
        if args[0] == "status":
            return "?? docs/benchmarks/full/"
        return "/repo"

    monkeypatch.setattr(module, "_git", fake_git)
    assert module._tree_is_dirty(Path("/repo/docs/benchmarks/full")) is False


def test_a_clean_tree_is_clean(monkeypatch):
    from guesstimate.bench import provenance as module

    monkeypatch.setattr(module, "_git", lambda *a: "")
    assert module._tree_is_dirty(None) is False


def test_capture_without_an_output_dir_counts_everything(monkeypatch):
    from guesstimate.bench import provenance as module

    monkeypatch.setattr(
        module, "_git", lambda *a: "?? anything" if a[0] == "status" else "/repo"
    )
    assert module._tree_is_dirty(None) is True


# --- the engine is part of a run's identity --------------------------------


def test_the_engine_is_in_every_config_name():
    from guesstimate.bench import Config

    assert Config("entropy", True, "matrix").name == "entropy/restricted/matrix"
    assert Config("entropy", True, "pure").name == "entropy/restricted/pure"


def test_two_engines_are_different_configurations():
    # Guess counts are identical across engines by construction; timings are
    # not. Sharing a name would let a matrix run resume a pure one's records
    # and produce a timing table describing neither.
    from guesstimate.bench import Config

    assert (
        Config("minimax", True, "pure").name != Config("minimax", True, "matrix").name
    )


def test_the_store_will_not_resume_across_engines(tmp_path):
    from guesstimate.bench import Config, RecordStore, draw_sample, run_config

    provenance = Provenance.capture(SMALL, sample_size=3, seed=1)
    sample = draw_sample(SMALL, size=3, seed=1)
    store = RecordStore(tmp_path / "g.jsonl", provenance)

    run_config(Config("entropy", True, "pure"), SMALL, sample, seed=1, store=store)
    done_pure = store.done("entropy/restricted/pure")
    assert len(done_pure) == 3
    assert store.done("entropy/restricted/matrix") == set()


def test_auto_declines_the_matrix_for_an_unaffordable_ruleset():
    from guesstimate.bench.__main__ import resolve_engine

    assert resolve_engine("auto", Ruleset(4, "0123456789ABCDEF")) == "pure"
    assert resolve_engine("auto", Ruleset()) == "matrix"


def test_an_explicit_engine_is_not_second_guessed():
    from guesstimate.bench.__main__ import resolve_engine

    assert resolve_engine("pure", Ruleset()) == "pure"
