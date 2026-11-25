"""STATUS-UP 11-25 (FABLE-RC-S81, leaf t36 c8s post-CTS): a collector whose root is a local relay far from the
cland_up_ready/fault pins (u_cland_collect_rst_n_t63 at (588,104) -> E-face pin, 1974 um, 20 buffers, -547.7 ps) takes
a registered egress CHAIN: stations u_cland_collect_egress_s<k> then the face register u_cland_collect_egress, each one
status cycle, each reset by its own local relay (no long reset-recovery leg to the root)."""
import pytest
from landing_collector import build_local, collector_egress, egress_chain, egress_instances
from landing_place import collector_instances


def tree():
    return dict(root=[0, 0], relays=[
        dict(q="rst_n_t0", d="rst_root_n", xy=[100, 0]),
        dict(q="rst_n_t1", d="rst_n_t0", xy=[400, 0]),
        dict(q="rst_n_t2", d="rst_n_t1", xy=[700, 0]),
        dict(q="rst_n_t3", d="rst_n_t2", xy=[1000, 0])])


def contract(eg):
    return dict(collector_egress_um=eg, pins=[
        dict(name="cland_up_ready", dir="out", xy_um=[0, 2]), dict(name="cland_up_fault", dir="out", xy_um=[0, 4])])


CHAIN = [dict(xy_um=[700, 0], node="rst_n_t2"), dict(xy_um=[400, 0], node="rst_n_t1"),
         dict(xy_um=[100, 2], node="rst_n_t0"), [20, 2]]


def test_single_site_form_unchanged():
    assert egress_chain([10, 2], "rst_root_n") == [("u_cland_collect_egress", [10, 2], "rst_root_n")]
    e = collector_egress(tree(), contract([10, 2]), "rst_root_n", 405)
    assert e["added_collector_cycles"] == 1 and set(e["legs_um"]) == {"reset_and_status_root", "cland_up_ready",
                                                                        "cland_up_fault"}


def test_single_site_with_local_root_still_refused():
    with pytest.raises(ValueError, match="station list"):
        collector_egress(tree(), contract([10, 2]), "rst_n_t3", 405)


def test_chain_from_local_root_emits_stations_then_face():
    e = collector_egress(tree(), contract(CHAIN), "rst_n_t3", 405)
    assert e["added_collector_cycles"] == 4 and max(e["legs_um"].values()) <= 405
    s = [dict(name="ring", tap=3, ready="r", fault="f", xy_um=[1000, 0])]
    body = "wire rr_t0;\nwire rr_t1;\nwire rr_t2;\nwire rr_t3;\n"
    r = build_local(tree(), s, body, root_node="rst_n_t3", egress=e)
    rtl = "\n".join(r["rtl"])
    names = [i["name"] for i in r["instances"] if i["module"] == "ot_dp_landing_collect"]
    assert names == ["u_cland_collect_rst_n_t3", "u_cland_collect_egress_s0", "u_cland_collect_egress_s1",
                     "u_cland_collect_egress_s2", "u_cland_collect_egress"]
    assert rtl.count(".ready_o(cland_up_ready)") == 1
    assert "u_cland_collect_egress_s0 (\n        .clk(clk), .rst_n(rr_t2), .ready_i(cland_r_rst_n_t3)" in rtl
    assert ".rst_n(rr_t0), .ready_i(cland_eg_r1)" in rtl
    assert "u_cland_collect_egress (\n        .clk(clk), .rst_n(rst_n_t3), .ready_i(cland_eg_r2)" in rtl
    assert r["depth"] == 1 + 4
    assert egress_instances(CHAIN) == names[1:]
    ev = dict(tree=tree(), collector_root_node="rst_n_t3", local_sources=[dict(name="ring", tap=3, node="rst_n_t3")],
              children=[], collector_egress_um=CHAIN)
    assert collector_instances(ev) == set(names)


def test_chain_leg_over_reach_and_unknown_reset_node_refused():
    with pytest.raises(ValueError, match="exceeds R4"):
        collector_egress(tree(), contract([CHAIN[0], [20, 2]]), "rst_n_t3", 405)
    with pytest.raises(ValueError, match="not a collector-tree relay"):
        collector_egress(tree(), contract([dict(xy_um=[700, 0], node="rst_n_t9"), [20, 2]]), "rst_n_t3", 405)
