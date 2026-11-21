"""S81-J6-ASSEMBLY-R4 11-21: the cfg7 RD_EXTRA=1 view (ot_s81_cfg7_seq_rdx_1121, S81 J7 RDX rows) has its HCP registry entry on main,
so kit GEN and die bind check the same parameter set (it lived only in the J7 tree tools copy before)."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
VIEW = REPO / "physical/die_plan/s81/cores/views/ot_s81_cfg7_seq_rdx_1121"


def _entries():
    reg = json.loads((HERE / "hard_core_built_params.json").read_text())["entries"]
    return [e for e in reg if e.get("lib_contains") == "ot_s81_cfg7_seq_rdx_1121/"]


def test_rdx_view_entry_matches_signed_receipt():
    (e,) = _entries()
    r = json.loads((VIEW / "receipt.json").read_text())
    assert e["module"] == r["module"] == "ot_s81_cfg7_seq" and e["die"] == "s81"
    assert e["params"] == r["params"] and e["params"]["RD_EXTRA"] == 1
    assert e["records"] == [r["signoff_sha256"]]


def test_rdx_entry_does_not_shadow_the_base_cfg7_views():
    reg = json.loads((HERE / "hard_core_built_params.json").read_text())["entries"]
    others = [e for e in reg if e.get("module") == "ot_s81_cfg7_seq" and e.get("lib_contains") != "ot_s81_cfg7_seq_rdx_1121/"]
    assert all("ot_s81_cfg7_seq_rdx_1121/" not in e.get("lib_contains", "") for e in others)
    assert all(e.get("params", {}).get("RD_EXTRA", 0) == 0 for e in others)
