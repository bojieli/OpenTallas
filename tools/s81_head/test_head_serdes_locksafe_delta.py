import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(__file__))
import head_serdes_locksafe_delta as D  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "results/die_head_52_1031/pin/source_plan_l48x.json"


def _plan():
    if PLAN.exists():
        return json.loads(PLAN.read_text())
    return {"partition_types": {"hd_serdes": {"contents": [{"inst": "u_phy", "module": D.OLD, "bind": {
        "ck": "clk", "rst_n": "rst_n", "pma_tx": "pad:pma_tx", "pma_tck": "pad:pma_tck", "pma_rx": "pad:pma_rx",
        "pma_rck": "pad:pma_rck"}}], "pads": [], "sources": []}, "hd_tile": {"contents": []}}}


def test_delta_only_touches_serdes():
    p = _plan()
    q = D.apply(p)
    for name in p["partition_types"]:
        if name != D.TYPE:
            assert q["partition_types"][name] == p["partition_types"][name]
    assert {k: v for k, v in q.items() if k != "partition_types"} == {k: v for k, v in p.items() if k != "partition_types"}
    t = q["partition_types"][D.TYPE]
    c = [c for c in t["contents"] if c["inst"] == "u_phy"][0]
    assert c["module"] == D.NEW and c["params"] == {"LOCKSAFE": 1, "HOLD_EDGES": 64}
    assert c["bind"]["pma_lock"] == "pad:pma_lock"
    assert [x for x in t["pads"] if x["name"] == "pma_lock"][0]["dir"] == "in"
    assert all(s in t["sources"] for s in D.SRC_NEW)
    assert t.get("hard_cores") == p["partition_types"][D.TYPE].get("hard_cores")


def test_delta_refuses_twice():
    with pytest.raises(ValueError):
        D.apply(D.apply(_plan()))


def test_wrapper_ports_bound():
    sys.path.insert(0, str(ROOT / "tools/die_plan"))
    import gen_rtl
    text = (ROOT / "rtl/dsrom_sys/s81_head/ot_s81hd_serdes_link_ls.sv").read_text()
    ports = gen_rtl.parse_leaf_ports(text, D.NEW)
    c = [c for c in D.apply(_plan())["partition_types"][D.TYPE]["contents"] if c["inst"] == "u_phy"][0]
    leaf_bound = set(c["bind"]) | {"coll_i0", "coll_o0"}
    assert set(ports) == leaf_bound
