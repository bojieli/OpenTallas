import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import uarch_model as u  # noqa: E402
import uarch_model_par2_boundary as X  # noqa: E402
import dsrom_par2_boundary as T  # noqa: E402

REC = ROOT / "results/uarch/dsrom_par2_boundary_20261003/model.json"


def test_census_matches_source_binding():
    c = X.call_census()
    assert c["calls"] == 1149
    assert c["crossing_calls"] + c["local_calls"] == 1149
    assert c["crossing_calls"] == 1050
    assert X.crossing_keys() == {"a_proj", "wq_b", "wo_a", "wo_b", "shared_gu", "experts_gu", "down", "wkv"}
    assert c["per_model_key"]["router"]["crosses"] is False


def test_default_off_reproduces_baseline():
    r = T.price(58, 1048576, None)
    # Historical rates omitted physical endpoint wires. Default-off now uses
    # the corrected common baseline, rather than reproducing that omission.
    assert r["ar_tok_s"] < T.PINNED[1048576][0]
    assert r["mtp_tok_s"] < T.PINNED[1048576][1]
    assert "par2_passes" not in r
    assert u._cons_adjust.__name__ == "_cons_adjust"


def test_owner_term_is_two_crossings_per_crossing_step():
    clock = u.PRODUCT_CLOCK_HZ
    cfg = X.default_cfg("owner")
    one = X.one_way_s(cfg, clock)
    assert abs(one - (2 * 34 / clock + 8.5e-9)) < 1e-15
    r = T.price(58, 1048576, cfg)
    assert u._cons_adjust.__name__ == "_cons_adjust"          # wrapper restored
    p1 = r["par2_passes"][0]
    assert p1["P"] == 1 and p1["field"] == 7 * 40 + 2       # 7 crossing steps a layer + 2 Engram wkv
    assert r["ar_tok_s"] < T.PINNED[1048576][0]


def test_bandwidth_never_serialises():
    b = X.bandwidth_check(X.default_cfg("owner"), u.PRODUCT_CLOCK_HZ)
    assert b["headroom"] > 1 and b["serialisation_exposed_s"] == 0.0


def test_record_replays_byte_identically(tmp_path):
    if not REC.exists():
        return
    rec = json.loads(REC.read_text())
    assert rec["default_off"] and rec["baseline_reproduced"]
    for r in rec["results"]:
        if r["id"] == "base_S58":
            assert (r["ar_tok_s"], r["mtp_tok_s"]) == T.PINNED[r["ctx"]]


def test_expert_split_crosses_only_the_expert_step():
    cfg = X.default_cfg("owner", split="experts")
    r = T.price(58, 1048576, cfg)
    p1 = r["par2_passes"][0]
    assert p1["field"] == 2 * 40                       # experts_gu in, down out, every layer
    owner = T.price(58, 1048576, X.default_cfg("owner"))
    assert r["ar_tok_s"] > owner["ar_tok_s"]
