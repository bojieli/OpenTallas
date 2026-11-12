"""KV-HG-SPLIT-1 11-12: HG-EX plan cut (vF form: EX 1..3 hard, EX 0 soft clone; fail-closed slot checks)."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("hg_ex_plan_cut", HERE / "plan_cut.py")
PC = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(PC)
REPO = HERE.parents[4]
VIEW = REPO / PC.VIEW_DIR


def plan():
    inst = [f"astk__u_strip_u_strip_g_ep_p__g_ex_{k}__u_ex" for k in range(4)]
    t = dict(note="hg", outline_um=[1278.72, 1520.64],
             contents=[dict(inst=i, module=PC.MODULE) for i in inst] + [dict(inst="x", module="other")],
             hard_cores=[dict(inst="head0_e0", module="kv3_head_eighth_e0", origin_um=[17.28, 17.28],
                              outline_um=[216.0, 216.0], orient="MX")],
             clock=dict(taps=[dict(name="head0_e0.ck[0]", kind="core", xy=[100.0, 100.0])],
                        die_islands_um=[[438.588, 563.22, 441.288, 564.03], [13.068, 759.78, 15.768, 760.59]],
                        landing_contract=dict(bands=dict(ft2_i=dict(rect_um=[17.28, 571.32, 313.2, 644.76])),
                                              collector_tree=dict(relays=[dict(name="u_rrl_48", xy=[479.52, 570.24])]))),
             reset=dict(tap_um=[630.72, 760.32]))
    return dict(partition_types=dict(kv3_hg_v1=t, other=dict(note="o", contents=[], clock={})))


def test_vf_form_three_hard_one_soft_clone():
    p, types, resite = PC.apply(plan(), (1, 2, 3), "qkd_astk_ex_s_soft")
    t = p["partition_types"]["kv3_hg_v1"]
    new = [h for h in t["hard_cores"] if h["module"] == PC.MODULE]
    assert types == ["kv3_hg_v1"] and [h["inst"].split("_ex_")[1][0] for h in new] == ["1", "2", "3"]
    assert [h["origin_um"] for h in new] == [[371.52, 561.6], [665.28, 561.6], [984.96, 561.6]]
    assert [h["orient"] for h in new] == ["R0", "MY", "MY"]
    assert all(h["physical_master"] == PC.MODULE and h["outline_um"] == PC.OUTLINE for h in new)
    assert t["soft_clones"] == [dict(physical_inst="u_bound.u_astk_u_strip_u_strip_g_ep_p_g_ex_0_u_ex",
                                     base=PC.MODULE, master="qkd_astk_ex_s_soft")]
    taps = {x["name"]: x["xy"] for x in t["clock"]["taps"] if x["name"].endswith("_u_ex.ck")}
    assert taps["astk__u_strip_u_strip_g_ep_p__g_ex_1__u_ex.ck"] == [466.584, 617.76]
    assert taps["astk__u_strip_u_strip_g_ep_p__g_ex_2__u_ex.ck"] == [round(665.28 + 190.08 - 95.064, 3), 617.76]
    # island under EX1 removed and reported; the other island stays; relay under EX1 reported for the reset re-solve
    assert t["clock"]["die_islands_um"] == [[13.068, 759.78, 15.768, 760.59]]
    kinds = sorted((r["kind"], r.get("name", "")) for r in resite)
    assert kinds == [("collector_relay", "u_rrl_48"), ("die_clock_island", "")]
    assert "KV-HG-SPLIT-1" in t["note"]


def test_slot0_band_fails_closed():
    with pytest.raises(ValueError, match="EX0 .*landing_band"):
        PC.apply(plan(), (0, 1, 2, 3))


def test_soft_needs_clone_master():
    with pytest.raises(ValueError, match="soft-master"):
        PC.apply(plan(), (1, 2, 3))


def test_hard_core_under_slot_fails():
    p = plan()
    p["partition_types"]["kv3_hg_v1"]["hard_cores"].append(dict(inst="blk", module="m", origin_um=[700.0, 600.0],
                                                                outline_um=[10.0, 10.0], orient="R0"))
    with pytest.raises(ValueError, match="EX2 .*hard_core"):
        PC.apply(p, (1, 2, 3), "qkd_astk_ex_s_soft")


def test_input_not_mutated_and_double_cut_refused():
    p = plan()
    keep = copy.deepcopy(p)
    q, _, _ = PC.apply(p, (1, 2, 3), "s")
    assert p == keep
    with pytest.raises(AssertionError, match="already cut"):
        PC.apply(q, (1, 2, 3), "s")


def test_pins_equal_signed_view_pin_table():
    """the plan pin table hashes to the one the SIGNED view was built from (provenance pins_sha256)"""
    prov = json.loads((VIEW / "provenance.json").read_text())["kit"]
    txt = json.dumps(PC.pins(), indent=1) + "\n"
    assert hashlib.sha256(txt.encode()).hexdigest() == prov["pins_sha256"]
    assert prov["outline_um"] == PC.OUTLINE and prov["module"] == PC.MODULE
    assert json.loads((VIEW / "provenance.json").read_text())["verdict"].startswith("SIGNED")
