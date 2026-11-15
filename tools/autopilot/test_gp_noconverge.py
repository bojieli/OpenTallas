import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gp_noconverge as G


def flat(n, x=0.5):
    return [x + (i % 7) * 0.001 for i in range(n)]


def test_parses_both_log_formats():
    assert G.overflows(["      440 |   0.5150 |  4.5e+07 |  +36% |  8e-07 |  \n", "[NesterovSolve] Iter:  10 overflow: 0.25 HPWL: 1\n", "x\n"]) == [0.515, 0.25]


def test_cap_fires_at_the_cap_only():
    assert G.judge(list(range(G.CAP_ROWS, 0, -1)))[0] == "STOP"
    assert G.judge([1.0 - i * 1e-6 for i in range(G.CAP_ROWS - 1)])[0] == "OK"


def test_flat_series_fires_after_the_streak():
    assert G.judge(flat(G.WINDOW * (G.STREAK + 1)))[0] == "STOP"
    assert G.judge(flat(G.WINDOW * G.STREAK))[0] == "OK"                 # one block short


def test_a_lower_floor_resets_the_streak():
    s = []
    for b in range(10):
        s += [0.5 - b * 0.001] * G.WINDOW
    assert G.judge(s)[0] == "OK"


def test_incomplete_block_does_not_count():
    assert G.judge(flat(G.WINDOW * (G.STREAK + 1) - 1))[0] == "OK"


def test_replayed_long_plateau_shape_with_falling_floors_is_not_stopped():
    s = [0.0] * 10 + [0.72 - b * 1e-4 for b in range(18000)] + [0.1] * 100
    assert G.judge(s)[0] == "OK"


def test_report_keeps_one_row_for_a_run_seen_at_two_paths_and_names_the_class():
    log = dict(age_s=1, lines=[f"{i} | 0.5000 |\n" for i in range(G.WINDOW * (G.STREAK + 1))])
    rows, err = G.report([("h", [dict(log, path="/a/run/logs/x/3.log"), dict(log, path="/b/run/logs/x/3.log")], "")])
    assert len(rows) == 1 and rows[0]["verdict"] == "STOP" and rows[0]["cls"] == "FLOW no-converge" and not err


def test_report_passes_host_errors_through():
    assert G.report([("h", [], "boom")]) == ([], ["h: boom"])


def test_hub_scans_itself_without_ssh(monkeypatch):
    seen = []

    class R:
        returncode, stdout, stderr = 0, "[]", ""

    monkeypatch.setattr(G.subprocess, "run", lambda cmd, **k: seen.append(cmd) or R)
    assert G.scan_host(G.HUB)[1:] == ([], "") and seen[0][0] == "sh"
    G.scan_host("epyc7")
    assert seen[1][0] == "ssh" and "epyc7" in seen[1]
