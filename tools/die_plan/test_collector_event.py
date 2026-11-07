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
