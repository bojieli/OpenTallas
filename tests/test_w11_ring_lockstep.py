"""W11 ring reader control / quarter join 1.2 GHz forms: lockstep record current and passing (fast)."""

import json

from tools.w11_ring_lockstep import OUT, SOURCES, sha, ROOT


def test_lockstep_record_current_and_passing():
    rec = json.loads(OUT.read_text())
    assert rec["status"] == "pass"
    assert rec["sources_sha256"] == {p: sha(ROOT / p) for p in SOURCES}
    assert all(c["passed"] and c["mismatches"] == 0 for c in rec["cases"])
    assert {c["unit"] for c in rec["cases"]} == {"kctl_ring", "quarter_join"}
    assert all(m["failed_as_required"] and m["mismatches"] > 0 for m in rec["negative_controls"].values())
