"""KV-LEAF-BANKS: leaf / exact bit-group bank sites stay on CORE_AREA rows with the epoch-flop cell (PV-R7 19:19 / 21:59)."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kv_leaf_bank_sites as K  # noqa: E402
from kit_fit import kit_core_area  # noqa: E402

RTL_MIXED = "  ot_dp_st #(.W(3)) u_ist_o_x_0 (.clk(clk), .d({w_vport_W_a[1:0], w_other[0]}), .ea(ea));\n"
RTL_PURE = "  ot_dp_st #(.W(2)) u_ist_o_y_0 (.clk(clk), .d({w_vport_W_b[1:0]}), .ea(ea));\n"


def _plan(outline, rows):
    return {"partition_types": {"kv3_pv_v3": {"outline_um": outline, "hard_cores": [], "internal_stations": rows}}}


def _write(tmp, plan, rtl):
    (tmp / "rtl").mkdir()
    (tmp / "rtl" / "kv3_pv_v3_part.sv").write_text(rtl)
    (tmp / "plan.json").write_text(json.dumps(plan))


def _inside(t, x, y, w, h):
    x0, y0, x1, y1 = kit_core_area(t)
    return x >= x0 - 1e-6 and y >= y0 - 1e-6 and x + w <= x1 + 1e-6 and y + h <= y1 + 1e-6


def test_mixed_banks_at_the_north_edge_stay_on_rows(tmp_path):
    # station and its capture face sit 0.5-2 um from the north edge: the old generator (outline - 1.08 bounds, 1.188 cell)
    # put these bit sites above CORE_AREA (y + 0.27 > 195.68)
    rows = [{"conn": "bus:i_leaf", "capture": "leaf u_vport_W", "regs_um": [], "from_um": [100, 199], "to_um": [100, 199]},
            {"conn": "bus:o_x", "capture": "face bus o_x", "launch": "bus i_x", "regs_um": [[100, 198]],
             "from_um": [100, 199], "to_um": [100, 199.5]}]
    _write(tmp_path, _plan([200.0, 200.0], rows), RTL_MIXED)
    rep = {"kv3_pv_v3": {"moved": [], "unsolved": [], "mixed": [
        {"bus": "o_x", "width": 3, "leaf": "u_vport_W", "leaf_bits": 2, "old_hop": 310.0, "depth": 1}]}}
    (tmp_path / "pure.json").write_text(json.dumps(rep))
    K.main(["mixed", str(tmp_path / "plan.json"), str(tmp_path / "pure.json"), str(tmp_path / "rtl"),
            str(tmp_path / "out.json"), str(tmp_path / "rep.json")])
    t = json.loads((tmp_path / "out.json").read_text())["partition_types"]["kv3_pv_v3"]
    row = t["internal_stations"][1]
    assert row["bit_site_cell_um"] == [1.404, 0.27]
    sites = [p for st in row["bit_sites_um"] for p in st]
    assert len(sites) == 4                      # W leaf+forwarded bits + the epoch flop
    assert all(_inside(t, x, y, 1.404, 0.27) for x, y in sites)
    assert len({tuple(p) for p in sites}) == len(sites)
    from adv_bank_offarea import type_hits
    assert type_hits(t)[1] == []
    assert json.loads((tmp_path / "rep.json").read_text())["kv3_pv_v3"]["mixed"][0]["accepted"] is True


def test_off_area_site_refuses(tmp_path):
    plan = _plan([200.0, 200.0], [{"conn": "bus:o_x", "capture": "face bus o_x", "regs_um": [[100, 198]],
                                   "bit_sites_um": [[[100.0, 199.3]]], "bit_site_cell_um": [1.404, 0.27]}])
    with pytest.raises(SystemExit, match="outside CORE_AREA"):
        K.check_on_rows(plan, ["kv3_pv_v3"])


def test_pure_chain_regs_inside_core(tmp_path):
    rows = [{"conn": "bus:i_leaf", "capture": "leaf u_vport_W", "regs_um": [], "from_um": [10, 2], "to_um": [10, 2]},
            {"conn": "bus:o_y", "capture": "face bus o_y", "launch": "bus i_y",
             "regs_um": [[400, 1.5], [500, 1.5], [600, 1.5]], "from_um": [300, 1.5], "to_um": [700, 1.2]}]
    _write(tmp_path, _plan([800.0, 200.0], rows), RTL_PURE)
    K.main(["pure", str(tmp_path / "plan.json"), str(tmp_path / "rtl"), str(tmp_path / "out.json"),
            str(tmp_path / "rep.json"), "--types", "kv3_pv_v3"])
    t = json.loads((tmp_path / "out.json").read_text())["partition_types"]["kv3_pv_v3"]
    regs = t["internal_stations"][1]["regs_um"]
    assert len(regs) == 3
    a = K.centre_area(t)
    assert all(a[0] - 1e-6 <= x <= a[2] + 1e-6 and a[1] - 1e-6 <= y <= a[3] + 1e-6 for x, y in regs)
    assert json.loads((tmp_path / "rep.json").read_text())["kv3_pv_v3"]["moved"][0]["bus"] == "o_y"
