"""DIE-KV-14b pv_pair plan delta: macro leaves at the register-leaf stage count + the lc RTL generator is current.
    python3 -m pytest -q results/die_kv_14_1028/pv_pair/test_pv_macro_leaves.py"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import pv_macro_leaves as PM  # noqa: E402


def test_tritoncts_stage_census():
    # fMX 4_1_cts.log: 7429 sinks -> 310 clusters, H-tree levels 1..5, worst path regs-root + 0,1,3,5 + leaf = 6
    assert PM.tritoncts_stages(7429) == 6
    assert PM.tritoncts_stages(24 * 15) == 3          # no H-tree level: split root + root + leaf


@pytest.mark.parametrize("form", ["fMX", "R0"])
def test_macro_leaves_equal_total_stages(form):
    sl = json.loads((ROOT / f"results/qk_cores_11_1027/pv_tree_slice_{form}.json").read_text())
    new, plan, S = PM.apply(sl)
    t = plan["core_tree"]
    assert S == 6 and t["depth"] == 8 and t["stage_basis"] == "total"
    assert t["cts_open"] == [f"mp_pv_ck_isl{j}" for j in range(4)]
    nodes = {n["name"]: n for n in t["nodes"]}
    mac = [l for l in t["leaves"] if l.get("load_class") == "macro"]
    assert len(mac) == 4 and sum(len(l["sinks"]) for l in mac) == 8
    for l in mac:                                      # chain of S+1 BUFx24 from the BRANCH buffer, inside the island
        n, k = l["node"], 0
        while not nodes[n]["parent"].startswith("mp_pv_ck_br"):
            assert nodes[n]["master"] == PM.CHAIN_MASTER
            n, k = nodes[n]["parent"], k + 1
        assert k + 1 == S + 1
    for n in nodes.values():                           # KV-KITS-15: chain cell footprint (xy = centre) inside its island
        if n["name"].startswith("mp_pv_ck_mac"):
            x0, y0, x1, y1 = n["island_rect_um"]
            x, y = n["xy_um"]
            assert x0 <= x - PM.CHAIN_W_UM / 2 and x + PM.CHAIN_W_UM / 2 <= x1 and y0 <= y - PM.ROW_UM / 2 and y + PM.ROW_UM / 2 <= y1
    for l in t["leaves"]:                              # island nets carry registers only
        if l["node"].startswith("mp_pv_ck_isl"):
            assert l.get("cts_open") and not any("u_mem" in s for s in l["sinks"])
    with pytest.raises(SystemExit):
        PM.apply(new)                                  # idempotence guard


def test_slice_lc_rtl_is_current():
    r = subprocess.run([sys.executable, str(HERE / "gen_slice_lc.py"), "--check"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
