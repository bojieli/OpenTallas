"""The packed-attention service record pins the RTL boundary actually linted."""
import json

from tools.rtl_v41x_packed_attn_service_gate import OUT, source_hashes


def test_service_gate_is_current():
    rec = json.loads(OUT.read_text())
    assert rec["status"] == "pass"
    assert rec["sources"] == source_hashes()
    assert rec["scheduler"] == {
        "jobs": 3, "window_rows": 6, "users": 2,
        "boundary_positions": [126, 127, 128, 129, 254, 1048575],
    }
