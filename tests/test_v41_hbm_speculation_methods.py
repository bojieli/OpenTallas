"""V4.1 HBM DSpark pricing record: reproduction gate, pins, and that the opt-in rows leave defaults unchanged."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
REC = ROOT / "results/speculative/v41_hbm_speculation_methods_20261003/v41_hbm_speculation_methods.json"


def _rec():
    return json.loads(REC.read_text())


def test_composer_reproduces_w19():
    import v41_hbm_speculation_methods as S
    w = S.W19()
    p = w.prog_ctx(1048576)
    assert abs(w.run(p)["total_us"] - 442.14) < 0.01
    assert abs(w.run(p, 6, w.w19_union)["total_us"] - 715.82) < 0.01


def test_record_gate_and_pins():
    r = _rec()
    assert r["reproduction_gate"]["ok"]
    for path, h in r["inputs"].items():
        f = ROOT / path if (ROOT / path).exists() else REC.parent / path
        assert hashlib.sha256(f.read_bytes()).hexdigest() == h, path


def test_draft_and_union_are_consistent():
    r = _rec()
    u = r["union"]
    for P in range(2, 9):
        assert 6 <= u["measured_mean_by_P"][str(P)] <= u["uniform_by_P"][str(P)] + 1e-9
    assert all(x <= u["drafter_uniform"] + 1e-9 for x in u["drafter_measured_per_stage"])
    d = r["draft"]["measured_union"]
    assert abs(d["total_us"] - (d["stages_us"] + d["head_us"] + d["markov_steps"] * d["markov_step_us"])) < 0.05
    for ctx, c in r["contexts"].items():
        for ts, rr in c["rates"].items():
            for x in rr["by_gamma"]:
                assert abs(x["tokens_s"] - x["tau"] * 1e6 / x["step_us"]) < 0.1


def test_defaults_untouched():
    import uarch_model as U
    assert U.V41_DRAFT_FRACTION == 3 / 40 and U.V41_TAU == 3.649 and U.V41_POSITIONS == 6
    assert U.HBM_W19["ar_us"] == 442.14 and U.HBM_W19["mtp_pass_us"] == 715.82 and U.HBM_W19["drafter_us"] == 49.9
    rows = U.v41_hbm_dspark_rows(1048576)
    assert rows[0]["design"] == "v41_hbm_ar_w19" and any(r["design"] == "v41_hbm_dspark_g5" for r in rows)
