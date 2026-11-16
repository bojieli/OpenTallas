"""WAVE-PREPNR-1115: noprog_watchdog GRT round metric, declared-priority exclusion, series-restart evidence, yosys stall."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "autopilot"))
import noprog_watchdog as W


def _rpt(d, n, total):
    body = "".join(f"violation type: Horizontal congestion\n\tcomment: capacity:0 usage:1 congestion:{1}\n" for _ in range(total))
    (d / f"congestion-{n}.rpt").write_text(body)


def test_rounds_sum_overflow(tmp_path):
    for n, t in ((5, 30), (10, 20), (15, 10)):
        _rpt(tmp_path, n, t)
    assert W.grt_rounds(str(tmp_path)) == [(5, 30), (10, 20), (15, 10)]
    assert W.judge_grt_rounds(W.grt_rounds(str(tmp_path))) is None            # falling: progress


def test_no_progress_two_consecutive_rounds():
    v = W.judge_grt_rounds([(5, 100), (10, 90), (15, 90), (20, 95)])
    assert v[0] in ("NO-PROGRESS", "DESIGN-FAIL")
    v = W.judge_grt_rounds([(5, 500), (10, 400), (15, 400), (20, 400)])
    assert v[0] == "NO-PROGRESS" and "2 consecutive" in v[1]
    assert W.judge_grt_rounds([(5, 500), (10, 400), (15, 400)]) is None         # only one non-fall


def test_cbn_q11_trend_flags_early():
    r = [(5, 16943), (10, 17500), (15, 19000), (20, 21563)]
    v = W.judge_grt_rounds(r)
    assert v[0] == "DESIGN-FAIL" and v[3] == "GRT-CONGESTION" and "21563" in v[2]


def test_stop_rules():
    assert W.judge_grt_rounds([(5, 10), (10, 1500)])[0] == "DESIGN-FAIL"          # iter-10 overflow > 1000
    assert W.judge_grt_rounds([(5, 900), (10, 800), (15, 900)])[0] == "DESIGN-FAIL"   # rising after round 10
    assert W.judge_grt_rounds([(5, 900), (10, 800), (15, 700)]) is None
    assert W.judge_grt_rounds([], "x\n[WARNING GRT-0273] Disabled NDR\n")[3] == "GRT-CONGESTION"


def test_plan_exclusion_declared_only():
    assert W.is_plan("plan", "anything") is True
    assert W.is_plan("", "python3 bind.py strict-bind /x --priority plan latcheck g0 die-proto") is False
    assert W.is_plan("die", "latcheck") is False


def test_restarted_series_uses_series_start_not_young():
    now = 100 * 3600.0
    anchors = [(now - 20 * 3600, 0), (now, 1000)]
    # series restarted: every point is inside the last 6 h, flat; stage is 20 h old
    ser = [(100 + 10 * i, 5000.0) for i in range(20)]
    res = {"name": "grt_overflow", "series": ser, "growth_idx": 0, "n": 1000}
    v, why, _ = W.judge(res, anchors, now, exact=True)
    assert v == "NO-PROGRESS", (v, why)


def test_young_is_one_hour_of_current_stage():
    now = 10 * 3600.0
    res = {"name": "x", "series": [(1, 5.0), (2, 5.0)], "growth_idx": 2, "n": 3}
    assert W.judge(res, [(now - 1800, 0), (now, 3)], now, exact=True)[0] == "YOUNG"


def test_synth_mem_stall():
    log = "Executing OPT pass\nExecuting SHARE pass\n"
    assert W.synth_mem_stall(log, 3700)[3] == "SYNTH-MEM-STALL"
    assert W.synth_mem_stall(log, 600) is None
    assert W.synth_mem_stall(log + "Executing OPT_CLEAN pass\n", 7200) is None


def test_decide_cancels_design_fail_after_report():
    rows = [{"unit": "u1", "verdict": "DESIGN-FAIL", "key": "k1", "container": "c"}]
    assert W.decide(rows, {}, 1e6, True) == [] and rows[0]["action"].startswith("REPORTED")
    assert W.decide(rows, {"k1": 1e6 - 5000}, 1e6, True) == ["u1"]


def test_grt_label_never_stops_a_job():
    """OWNER rule 11-14: no GRT early stop.  The GRT round metric only labels."""
    assert W.GRT_LABEL not in W.BAD_VERDICTS
    # every bad GRT trend (GRT-0273, overflow >1000, rising, 2 flat rounds) still decides to cancel nothing
    for rounds, text in (([(5, 10), (10, 1500)], ""), ([(5, 900), (10, 800), (15, 900)], ""), ([(5, 500), (10, 500), (15, 500)], ""),
                         ([], "GRT-0273 Disabled NDR")):
        v = W.judge_grt_rounds(rounds, text)
        assert v is not None
        rows = [{"unit": "u1", "verdict": W.GRT_LABEL, "key": "k1", "container": "c", "why": v[1]}]
        assert W.decide(rows, {"k1": 0.0}, 1e9, True) == []            # even with an earlier report and act=True
        assert "action" not in rows[0]


def test_grt_label_is_not_cancelled_by_do_cancel_path(monkeypatch):
    calls = []
    monkeypatch.setattr(W, "do_cancel", lambda *a, **k: calls.append(a))
    rows = [{"unit": "u1", "verdict": W.GRT_LABEL, "key": "k", "container": "c"}]
    assert W.decide(rows, {"k": 0.0}, 1e9, True) == [] and not calls
