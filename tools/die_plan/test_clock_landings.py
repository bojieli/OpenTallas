import copy
import pytest
from clock_landings import Landings, LandingError, requirements


def vehicle():
    def pin(name, direction):
        return dict(name=name, dir=direction, width=1, face="E", window_um=[1, 2], layers=["M8"])
    p = dict(partitions=[dict(name="a", type="A", origin_um=[0, 0]),
                         dict(name="b", type="B", origin_um=[10, 0])],
             partition_types={"A": dict(module="a_mod", outline_um=[10, 10], buses=[pin("fclk_out_x", "out")]),
                              "B": dict(module="b_mod", outline_um=[10, 10], buses=[pin("y", "in"), pin("fclk_in_y", "in"),
                                  pin("landing_ready_y", "out"), pin("landing_fault_y", "out")])},
             ports=[dict(id="P", width=4, kind="data", src=dict(part="a", bus="x"), dst=dict(part="b", bus="y"))])
    t = dict(regions=[dict(tag="r0", box_um=[0, 0, 10, 10]), dict(tag="r1", box_um=[10, 0, 20, 10])],
             ports=[dict(port="P", width=4, src="a", dst="b", src_region="r0", dst_region="r1", lane="L")])
    return p, t


def test_real_receiver_and_forwarded_clock_are_emitted():
    p, t = vehicle(); c = Landings(p, t)
    a = "module a_mod (\n input wire clk,\n output wire [4:0] x\n);\n assign x = 0;\nendmodule\n"
    b = "module b_mod (\n input wire clk,\n input wire [4:0] y // whole bundle\n);\n wire rst_n, rst_n_t0, rr_parent, run;\n ot_dp_rgate u_rrl_0 (.clk(clk), .d(rr_parent), .run(run), .q(rst_n_t0));\n wire [4:0] y_q;\n assign y_q = y;\nendmodule\n"
    aa = c.type_rtl("A", a); bb = c.type_rtl("B", b)
    assert "assign fclk_out_x = clk;" in aa
    assert "ot_dp_clk_landing #(.W(5)) u_cland_y" in bb
    assert ".d(y), .q(cland_y)" in bb
    assert "assign y_q = cland_y;" in bb
    assert "input wire [4:0] y," in bb
    assert ".rst_n(cland_reset_y)" in bb
    assert "ot_dp_rrelay u_cland_rst_y (.clk(clk), .d(rr_parent), .q(cland_reset_y))" in bb
    top = "module die_bound_top (rst_n, clk_core);\n input wire rst_n;\n input wire clk_core;\n    a_mod a (\n        .clk(clk_core)\n    );\n    b_mod b (\n        .clk(clk_core)\n    );\nendmodule\n"
    tt = c.top_rtl(top)
    assert ".fclk_in_y(clock_landing_fwd_a__x)" in tt
    assert ".fclk_out_x(clock_landing_fwd_a__x)" in tt
    assert ".clk(clk_region_r1)" in tt
    assert ".landing_fault_y(clock_landing_fault[0])" in tt
    assert c.manifest()["implemented"] is True
    assert c.manifest()["physical_qualified"] is False
    assert c.manifest()["lane_added_cycles"] == {"L": 3}


def test_missing_physical_pin_rejects_metadata_only_landing():
    p, t = vehicle(); p["partition_types"]["B"]["buses"].pop()
    with pytest.raises(LandingError, match="declare placed scalar out pin landing_fault_y"):
        Landings(p, t)


def test_repeated_type_with_different_masks_requires_explicit_split():
    p, t = vehicle(); p["partitions"].append(dict(name="b2", type="B", origin_um=[10, 0]))
    with pytest.raises(LandingError, match="TYPE_SPLIT"):
        Landings(p, t)
    r = requirements(p, t)
    assert r["type_count_after"] == 3
    assert len(r["split_types"]["B"]) == 2


def test_stale_width_or_region_cannot_emit():
    p, t = vehicle(); t["ports"][0]["width"] = 5
    with pytest.raises(LandingError, match="stale"):
        Landings(p, t)
    p, t = vehicle(); t["ports"][0]["dst_region"] = "r2"
    with pytest.raises(LandingError, match="region conflict"):
        Landings(p, t)


def test_inventory_does_not_claim_hardware_or_physical_pass():
    p, t = vehicle(); c = Landings(p, t)
    assert c.manifest()["implemented"] is False
    r = requirements(p, t)
    assert r["required_new_scalar_pins"] == 4
    assert r["added_live_data_storage_flops"] == 25


def test_registered_monitor_replaces_long_die_status_vectors():
    p,t=vehicle()
    def pin(n,d):return dict(name=n,dir=d,width=1,face="E",window_um=[1,2],layers=["M4"])
    for ty in p["partition_types"].values():
        ty["buses"] += [pin("cland_up_ready","out"),pin("cland_up_fault","out")]
    p["partition_types"]["A"]["buses"] += [pin("cland_dn_ready_0","in"),pin("cland_dn_fault_0","in"),pin("fclk_in_cland_dn_0","in")]
    p["partition_types"]["B"]["buses"].append(pin("fclk_out_cland_up","out"))
    tree=dict(root=[1,1],n_clock_taps=1,relays=[dict(q="rst_n_t0",d="rst_root_n",xy=[2,1])])
    t["collector"]=dict(root="a",parts={"a":dict(parent=None,active=True),"b":dict(parent="a",active=True)},
        edges=[dict(src="b",dst="a",dst_index=0,seam=True)],types={
            "A":dict(mask=dict(active=True,up_seam=False),tree=tree,local_sources=[],children=[
                dict(index=0,tap=0,seam=True,ready="cland_dn_ready_0",fault="cland_dn_fault_0",xy_um=[2,1])]),
            "B":dict(mask=dict(active=True,up_seam=True),tree=tree,children=[],local_sources=[
                dict(name="y",tap=0,ready="landing_ready_y",fault="landing_fault_y",xy_um=[10,1.5])])})
    c=Landings(p,t)
    a="module a_mod (\n input wire clk,\n output wire [4:0] x\n);\n wire rst_root_n; wire rr_t0;\n assign x=0;\nendmodule\n"
    b="module b_mod (\n input wire clk,\n input wire [4:0] y\n);\n wire rst_root_n, rst_n_t0;\n ot_dp_rgate u_rrl_0 (.clk(clk),.d(rst_root_n),.run(run),.q(rst_n_t0));\n wire [4:0] y_q; assign y_q=y;\nendmodule\n"
    aa=c.type_rtl("A",a);bb=c.type_rtl("B",b)
    assert "ot_dp_clk_landing #(.W(2)) u_cland_monitor_0" in aa
    assert "ot_dp_landing_collect" in aa
    assert "output wire landing_fault_y" not in bb
    assert "wire landing_ready_y, landing_fault_y;" in bb
    top="module die_bound_top (rst_n, clk_core);\n    a_mod a (\n        .clk(clk_core)\n    );\n    b_mod b (\n        .clk(clk_core)\n    );\nendmodule\n"
    out=c.top_rtl(top)
    assert "output wire clock_landing_ready;" in out
    assert "output wire [0:0] clock_landing_ready;" not in out
    assert ".cland_dn_ready_0(cland_ready_b)" in out
    assert ".cland_up_ready(clock_landing_ready)" in out
    renamed=top.replace("a_mod a (","a_mod__A a (").replace("b_mod b (","b_mod__B b (")
    assert ".cland_dn_ready_0(cland_ready_b)" in c.top_rtl(renamed,{"A":"a_mod__A","B":"b_mod__B"})
    with pytest.raises(LandingError):c.top_rtl(renamed,{"A":"a_mod__A"})


def test_actual_observer_port_transform():
    from clock_landings import gate_observer, LandingError
    spec=dict(module="qfd_sys_face_lctx3_wrapped",instance_suffix="u_sys_face",fault_port="obs_fault",ready_port="seq_cfg_image_ready")
    text="    qfd_sys_face_lctx3_wrapped native_u_sys_face (\n        .obs_fault((a | b)),\n        .seq_cfg_image_ready(c[0])\n    );\n"
    out=gate_observer(text,spec)
    assert ".obs_fault((((a | b)) | cland_up_fault))" in out
    assert ".seq_cfg_image_ready(((c[0]) & cland_up_ready))" in out
    with pytest.raises(LandingError):gate_observer(text.replace(".obs_fault", ".wrong"),spec)


def test_native_observer_uses_exact_emitted_identity(monkeypatch):
    import sys
    from types import SimpleNamespace as N
    from clock_landings import LandingError
    monkeypatch.setitem(sys.modules,'bind',N(short_id=lambda s,n:s))
    c=Landings.__new__(Landings)
    c.collector=dict(observer=dict(part='glue',module='qfd_sys_face_lctx3_wrapped',instance_suffix='u_sys_face',fault_port='obs_fault',ready_port='seq_cfg_image_ready'))
    leaf=N(path='sys_face',module='qfd_sys_face_lctx3_wrapped',ports=dict(obs_fault=[1],seq_cfg_image_ready=[2]))
    b=N(members=dict(glue=[0]),F=N(cells=[leaf]),G=N(dirs=[dict(obs_fault='input',seq_cfg_image_ready='input')]),rel_of=lambda ci:'sys_face')
    c.validate_observer(b)
    assert c.observer_source['path']=='sys_face'
    assert c.observer_source['emitted_instance']=='u_sys_face'
    b.rel_of=lambda ci:'wrong_face'
    with pytest.raises(LandingError):c.validate_observer(b)


def dataflow_vehicle(observer_open=False):
    """a -> b data crossing, b -> a return crossing; a is the observer (glue), b's tree bus is z."""
    def pin(n, d):
        return dict(name=n, dir=d, width=1, face="E", window_um=[1, 2], layers=["M4"])
    p, t = vehicle()
    p["partition_types"]["A"]["buses"] = [pin("fclk_out_x", "out"), pin("cland_up_ready_x", "out"), pin("cland_up_fault_x", "out"),
                                          pin("w", "in"), pin("fclk_in_w", "in"), pin("cland_dn_ready_w", "in"), pin("cland_dn_fault_w", "in")]
    p["partition_types"]["B"]["buses"] = [pin("y", "in"), pin("fclk_in_y", "in"), pin("cland_dn_ready_y", "in"), pin("cland_dn_fault_y", "in"),
                                          pin("fclk_out_z", "out"), pin("cland_up_ready_z", "out"), pin("cland_up_fault_z", "out")]
    p["ports"].append(dict(id="Q", width=3, kind="data", src=dict(part="b", bus="z"), dst=dict(part="a", bus="w")))
    t["ports"].append(dict(port="Q", width=3, src="b", dst="a", src_region="r1", dst_region="r0", lane="M"))
    obs = dict(part="a", module="OPEN" if observer_open else "obs_mod", instance_suffix="u_obs", fault_port="f_in", ready_port="r_in")
    t["collector"] = dict(root="a", monitor="dataflow", observer=obs,
        parts={"a": dict(parent=None, active=True), "b": dict(parent="a", active=True)},
        types={"A": dict(mask=dict(inputs=["w"], outputs=["x"], active=True, observer=True, monitor="dataflow", tree_bus=None),
                         tree=None, local_registered_depth=1, collector_root_xy=[5, 5], children=[], local_sources=[]),
               "B": dict(mask=dict(inputs=["y"], outputs=["z"], active=True, observer=False, monitor="dataflow", tree_bus="z"),
                         tree=None, local_registered_depth=3, collector_root_xy=[10, 1.5], children=[], local_sources=[])},
        edges=[], tree_bus={"A": None, "B": "z"})
    a = ("module a_mod (\n input wire clk,\n input wire [3:0] w,\n output wire [4:0] x\n);\n wire rst_n, rst_n_t0, rr_parent, run;\n"
         " ot_dp_rgate u_rrl_0 (.clk(clk), .d(rr_parent), .run(run), .q(rst_n_t0));\n assign x = {1'b0, w};\n"
         "    obs_mod native_u_obs (\n        .f_in(1'b0),\n        .r_in(run)\n    );\nendmodule\n")
    b = ("module b_mod (\n input wire clk,\n input wire [4:0] y,\n output wire [3:0] z\n);\n wire rst_n, rst_n_t0, rr_parent, run;\n"
         " ot_dp_rgate u_rrl_0 (.clk(clk), .d(rr_parent), .run(run), .q(rst_n_t0));\n assign z = y[3:0];\nendmodule\n")
    return p, t, a, b


def test_dataflow_monitor_rides_the_data_ring():
    p, t, a, b = dataflow_vehicle(); c = Landings(p, t)
    bb = c.type_rtl("B", b)
    # ring W+2 = data+epoch (5) + {fault, ready}
    assert "ot_dp_clk_landing #(.W(7)) u_cland_y (" in bb
    assert ".d({cland_dn_fault_y, cland_dn_ready_y, y}), .q(cland_ring_y)" in bb
    assert "assign cland_y = cland_ring_y[4:0];" in bb
    assert "assign z = cland_y[3:0];" in bb
    assert "wire cland_ok_y = cland_ring_y[5] && landing_ready_y && !landing_fault_y;" in bb
    assert "wire cland_bad_y = landing_fault_y || (landing_ready_y && cland_ring_y[6]);" in bb
    # depth 3 on the tree bus: two shared stages + the dedicated output register
    assert "ot_dp_landing_collect #(.N(1)) u_cland_agg_1" in bb
    assert ".ready_i({cland_ok_y})" in bb
    assert "u_cland_agg_2" in bb and "u_cland_agg_3" not in bb
    assert ".ready_i({cland_agg_r2}),\n        .fault_i({cland_agg_f2}), .ready_o(cland_up_ready_z), .fault_o(cland_up_fault_z)" in bb
    assert "output wire cland_up_ready_z" in bb and "input wire cland_dn_ready_y" in bb
    assert "output wire landing_ready_y" not in bb
    m = c.reset_placements["B"]["monitor"]
    assert m["depth"] == 3 and m["outputs"] == [dict(bus="z", carries="aggregate", registered_depth=3)]
    assert m["data_cycles_added"] == 0


def test_dataflow_observer_gets_registered_aggregate_and_local_outputs():
    p, t, a, b = dataflow_vehicle(); c = Landings(p, t)
    aa = c.type_rtl("A", a)
    # x is not a tree bus: it carries the LOCAL status through its own dedicated register
    assert ".ready_i({landing_ready_w}),\n        .fault_i({landing_fault_w}), .ready_o(cland_up_ready_x)" in aa
    assert ".ready_i({cland_ok_w}),\n        .fault_i({cland_bad_w}), .ready_o(cland_up_ready), .fault_o(cland_up_fault)" in aa
    assert ".f_in(((1'b0) | cland_up_fault))" in aa
    assert ".r_in(((run) & cland_up_ready))" in aa
    assert "output wire cland_up_ready," not in aa


def test_dataflow_top_wires_status_beside_each_crossing():
    p, t, a, b = dataflow_vehicle(); c = Landings(p, t)
    c.type_rtl("A", a); c.type_rtl("B", b)
    top = "module die_bound_top (rst_n, clk_core);\n    a_mod a (\n        .clk(clk_core)\n    );\n    b_mod b (\n        .clk(clk_core)\n    );\nendmodule\n"
    tt = c.top_rtl(top)
    assert "wire cland_mon_a__x_ready, cland_mon_a__x_fault;" in tt
    assert ".cland_up_ready_x(cland_mon_a__x_ready)" in tt
    assert ".cland_dn_ready_y(cland_mon_a__x_ready)" in tt
    assert ".cland_dn_fault_w(cland_mon_b__z_fault)" in tt
    assert "clock_landing_ready" not in tt          # no die-top status IO
    assert c.manifest()["implemented"] is True


def test_dataflow_requires_declared_monitor_pins_and_real_observer():
    p, t, a, b = dataflow_vehicle()
    p["partition_types"]["B"]["buses"] = [x for x in p["partition_types"]["B"]["buses"] if x["name"] != "cland_up_fault_z"]
    with pytest.raises(LandingError, match="cland_up_fault_z"):
        Landings(p, t)
    p, t, a, b = dataflow_vehicle(observer_open=True); c = Landings(p, t)
    c.type_rtl("B", b)
    with pytest.raises(LandingError, match="OPEN"):
        c.type_rtl("A", a)
    p, t, a, b = dataflow_vehicle(); t["collector"]["types"]["B"]["mask"]["tree_bus"] = "nope"
    with pytest.raises(LandingError, match="tree bus"):
        Landings(p, t)


def test_dataflow_landing_place_emits_bands_and_status_points_only():
    from types import SimpleNamespace as N
    import landing_place as LP
    c = dict(monitor="dataflow", collector_tree=None, collector_root_node="cland_up_ready_z",
             bands={"y": dict(instance="u_cland_y", rect_um=[1, 2, 3, 4])},
             collector_local_sources=[dict(name="y", ready="landing_ready_y", fault="landing_fault_y", xy_um=[9, 1])],
             pins=[dict(name="cland_up_ready_z", dir="out", xy_um=[9.0, 1.5]), dict(name="cland_up_fault_z", dir="out", xy_um=[9.0, 2.0]),
                   dict(name="cland_dn_ready_y", dir="in", xy_um=[9.0, 3.0])])
    out = LP.tcl(N(types={"B": dict(clock=dict(landing_contract=c))}), "B")
    head = out.split("# Generated caller")[0]
    assert "{u_cland_y {1.00000 2.00000 3.00000 4.00000} ring:y}" in head
    assert "{cland_up_ready_z 9.00000 1.50000}" in head and "{cland_up_fault_z 9.00000 2.00000}" in head
    assert "cland_dn_ready_y" not in head and "collector:" not in head and "u_cland_rst_" not in head
