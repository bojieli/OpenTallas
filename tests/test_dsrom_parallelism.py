"""DS-ROM parallelism mapping study: the extension is opt-in, restores the model, and the record replays."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import dsrom_parallelism as R  # noqa: E402
import uarch_model as u  # noqa: E402
import uarch_model_parallelism as M  # noqa: E402

REC = json.loads((ROOT / "results/uarch/dsrom_parallelism_20261003/model.json").read_text())


def _cand(cid):
    return next(c for c in REC["candidates"] if c["id"] == cid)


def test_record_reproduces_pinned_baselines():
    assert REC["baseline_reproduced"]
    for ctx, (ar, mtp) in R.PINNED.items():
        r = _cand("M0_model_S58_TP4")["results"][str(ctx)]
        assert (r["ar_tok_s"], r["mtp_tok_s"]) == (ar, mtp)
    for ctx, (ar, mtp) in R.PAR2_PINNED.items():
        r = _cand("C1_PP58_TP4_PAR2rows")["results"][str(ctx)]
        assert (r["ar_tok_s"], r["mtp_tok_s"]) == (ar, mtp)


def test_recommended_is_best_exact_at_equal_hardware():
    rec = REC["recommendation"]["mapping"]
    best = _cand(rec)
    assert best["exactness"]["verdict"] == "exact"
    for c in REC["candidates"]:
        if c["id"] in (rec, "C5hc4_hybrid_4stacks", "M0_model_S58_TP4"):
            continue          # 2x HBM sensitivity; M0 is the inexact unpriced-PAR2 model proxy
        for ctx in ("1048576", "200000"):
            assert best["results"][ctx]["ar_tok_s"] >= c["results"][ctx]["ar_tok_s"], (c["id"], ctx)
            assert best["results"][ctx]["mtp_tok_s"] >= c["results"][ctx]["mtp_tok_s"], (c["id"], ctx)
    p = best["physical"]
    assert (p["total_dies"], p["packages"], p["hbm_stacks"]) == (508, 254, 960)
    assert all(v["fits"] for v in p["power_w_saturated"].values())


def test_mapping_none_is_baseline_and_state_restored():
    f, rows, adj = u.A.die_fraction, dict(u.EXPERT_ROWS), u._cons_adjust
    r, _ = R.price(1048576, None, None)
    assert (r["ar_tok_s"], r["mtp_tok_s"]) == R.PINNED[1048576]
    assert u.A.die_fraction is f and u.EXPERT_ROWS == rows and u._cons_adjust is adj


def test_recommended_replays():
    cfg = {m[0]: m for m in R.mappings()}
    _, par2, mp, _ = cfg[REC["recommendation"]["mapping"]]
    r, _ = R.price(1048576, par2, mp)
    want = _cand(REC["recommendation"]["mapping"])["results"]["1048576"]
    assert (r["ar_tok_s"], r["mtp_tok_s"]) == (want["ar_tok_s"], want["mtp_tok_s"])


def test_ep_kmax_and_links():
    assert 2.1 < M.kmax(6, 8) < 2.3
    assert abs(REC["links"]["ucie_in_package"]["one_way_ns"] - 65.2) < 0.1
    assert abs(REC["links"]["board_light_fec"]["one_way_ns"] - 205.0) < 0.1
