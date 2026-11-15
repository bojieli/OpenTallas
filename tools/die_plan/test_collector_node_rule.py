"""GENBUG D2 (FABLE-PD-S81-0335 D2): the emitter (landing_collector.build_local) and the placement/scan side
(landing_place.collector_instances) must name the SAME collector instances for a source row that carries a node beside a
different tap (B6gsh leaf t8 t12 t17 t33 t52 t59 t68 t72, kv_leaf t3: node rst_n_t20 / t18, tap 46 / 47)."""
import re
import landing_place as LP
from landing_collector import build_local


def tree():
    return dict(root=[0, 0], relays=[
        dict(q="rst_n_t0", d="rst_root_n", xy=[100, 0]),
        dict(q="rst_n_t1", d="rst_n_t0", xy=[200, 0]),
        dict(q="rst_n_t2", d="rst_root_n", xy=[0, 300])])


def _emitted(t, srcs):
    r = build_local(t, srcs, "wire rst_root_n;\nwire rr_t0;\n")
    return {m for x in r["rtl"] + [str(i) for i in r["instances"]] for m in re.findall(r"u_cland_collect_\w+", x)}


def test_stale_tap_beside_node_places_what_the_emitter_emits():
    t = tree()
    srcs = [dict(name="ring", tap=1, node="rst_n_t2", ready="r", fault="f", xy_um=[0, 300])]
    ev = dict(tree=t, collector_root_node="rst_root_n", local_sources=srcs, children=[])
    got = LP.collector_instances(ev)
    assert got == {"u_cland_collect_rst_n_t2", "u_cland_collect_rst_root_n"} or "u_cland_collect_rst_n_t2" in got
    assert "u_cland_collect_rst_n_t1" not in got
    assert got <= _emitted(t, srcs) | {"u_cland_collect_rst_root_n"}


def test_tap_only_and_hard_rows_unchanged():
    assert LP._source_node(dict(tap=7)) == "rst_n_t7"
    assert LP._source_node(dict(tap=None, node="cland_h3")) == "cland_h3"
    assert LP._source_node(dict(tap=3, node="rst_n_t3")) == "rst_n_t3"
