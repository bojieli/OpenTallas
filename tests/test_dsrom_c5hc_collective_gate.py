"""DS-ROM C5hc collective gate: the measured-collective hook is opt-in and interpolates the RTL points; the committed
verdict follows from its own priced numbers, the pre-registered rule and the exactness record."""
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import uarch_model_parallelism as M  # noqa: E402

GATE = ROOT / "results/rtl/dsrom_c5hc_collective_gate_20261003"
FITS = {"all_gather": dict(fixed_cycles=100.0, cycles_per_word=2.0, points=[[1, 102], [10, 125], [100, 300]]),
        "all_reduce": dict(fixed_cycles=150.0, cycles_per_word=1.0, points=[[1, 151], [320, 470]])}


def test_measured_interpolation():
    c = 1.2e9
    assert math.isclose(M.measured_collective_s(FITS, "all_gather", 10 * 64 * 8, 8, c), 125 / c)
    assert math.isclose(M.measured_collective_s(FITS, "all_gather", 55 * 64 * 8, 8, c), (125 + 175 * 45 / 90) / c)
    assert math.isclose(M.measured_collective_s(FITS, "all_gather", 200 * 64 * 4, 4, c), (100 + 2 * 200) / c)
    assert math.isclose(M.measured_collective_s(FITS, "all_reduce", 20480, 8, c), 470 / c)
    assert math.isclose(M.measured_collective_s(FITS, "all_gather", 1, 8, c), 102 / c)


def test_decision_rule_precedes_and_verdict_follows_it():
    rule = json.loads((GATE / "decision_rule.json").read_text())
    v = json.loads((GATE / "verdict.json").read_text())
    assert v["decision_rule"] == rule["rule"]
    m = {c: {ctx: v["priced"][c]["measured"][ctx]["ar_tok_s"] for ctx in ("1048576", "200000")} for c in ("C1", "C5hc")}
    g1 = m["C5hc"]["1048576"] / m["C1"]["1048576"] - 1
    g2 = m["C5hc"]["200000"] / m["C1"]["200000"] - 1
    assert v["rate"]["c5hc_vs_c1_ar_1m_pct"] == round(100 * g1, 2)
    want = "ADOPT" if (g1 >= 0.05 and g2 >= 0.01 and v["exactness"]["all_passed"]) else "REJECT"
    assert v["verdict"] == want


def test_measurements_exact_and_deterministic():
    meas = json.loads((GATE / "measurements.json").read_text())
    for name, c in meas["configs"].items():
        assert c["calibration"]["all_passed"] and c["deterministic"]["all_passed"], name
        assert all(f == 0 for f in c["deterministic"]["faults"]) and all(x == 0 for x in c["deterministic"]["mismatches"])
        w = c["fixture"]["wo_b"]
        assert w["tree_of_rank_partials_equals_golden_csum"] and w["to_bf16_equals_golden_linear_q"]
    for name in ("c5hc_phys", "c1_phys"):
        assert meas["configs"][name]["deterministic_timing"], name


def test_model_record_untouched():
    # the default path is the abd77c4e1 study; tests/test_dsrom_parallelism.py replays it in full
    v = json.loads((GATE / "verdict.json").read_text())
    for cand, (ar1, ar2) in (("C1", (2347.4, 2445.0)), ("C5hc", (2606.6, 2677.1))):
        assert v["priced"][cand]["model"]["1048576"]["ar_tok_s"] == ar1
        assert v["priced"][cand]["model"]["200000"]["ar_tok_s"] == ar2
