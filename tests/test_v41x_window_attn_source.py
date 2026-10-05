"""The WINDOW-only attention HBM replay is pinned to its exact source."""
import json

from tools.rtl_v41x_window_attn_source_gate import OUT, source_hashes


def test_window_attn_source_record_current():
    rec = json.loads(OUT.read_text())
    assert rec["status"] == "pass"
    assert rec["sources"] == source_hashes()
    assert rec["jobs"] == 2
    assert rec["hbm_sector_requests"] == 4352
    assert rec["accepted_packed_beats"] == 64
    assert rec["stale_cross_user_fault"]
