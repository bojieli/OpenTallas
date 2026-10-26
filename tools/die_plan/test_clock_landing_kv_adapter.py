"""KV-LAND-R3 (2026-10-26): clock_landing_plan.compose adapter for plans whose bus geometry lives on die-frame
ports with mirrored/rotated replicas (KV), hard partitions without a reset tree (KV hard PHY), and a
configurable observer.  QC behaviour stays the default."""
import copy
import json
from pathlib import Path

import pytest

import clock_landing_plan as C
import clock_landings as CL
import landing_collector as LC

HERE = Path(__file__).resolve().parent
TINY = json.loads((HERE / "examples" / "tiny_plan.json").read_text())


def table(*pids):
    return dict(ports=[dict(port=p) for p in pids])


def test_port_window_maps_to_type_frame_r0():
    raw = copy.deepcopy(TINY)
    C._fill_port_windows(raw, None, table("x0"))
    g = raw["partition_types"]["src"]["_cland_geom"]["x_o"]
    assert g["face"] == "E" and g["window_um"] == [400.0, 420.0]
    assert C._bus_xy(raw["partition_types"]["src"], "x_o") == [864.0, 410.0]


def test_port_window_maps_through_mx_orient():
    raw = copy.deepcopy(TINY)
    raw["partitions"][0]["orient"] = "MX"           # pa mirrored about x: y -> h - y, E stays E
    C._fill_port_windows(raw, None, table("x0"))
    g = raw["partition_types"]["src"]["_cland_geom"]["x_o"]
    assert g["face"] == "E" and g["window_um"] == [444.0, 464.0]


def test_port_window_maps_through_my_orient_flips_face():
    raw = copy.deepcopy(TINY)
    raw["partitions"][0]["orient"] = "MY"           # pa mirrored about y: the die E face is the type W face
    C._fill_port_windows(raw, None, table("x0"))
    g = raw["partition_types"]["src"]["_cland_geom"]["x_o"]
    assert g["face"] == "W" and g["window_um"] == [400.0, 420.0]


def test_nonuniform_replica_windows_fail_closed():
    raw = copy.deepcopy(TINY)
    raw["partitions"][2]["orient"] = "MX"           # pm2 differs from pm1: one type, two type-local windows
    with pytest.raises(ValueError, match="nonuniform type-local landing window"):
        C._fill_port_windows(raw, None, table("x1", "x2"))


def test_declared_type_geometry_is_untouched():
    raw = copy.deepcopy(TINY)
    b = next(b for b in raw["partition_types"]["src"]["buses"] if b["name"] == "x_o")
    b.update(face="E", window_um=[1.0, 2.0])
    C._fill_port_windows(raw, None, table("x0"))
    assert "x_o" not in raw["partition_types"]["src"].get("_cland_geom", {})
    assert C._bus_geom(raw["partition_types"]["src"], "x_o")["window_um"] == [1.0, 2.0]


def test_hard_tree_stages_within_reach_and_end_at_entry():
    t = C._hard_tree([842.4, 760.32], [432.0, 1520.64])
    pts = [[842.4, 760.32]] + [r["xy"] for r in t["relays"]] + [[432.0, 1520.64]]
    hops = [abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(pts, pts[1:])]
    assert max(hops) <= 405 and len(t["relays"]) == 2
    assert t["relays"][0]["d"] == "rst_root_n" and t["leaf_node"] == t["relays"][-1]["q"]
    assert C._hard_tree([0, 0], [100, 100])["relays"] == []      # within reach: collector at the entry only


def test_hard_chain_rtl_registered_on_delivered_reset():
    t = C._hard_tree([842.4, 760.32], [432.0, 1520.64])
    r = LC.build_hard_chain(t, [dict(name="ft0_i", node=t["leaf_node"], xy_um=[432.0, 1520.64],
                                     ready="landing_ready_ft0_i", fault="landing_fault_ft0_i")])
    rtl = "\n".join(r["rtl"])
    assert r["data_cycles_added"] == 0 and r["depth"] == 3 and r["max_hop_um"] <= 405
    assert rtl.count("ot_dp_landing_collect") == 3 and ".rst_n(rst_n)" in rtl
    assert ".ready_o(cland_up_ready), .fault_o(cland_up_fault)" in rtl
    with pytest.raises(ValueError, match="exceeds"):
        LC.build_hard_chain(t, [dict(name="x", node=t["leaf_node"], xy_um=[0, 0], ready="r", fault="f")])


def test_hard_partition_cannot_collect_children():
    class P:
        parts = dict(a=dict(type="H"), b=dict(type="S"))
        types = dict(H=dict(hard=True), S=dict())
    W = dict(parts=dict(a=dict(parent=None), b=dict(parent="a", source="a.rst_o_0")))
    with pytest.raises(ValueError, match="hard partition cannot collect"):
        C._monitor_endpoints(P, W, "b", "a")


def test_observer_default_is_qc_and_spec_is_validated():
    assert C.QC_OBSERVER == dict(module="qfd_sys_face_lctx3_wrapped", instance_suffix="u_sys_face",
                                 fault_port="obs_fault", ready_port="seq_cfg_image_ready")
    with pytest.raises(ValueError, match="observer spec missing"):
        C.compose(TINY, table(), observer=dict(module="m"))


def test_hard_wrapper_ring_uses_delivered_reset():
    p = dict(partitions=[dict(name="a", type="A", origin_um=[0, 0]), dict(name="b", type="B", origin_um=[10, 0])],
             partition_types={"A": dict(module="a_mod", outline_um=[10, 10], buses=[]),
                              "B": dict(module="b_mod", outline_um=[10, 10], hard=True, buses=[])},
             ports=[dict(id="P", width=1, kind="data", src=dict(part="a", bus="x"), dst=dict(part="b", bus="y"))])
    tree = C._hard_tree([1, 5], [0, 5])
    col = dict(observer=None, parts={}, edges=[], types={
        "A": dict(mask=dict(active=False), tree=None, children=[], local_sources=[], bus_geometry={}),
        "B": dict(mask=dict(active=True, observer=False, up_seam=False), tree=tree, children=[],
                  collector_root_node="rst_root_n", bus_geometry={"y": dict(face="W", window_um=[4, 6])},
                  local_sources=[dict(name="y", ready="landing_ready_y", fault="landing_fault_y", tap=None,
                                      node=tree["leaf_node"], xy_um=[0, 5])])})
    t = dict(regions=[dict(tag="r0", box_um=[0, 0, 10, 10]), dict(tag="r1", box_um=[10, 0, 20, 10])],
             ports=[dict(port="P", width=1, src="a", dst="b", src_region="r0", dst_region="r1", lane="L")],
             collector=col)
    c = CL.Landings(p, t, require_geometry=False)
    body = ("module b_mod (\n input wire clk,\n input wire arst_n,\n input wire [1:0] y\n);\n"
            "    wire rst_n = arst_n;  // delivered reset to the native hard partition\n"
            "    ot_dp_st #(.W(1)) u_ft (.clk(clk), .rst_n(rst_n), .d(y[0:0]), .ea(y[1]), .q(q), .eq(eq));\nendmodule\n")
    v = c.type_rtl("B", body)
    assert ".rst_n(rst_n), .d(y), .q(cland_y)" in v
    assert "output wire cland_up_ready" in v and "u_cland_collect_rst_root_n" in v
    assert "ot_dp_rrelay" not in v                    # no invented reset tree in the hard wrapper
    assert c.reset_placements["B"]["y"]["hard_wrapper"] is True
