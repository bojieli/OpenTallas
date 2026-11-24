"""pytest: ADV-TAPOFF-SITE compare() on the QC st_a pattern (name-keyed rows on renumbered taps)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_tapoff_site as A  # noqa: E402


def test_renumbered_taps_are_moved():
    base = {"clk_t1": (10.0, 10.0), "clk_t2": (500.0, 10.0), "clk_t3": (900.0, 10.0)}
    cur = {"clk_t1": (10.0, 10.0), "clk_t2": (900.0, 10.0), "clk_t3": (500.0, 10.0), "clk_t4": (5.0, 5.0)}
    moved, same, new, gone = A.compare(["clk_t1", "clk_t2", "clk_t3", "clk_t4", "clk_t9"], cur, base)
    assert [p for p, _ in moved] == ["clk_t2", "clk_t3"] and same == 1 and new == 1 and gone == 1


def test_within_tolerance_is_same():
    assert A.compare(["a"], {"a": (3.0, 4.0)}, {"a": (0.0, 0.0)})[1] == 1       # 7 um Manhattan <= 9


def test_no_baseline_is_not_run_and_never_raises():
    assert "NOT-RUN" in A.findings({"partition_types": {}}, "p")[0]
    assert A.findings(None, "p", baseline={})[0].startswith("WARN ADV-TAPOFF-SITE")
