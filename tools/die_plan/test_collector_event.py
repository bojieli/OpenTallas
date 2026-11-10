"""KW-FIX-27 11-07 three-reset-tree class: collector placement follows the sidecar event the collector RTL came from, not
the native captured solve in contract collector_tree (TYPE-SAFE-3), and a kit whose RTL disagrees stops at gen."""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_phys
import gen_rtl
import landing_collector as LC
import landing_place as LP


def rel(q, d, xy):
    return dict(q=q, d=d, xy=xy)


EVENT_TREE = dict(root=[0, 0], relays=[rel("rst_rl_38", "rst_root_n", [10, 0]), rel("rst_rl_22", "rst_rl_38", [20, 0]),
                                       rel("rst_n_t0", "rst_rl_22", [30, 0])])
NATIVE_TREE = dict(root=[0, 0], relays=[rel("rst_rl_30", "rst_root_n", [11, 0]), rel("rst_rl_16", "rst_rl_30", [21, 0]),
                                        rel("rst_n_t0", "rst_rl_16", [31, 0])])
SRC = dict(name="b", tap=0, xy_um=[30, 0], ready="r", fault="f")
EVENT = dict(tree=EVENT_TREE, collector_root_node="rst_root_n", local_sources=[SRC], children=[])
NAMES = {"u_cland_collect_rst_root_n", "u_cland_collect_rst_rl_38", "u_cland_collect_rst_rl_22", "u_cland_collect_rst_n_t0"}


def plan(contract):
    t = dict(clock=dict(landing_contract=contract), buses=[], contents=[], hard_cores=[], outline_um=[100, 100])
    return SimpleNamespace(types={"T": t}, raw=dict(partition_types={"T": t}))


def contract():
    return dict(pins=[], bands={}, collector_tree=NATIVE_TREE, collector_root_node="rst_root_n",
                collector_local_sources=[SRC], collector_children=[])


def rtl(tmp_path, names):
    f = tmp_path / "T_bound.sv"
    f.write_text("module T;\n" + "".join(f"  ot_dp_landing_collect #(.N(1)) {n} (.clk(clk), .rst_n(x));\n"
                                         for n in sorted(names)) + "endmodule\n")
    return [f]


def lands(info=None):
    info = info or dict(EVENT, mask=dict(active=True))
    return SimpleNamespace(collector=dict(types=dict(T=info)), dataflow=False)


def test_active_set_is_what_the_rtl_builder_emits():
    body = "\n".join(f"wire {r['q']};" for r in EVENT_TREE["relays"])
    out = LC.build_local(EVENT_TREE, [SRC], body, root_node="rst_root_n")
    assert {i["name"] for i in out["instances"] if i["module"] == "ot_dp_landing_collect"} == LP.collector_instances(EVENT) == NAMES


def test_placement_names_come_from_event_not_native_solve(tmp_path):
    P = plan(contract())
    gen_phys.install_collector_event(P, "T", lands(), rtl(tmp_path, NAMES))
    text = LP.tcl(P, "T")
    assert "u_cland_collect_rst_rl_38 " in text and "u_cland_collect_rst_rl_22 " in text
    assert "u_cland_collect_rst_rl_30" not in text and "u_cland_collect_rst_rl_16" not in text
    # the native solve stays where the bound_reset mapping reads it
    assert P.types["T"]["clock"]["landing_contract"]["collector_tree"] is NATIVE_TREE


def test_rtl_disagreeing_with_event_stops_at_gen(tmp_path):
    with pytest.raises(gen_rtl.GenError, match="differs from the bound collector RTL"):
        gen_phys.install_collector_event(plan(contract()), "T", lands(), rtl(tmp_path, NAMES - {"u_cland_collect_rst_rl_22"}))


def test_no_event_or_inactive_keeps_published_tree(tmp_path):
    P = plan(contract())
    gen_phys.install_collector_event(P, "T", SimpleNamespace(collector=None, dataflow=False), [])
    gen_phys.install_collector_event(P, "T", lands(dict(EVENT, mask=dict(active=False))), [])
    assert "collector_event" not in P.types["T"]["clock"]["landing_contract"]
    assert "u_cland_collect_rst_rl_30 " in LP.tcl(P, "T")


# DIE-S81-85 11-09 (dsdv_slice_kv512_C__t1, plan 65648816 + bind6): the bind walked the plan collector_tree
# (LC.effective_tree, S81-OTHERFAIL-1) while the sidecar kept an older table tree; gen must check the bind's tree.
PLAN_TREE = dict(root=[0, 0], relays=[rel("rst_rl_45", "rst_root_n", [12, 0]), rel("rst_rl_57", "rst_rl_45", [22, 0]),
                                      rel("rst_n_t0", "rst_rl_57", [32, 0])])
PLAN_NAMES = {"u_cland_collect_rst_root_n", "u_cland_collect_rst_rl_45", "u_cland_collect_rst_rl_57",
              "u_cland_collect_rst_n_t0"}


def bind_names(plan_tree, table_tree):
    tree = LC.effective_tree(dict(clock=dict(landing_contract=dict(collector_tree=plan_tree))), table_tree)
    body = "\n".join(f"wire {r['q']};" for r in tree["relays"])
    out = LC.build_local(tree, [SRC], body, root_node="rst_root_n")
    return {i["name"] for i in out["instances"] if i["module"] == "ot_dp_landing_collect"}


def test_plan_tree_the_bind_walked_passes_over_stale_sidecar_tree(tmp_path):
    assert bind_names(PLAN_TREE, EVENT_TREE) == PLAN_NAMES
    c = contract()
    c["collector_tree"] = PLAN_TREE
    P = plan(c)
    gen_phys.install_collector_event(P, "T", lands(), rtl(tmp_path, PLAN_NAMES), plan_tree=PLAN_TREE)
    assert P.types["T"]["clock"]["landing_contract"]["collector_event"]["tree"] is PLAN_TREE
    text = LP.tcl(P, "T")
    assert "u_cland_collect_rst_rl_45 " in text and "u_cland_collect_rst_rl_38" not in text


def test_without_plan_tree_the_stale_sidecar_still_stops(tmp_path):
    with pytest.raises(gen_rtl.GenError, match="differs from the bound collector RTL"):
        gen_phys.install_collector_event(plan(contract()), "T", lands(), rtl(tmp_path, PLAN_NAMES))


def test_rtl_from_sidecar_event_still_passes_with_a_plan_tree(tmp_path):
    # KW-FIX-27 form: RTL from the sidecar event; plan_tree (here the native solve) does not hide it
    P = plan(contract())
    gen_phys.install_collector_event(P, "T", lands(), rtl(tmp_path, NAMES), plan_tree=NATIVE_TREE)
    assert P.types["T"]["clock"]["landing_contract"]["collector_event"]["tree"] is EVENT_TREE


def test_rtl_matching_neither_tree_stops(tmp_path):
    with pytest.raises(gen_rtl.GenError, match="plan collector_tree checked too"):
        gen_phys.install_collector_event(plan(contract()), "T", lands(), rtl(tmp_path, PLAN_NAMES - {"u_cland_collect_rst_rl_57"}),
                                         plan_tree=PLAN_TREE)
