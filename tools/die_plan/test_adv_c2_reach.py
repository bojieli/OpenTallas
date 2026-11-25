"""ADV-C2-REACH (FP-CONVERGE-QC 11-25): pass case (v13 shape) + mutant (pre-row kit shape) on synthetic st_a / stm types."""
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adv_c2_reach as A  # noqa: E402

RSTART = {"u_cland_rstart_tx_p%d/q" % i: [406.08, 447.552 + 244.512 * i] for i in range(4)}
GREAD = {"u_u_btab.u_bt.u_core.g_read[0].q[2]": [497.08, 700.0]}


def plan():
    sta = {"outline_um": [622.08, 1339.2],
           "clock": {"landing_reader_start": {"origin_rect_um": [349.92, 244.08, 367.2, 257.04]},
                     "landing_contract": {"pins": [{"name": "cland_rstart_out", "xy_um": [311.52, 1336.544]}]}},
           "relay_sites": dict(RSTART, **GREAD),
           "hard_cores": [{"inst": "u_bound.u_u_btab.u_bt.u_core.g_btb[1].u_m", "origin_um": [505.44, 801.432],
                           "outline_um": [94.824, 41.064]}]}
    stm = {"outline_um": [613.44, 1831.68], "buses": [{"name": "flt_o", "dir": "out", "face": "W", "width": 1}],
           "internal_stations": [{"conn": "bus:flt_o", "from_um": [198.9, 1433.4], "to_um": [0, 4.512],
                                  "regs_um": [[129.6, 959.04], [69.12, 483.84]]}]}
    return {"partition_types": {"sle_st_a_v1": sta, "sle_stm_v1": stm}}


def test_pass_v13_shape():
    out = A.findings(plan(), "p.json")
    assert not any(" reach " in x for x in out)
    assert any(x.startswith("WARN ADV-C2-REACH cbc sle_stm_v1 flt_o") for x in out)      # 548 um > CBC 405: advisory tier


def test_mutant_pre_row_shape_fires():
    p = copy.deepcopy(plan())
    p["partition_types"]["sle_st_a_v1"]["relay_sites"] = {}
    p["partition_types"]["sle_stm_v1"]["internal_stations"][0]["regs_um"] = []
    out = A.findings(p, "p.json")
    reach = [x for x in out if " reach " in x]
    assert any("sle_st_a_v1 rstart" in x for x in reach)
    assert any("sle_st_a_v1 btab" in x for x in reach)
    assert any("sle_stm_v1 flt_o" in x for x in reach)
    assert out[-1].startswith("WARN ADV-C2-REACH summary: 3 ")
