"""S81-CORES-R3 11-17 (COORD r561): the REAL dsdv_bk_sel binds its hard bksel cores with the parameter sets of their signed
views, as HCPARAM-ALL sees them (dsdv_bksel_c is no longer allowlisted)."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hard_core_param_all as A

REPO = HERE.parents[1]
BK = REPO / "rtl/dsrom_sys/s81_dv/unit/bk"


def _found(defines):
    idx, _ = A.load_index([BK / "dsdv_bk_sel.sv", BK / "dsdv_bksel_c.sv"], defines)
    got = {}
    for f in A.elaborate(idx, "dsdv_bk_sel", {"dsdv_bksel_c", "dsdv_bksel_q"}):
        got.setdefault(f.module, []).append(f)
    return got


def _registry(module):
    reg = json.loads((HERE / "hard_core_built_params.json").read_text())["entries"]
    return [e for e in reg if e.get("module") == module and e.get("die") == "s81"]


def test_control_is_bound_with_its_signed_rfd6_parameters():
    (c,) = _found([])["dsdv_bksel_c"]
    (e,) = _registry("dsdv_bksel_c")
    assert {k: c.eff[k] for k in e["params"]} == e["params"] == {"OLL": 2, "SELOH": 1, "RNF": 1, "LQH": 1}
    assert c.eff["QRX"] == 0


def test_default_quarters_are_hq3_and_eco3_quarters_take_the_eco3_set_with_control_qrx():
    q = _found([])["dsdv_bksel_q"]
    assert q and all((f.eff["OLL"], f.eff["RFH"]) == (0, 0) for f in q)
    got = _found(["OT_BKQ_ECO3"])
    assert got["dsdv_bksel_q"] and all((f.eff["OLL"], f.eff["RFH"], f.eff["HLAT"]) == (2, 2, 1) for f in got["dsdv_bksel_q"])
    (c,) = got["dsdv_bksel_c"]
    assert c.eff["QRX"] == 1 and c.eff["LQH"] == 1


def test_control_no_longer_allowlisted():
    a = json.loads((HERE / "hard_core_param_allow.json").read_text())
    assert not [e for e in a["entries"] if e.get("die") == "s81" and "dsdv_bksel_c" in e.get("modules", [])]
