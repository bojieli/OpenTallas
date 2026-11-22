"""TAPNAME-1122 (FLOW-OPS-R2, COORD): density added tap names are checked against the bind's density base in seconds."""
import json
import sys
from pathlib import Path
H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import plan_gate_pre as G  # noqa: E402


def plan(tmp_path, added, refs=()):
    ck = {"tap_mode": "density", "added_taps": [{"name": n, "xy": [1, 1]} for n in added],
          "landing_contract": {"pins": [{"source_clock_port": r} for r in refs]}}
    p = tmp_path / "p.json"
    p.write_text(json.dumps({"partition_types": {"cbf_q00": {"clock": ck}, "other": {"clock": {"tap_mode": "explicit"}}}}))
    return str(p)


BASE = lambda P, raw, tn: 114  # noqa: E731


def test_wrong_added_name_refused_with_expected():
    import tempfile
    d = Path(tempfile.mkdtemp())
    f = G.check_tapname(plan(d, ["clk_t101", "clk_t102"]), base_fn=BASE)
    assert f == ["FAIL TAPNAME cbf_q00: density base gives 114 taps, so added_taps must be clk_t114..clk_t115; "
                 "clk_t101 should be clk_t114; clk_t102 should be clk_t115"]


def test_right_names_pass_and_stale_refs_need_retap(tmp_path):
    assert G.check_tapname(plan(tmp_path, ["clk_t114"], ["clk_t3", "clk_t114"]), base_fn=BASE) == []
    f = G.check_tapname(plan(tmp_path, ["clk_t114"], ["clk_t130", "clk_t3"]), base_fn=BASE)
    assert len(f) == 1 and f[0].startswith("FAIL TAPNAME-RETAP cbf_q00:") and "clk_t130" in f[0] and "clk_t3," not in f[0]


def test_solve_error_warns(tmp_path):
    f = G.check_tapname(plan(tmp_path, ["clk_t114"]), base_fn=lambda *a: 1 / 0)
    assert f[0].startswith("WARN TAPNAME cbf_q00: density base not solved")
