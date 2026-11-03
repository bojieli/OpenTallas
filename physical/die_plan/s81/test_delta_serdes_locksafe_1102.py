import importlib.util
import re
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("dsl", HERE / "delta_serdes_locksafe_1102.py")
dsl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dsl)
ROOT = HERE.parents[2]


def serdes():
    pads = [dict(name="io_pma_tx", dir="out", width=544), dict(name="io_pma_tck", dir="out", width=1),
            dict(name="io_pma_rx", dir="in", width=544), dict(name="io_pma_rck", dir="in", width=1)]
    ser = dict(module="s81p_serdes__t3", pads=pads, contents=[dict(inst="u_phy", module="ot_pdie_serdes")],
               clock=dict(pad_clock=dict(pins=[dict(name="io_pma_rck", cdc_evidence="gray FIFO")])), note="serdes")
    return ser


def plan():
    other = dict(module="s81p_iqf", pads=[], contents=[dict(inst="u_q", module="dsdv_iqf")], note="iqf")
    return dict(partition_types={"serdes__t3": serdes(), "serdes__t1__clx": serdes(), "iqf": other}, partitions=[], ports=[])


def test_delta_adds_lock_pad_only_on_serdes_types():
    p = plan()
    out = dsl.apply(p)
    for tn in ("serdes__t3", "serdes__t1__clx"):
        t = out["partition_types"][tn]
        assert [x["name"] for x in t["pads"]][-1] == "io_pma_lock"
        assert t["pads"][-1]["dir"] == "in" and t["pads"][-1]["width"] == 1
        assert t["pads"][:4] == p["partition_types"][tn]["pads"]
        assert t["contents"] == p["partition_types"][tn]["contents"]
        assert "ot_pdie_pma_reset_hold" in t["clock"]["pad_clock"]["pins"][0]["cdc_evidence"]
    assert out["partition_types"]["iqf"] == p["partition_types"]["iqf"]
    assert p["partition_types"]["serdes__t3"]["pads"][-1]["name"] == "io_pma_rck"  # input untouched


def test_delta_refuses_twice_and_non_column():
    out = dsl.apply(plan())
    with pytest.raises(ValueError):
        dsl.apply(out)
    bad = plan()
    bad["partition_types"]["serdes__t3"]["contents"][0]["module"] = "other"
    with pytest.raises(ValueError):
        dsl.apply(bad)


def test_source_wiring_matches_delta():
    """die_b178.v: every u_lk_* column runs LOCKSAFE=1 HOLD_EDGES=64 on its own lk_*_pma_lock die input, and every
    S81 manifest maps that input to the partition role pma_lock (the pad name io_pma_lock) and lists the shared file."""
    v = (ROOT / "physical/die_plan/s81/bind/inputs/die_b178.v").read_text()
    inst = re.findall(r"^  ot_pdie_serdes_col (#\(.*?\) )?u_lk_(\w+) \(.*\.pma_lock\(lk_(\w+)_pma_lock\)\);$", v, re.M)
    assert len(inst) == 14 and all(p == "#(.LOCKSAFE(1), .HOLD_EDGES(64)) " and a == b for p, a, b in inst)
    assert len(re.findall(r"^  input wire lk_\w+_pma_lock;", v, re.M)) == 14
    assert len(re.findall(r"^  ot_pdie_serdes_col ", v, re.M)) == 14
    import json
    rx = None
    for f in sorted((ROOT / "physical/die_plan/s81/bind").glob("asbuilt*.json")):
        m = json.loads(f.read_text())
        if "io_roles" not in m:
            continue
        assert "rtl/dsrom_sys/s81_link/ot_pdie_serdes_locksafe.sv" in m["files"], f.name
        rx = re.compile(m["io_roles"][0][0])
        assert rx.fullmatch("lk_WS0_pma_lock").expand(m["io_roles"][0][1]) == "pma_lock", f.name
    assert rx is not None
    col = (ROOT / "rtl/dsrom_sys/s81_link/col/ot_pdie_serdes_col.sv").read_text()
    assert "ot_pdie_pma_reset_hold #(.HOLD_EDGES(HOLD_EDGES))" in col and "parameter integer LOCKSAFE = 0" in col
    assert "module ot_pdie_pma_reset_hold" not in col  # shared module, no fork
