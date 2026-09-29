"""W11 ring key layout: gate and region-preflight records are current and consistent (fast)."""

import json

from tools import w11_v41_hbm_region_preflight_ring as pre
from tools.w11_idx_ring_gate import OUT, sources


def test_gate_record_current_and_passing():
    rec = json.loads(OUT.read_text())
    assert rec["status"] == "pass"
    assert rec["sources_sha256"] == sources()
    assert all(rec["verdicts"].values())
    by = {c["name"]: c for c in rec["cases"]}
    assert not by["negative_no_migration"]["passed"]
    full = by["full_shape"]
    assert {r["user"] for r in full["reads"]} == {0, 481, 551, 865}
    assert all(r["checked"] == r["n"] for r in full["reads"] + by["ring_small"]["reads"])
    assert full["max_sector_address"] < 1 << 30
    assert by["ring_small"]["writer"]["migrations"] == 2 * (8223 // 32)


def test_preflight_record_matches_rebuild():
    rec = json.loads(pre.OUT.read_text())
    assert rec == json.loads(json.dumps(pre.build(), sort_keys=True))
    assert rec["status"] == "capacity_match"
    assert rec["capacity"]["users_ring_layout"] >= rec["capacity"]["users_model"] == 866
