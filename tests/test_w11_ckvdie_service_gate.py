"""W11 CKV die-service gate record (results/rtl/w11_ckvdie_service_gate.json): the L20 selection's 512 compressed
rows through four dies' ot_chip_v41x_ckv_die_service, exact against the golden (QK and PV passes), the position's own
row selected, non-zero, re-encoded per rank and written home exactly by its owner; sources pinned."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_ckvdie_gate():
    r = json.loads((ROOT / "results/rtl/w11_ckvdie_service_gate.json").read_text())
    assert r["status"] == "pass" and not r["sources_dirty"]
    for rel, h in r["source_sha256"].items():
        assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == h, rel
    sel = r["selection"]
    assert sel["own_row_selected"] and sel["own_row_nonzero"] and sum(sel["owned_per_die"]) == 512 - 1 + 1
    assert len(r["runs"]) >= 2
    for run in r["runs"]:
        assert run["pass_"] and run["rows_checked"] == 4096 and run["row_errors"] == 0 and run["fmt_errors"] == 0
        assert run["own_row_write_exact"] and run["fields"]["hbm_miss"] == "0" and run["fields"]["faults"] == "0,0,0,0"
