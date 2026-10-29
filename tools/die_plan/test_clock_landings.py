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
    # A terminal START-gated tap has no rr_t0 copy until a boot monitor needs it.
    terminal=a.replace("wire rr_t0;", "wire rst_n_t0;\n ot_dp_rgate u_rrl_0 (.clk(clk),.d(rst_root_n),.run(run),.q(rst_n_t0));")
    terminal_out=Landings(p,t).type_rtl("A",terminal)
    assert terminal_out.count("wire cland_reset_rst_n_t0;")==1
    assert terminal_out.count("ot_dp_rrelay u_cland_reset_rst_n_t0")==1
    assert ".rst_n(cland_reset_rst_n_t0)" in terminal_out
    boot=a.replace("wire rr_t0;", "wire rst_n_t0;\n ot_dp_rrelay u_rrl_0 (.clk(clk),.d(rst_root_n),.q(rst_n_t0));")
    boot_out=Landings(p,t).type_rtl("A",boot)
    assert "cland_reset_rst_n_t0" not in boot_out
    assert ".rst_n(rst_n_t0)" in boot_out
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


def test_ring_form_is_a_per_row_choice_and_default_is_unchanged():
    # MESO-COUNT-1 may swap in a count-aligned ring: module/params/extra pins come from the sidecar row
    b = "module b_mod (\n input wire clk,\n input wire [4:0] y // whole bundle\n);\n wire rst_n, rst_n_t0, rr_parent, run;\n ot_dp_rgate u_rrl_0 (.clk(clk), .d(rr_parent), .run(run), .q(rst_n_t0));\n wire [4:0] y_q;\n assign y_q = y;\nendmodule\n"
    p, t = vehicle()
    assert "ot_dp_clk_landing #(.W(5)) u_cland_y (" in Landings(p, t).type_rtl("B", b)
    p, t = vehicle()
    t["ports"][0].update(ring_module="ot_dp_clk_landing_ca", ring_params=dict(DEPTH=4, K=3), ring_ports=dict(t_rst_n="rr_parent"))
    c = Landings(p, t)
    bb = c.type_rtl("B", b)
    assert "ot_dp_clk_landing_ca #(.W(5), .DEPTH(4), .K(3)) u_cland_y (" in bb
    assert ".rst_n(cland_reset_y), .t_rst_n(rr_parent), .d(y)" in bb
    assert c.rows[0]["ring_offset"] == 3
    for bad in (dict(ring_module="ot_meso_fifo"), dict(ring_params=dict(W=9)), dict(ring_ports=dict(clk="x")),
                dict(ring_ports=dict(t_rst_n="a); evil(")),):
        p, t = vehicle(); t["ports"][0].update(bad)
        with pytest.raises(LandingError):
            Landings(p, t)


def test_replicas_of_one_type_must_agree_on_ring_form():
    p, t = vehicle()
    p["partitions"].append(dict(name="b2", type="B", origin_um=[20, 0]))
    p["ports"].append(dict(id="Q", width=4, kind="data", src=dict(part="a", bus="x"), dst=dict(part="b2", bus="y")))
    t["regions"].append(dict(tag="r2", box_um=[20, 0, 30, 10]))
    t["ports"].append(dict(port="Q", width=4, src="a", dst="b2", src_region="r0", dst_region="r2", lane="L",
                           ring_module="ot_dp_clk_landing_ca"))
    with pytest.raises(LandingError, match="TYPE_SPLIT"):
        Landings(p, t)


def region_vehicle():
    """DIE-HEAD-3: dataflow_vehicle + partition c in a's clock region r0 with NO landed port; its tree bus u feeds
    a.v inside the region, so its status rides same-region ctl pins (compose monitor="region")."""
    def pin(n, d):
        return dict(name=n, dir=d, width=1, face="E", window_um=[1, 2], layers=["M4"])
    p, t, a, b = dataflow_vehicle()
    t["regions"][0]["box_um"] = [0, 0, 10, 20]
    p["partitions"].append(dict(name="c", type="C", origin_um=[0, 10]))
    p["partition_types"]["C"] = dict(module="c_mod", outline_um=[10, 10], buses=[pin("cland_up_ready_u", "out"), pin("cland_up_fault_u", "out")])
    p["partition_types"]["A"]["buses"] += [pin("cland_dn_ready_v", "in"), pin("cland_dn_fault_v", "in")]
    p["ports"].append(dict(id="R", width=2, kind="data", src=dict(part="c", bus="u"), dst=dict(part="a", bus="v")))
    for k in ("ready", "fault"):
        p["ports"].append(dict(id=f"cland_mon_{k}__R", width=1, kind="ctl", src=dict(part="c", bus=f"cland_up_{k}_u"),
                               dst=dict(part="a", bus=f"cland_dn_{k}_v")))
    col = t["collector"]; col["monitor"] = "region"
    for m in col["types"].values():
        m["mask"].update(monitor="region", intra_inputs=[], intra_outputs=[])
    col["types"]["A"]["mask"]["intra_inputs"] = ["v"]
    col["types"]["C"] = dict(mask=dict(inputs=[], outputs=[], active=True, observer=False, monitor="region", tree_bus="u",
                                       intra_inputs=[], intra_outputs=["u"]),
                             tree=None, local_registered_depth=1, collector_root_xy=[5, 5], children=[], local_sources=[])
    col["parts"]["c"] = dict(parent="a", active=True)
    c = ("module c_mod (\n input wire clk,\n output wire [1:0] u\n);\n wire rst_n, rst_n_t0, rr_parent, run;\n"
         " ot_dp_rgate u_rrl_0 (.clk(clk), .d(rr_parent), .run(run), .q(rst_n_t0));\n assign u = 2'b0;\nendmodule\n")
    return p, t, a, b, c


def test_region_monitor_binds_same_region_status_pins():
    p, t, a, b, c = region_vehicle(); L = Landings(p, t)
    cc = L.type_rtl("C", c)
    assert "output wire cland_up_ready_u" in cc and "u_cland_rst_monitor (.clk(clk), .d(rr_parent), .q(cland_reset_monitor))" in cc
    assert ".clk(clk), .rst_n(cland_reset_monitor), .ready_i({1'b1}),\n        .fault_i({1'b0}), .ready_o(cland_up_ready_u)" in cc
    aa = L.type_rtl("A", a)
    assert "input wire cland_dn_ready_v" in aa
    assert ".ready_i({cland_ok_w, cland_dn_ready_v}),\n        .fault_i({cland_bad_w, cland_dn_fault_v}), .ready_o(cland_up_ready), .fault_o(cland_up_fault)" in aa
    L.type_rtl("B", b)
    top = ("module die_bound_top (rst_n, clk_core);\n    a_mod a (\n        .clk(clk_core)\n    );\n    b_mod b (\n        .clk(clk_core)\n    );\n"
           "    c_mod c (\n        .clk(clk_core)\n    );\nendmodule\n")
    tt = L.top_rtl(top)
    assert "wire cland_mon_c__u_ready, cland_mon_c__u_fault;" in tt
    assert ".cland_up_ready_u(cland_mon_c__u_ready)" in tt and ".cland_dn_fault_v(cland_mon_c__u_fault)" in tt
    assert "fclk_in_v" not in tt and "u_cland_v" not in aa          # same region: no ring, no forwarded clock
    assert L.manifest()["implemented"] is True and L.reset_placements["C"]["monitor"]["mode"] == "region"
    # composed form: the status ports live in clock.landing_network.edges, not in ports
    p, t, a, b, c = region_vehicle()
    mon = [x for x in p["ports"] if x["id"].startswith("cland_mon_")]
    p["ports"] = [x for x in p["ports"] if x not in mon]; p["clock"] = dict(landing_network=dict(edges=mon))
    assert Landings(p, t).intra_links == [("R", "c", "u", "a", "v")]


def test_region_monitor_fails_closed():
    p, t, a, b, c = region_vehicle(); t["collector"]["types"]["A"]["mask"]["intra_inputs"] = []
    with pytest.raises(LandingError, match="region monitor pins"):
        Landings(p, t)
    p, t, a, b, c = region_vehicle(); p["ports"] = [x for x in p["ports"] if x["id"] != "cland_mon_fault__R"]
    with pytest.raises(LandingError, match="ready/fault pair"):
        Landings(p, t)
    p, t, a, b, c = region_vehicle(); t["collector"]["monitor"] = "dataflow"   # plain dataflow keeps its strict rules
    with pytest.raises(LandingError):
        Landings(p, t)
def ca_vehicle(k=-2, depth=4, edge_fall=False):
    """MESO-INTEG-1 count-aligned form: the same a -> b crossing with the bind's K/DEPTH/latency and start tree."""
    p, t = vehicle()
    def pin(name, direction):
        return dict(name=name, dir=direction, width=1, face="E", window_um=[1, 2], layers=["M8"])
    p["partition_types"]["A"]["buses"].append(pin("cland_fstart_out_x", "out"))
    p["partition_types"]["B"]["buses"].append(pin("cland_fstart_in_y", "in"))
    t["count_aligned"] = dict(schema="opentallas.count_align_bind.v1", period_ps=833.0, root="r0", pad=0,
                              root_settle_cycles=40,
                              ports={"P": dict(K=k, depth=depth, sched_lat=2, tree=True)},
                              regions={"r0": dict(parent=None, tree_port=None, edge_fall=False, pad=0),
                                       "r1": dict(parent="r0", tree_port="P", edge_fall=edge_fall, pad=0)})
    return p, t


A_BODY = ("module a_mod (\n input wire clk,\n output wire [4:0] x\n);\n wire rr_parent, rst_n_t0;\n"
          " ot_dp_rrelay u_rrl_0 (.clk(clk), .d(rr_parent), .q(rst_n_t0));\n assign x = 0;\nendmodule\n")
B_BODY = ("module b_mod (\n input wire clk,\n input wire [4:0] y // whole bundle\n);\n wire rst_n, rst_n_t0, rr_parent, run;\n"
          " ot_dp_rgate u_rrl_0 (.clk(clk), .d(rr_parent), .run(run), .q(rst_n_t0));\n wire [4:0] y_q;\n assign y_q = y;\nendmodule\n")


def test_count_aligned_form_emits_ca_ring_origin_and_start_pins():
    p, t = ca_vehicle(edge_fall=True); c = Landings(p, t)
    aa = c.type_rtl("A", A_BODY); bb = c.type_rtl("B", B_BODY)
    assert "ot_dp_landing_root #(.SETTLE(40)) u_cland_origin (.clk(clk), .rst_raw_n(rst_n_t0), .start(cland_start));" in aa
    assert "assign cland_fstart_out_x = cland_start;" in aa and "output wire cland_fstart_out_x" in aa
    assert "ot_dp_clk_landing_ca #(.W(5), .DEPTH(4), .K(-2)) u_cland_y" in bb
    assert ".t_rst_n(cland_fstart_in_y), .clk(clk), .rst_n(cland_start), .d(y), .q(cland_y)" in bb
    assert ("ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(1)) u_cland_origin (" in bb
            and ".p_start(cland_fstart_in_y), .start(cland_start));" in bb and ".rst_raw_n(cland_reset_y)" in bb)
    assert ".ready(landing_ready_y), .fault(landing_fault_y));" in bb   # status still observed, never dropped
    assert "ot_dp_clk_landing #(" not in bb                            # old ring not emitted in this form
    top = ("module die_bound_top (rst_n, clk_core);\n input wire rst_n;\n input wire clk_core;\n    a_mod a (\n"
           "        .clk(clk_core)\n    );\n    b_mod b (\n        .clk(clk_core)\n    );\nendmodule\n")
    tt = c.top_rtl(top)
    assert ".cland_fstart_out_x(clock_landing_start_a__x)" in tt and ".cland_fstart_in_y(clock_landing_start_a__x)" in tt
    assert ".landing_fault_y(clock_landing_fault[0])" in tt
    m = c.manifest()
    assert m["lane_added_cycles"] == {"L": 2} and m["count_aligned"] is True
    assert requirements(p, t)["lane_added_cycles"] == {"L": 2}


def test_count_aligned_form_old_ring_stays_default():
    p, t = vehicle(); c = Landings(p, t)
    assert c.rows[0]["module"] == "ot_dp_clk_landing" and c.rows[0]["added_cycles"] == 3 and not c.ca


def test_count_aligned_form_requires_bind_pins_and_type_uniform_parameters():
    p, t = ca_vehicle(); p["partition_types"]["B"]["buses"].pop()
    with pytest.raises(LandingError, match="cland_fstart_in_y"):
        Landings(p, t)
    p, t = ca_vehicle(); t["count_aligned"]["ports"] = {}
    with pytest.raises(LandingError, match="no K/DEPTH/latency"):
        Landings(p, t)
    # two copies of type B whose crossings need different K -> TYPE_SPLIT, never a silent first-copy wrapper
    p, t = ca_vehicle()
    p["partitions"].append(dict(name="c", type="B", origin_um=[20, 0]))
    p["ports"].append(dict(id="Q", width=4, kind="data", src=dict(part="a", bus="x"), dst=dict(part="c", bus="y")))
    t["regions"].append(dict(tag="r2", box_um=[20, 0, 30, 10]))
    t["ports"].append(dict(port="Q", width=4, src="a", dst="c", src_region="r0", dst_region="r2", lane="L2"))
    t["count_aligned"]["ports"]["Q"] = dict(K=-1, depth=4, sched_lat=3, tree=True)
    t["count_aligned"]["regions"]["r2"] = dict(parent="r0", tree_port="Q", edge_fall=False, pad=0)
    with pytest.raises(LandingError, match="count-aligned landing TYPE_SPLIT"):
        Landings(p, t)


def test_count_aligned_network_prices_per_crossing():
    from clock_landings import network_lane_cycles
    p, t = vehicle()
    p["lanes"] = [dict(id="L", ports=["P"])]
    p["clock"] = dict(landing_network=dict(data_cycles_per_crossing="count_aligned", count_aligned_cycles={"P": 4},
                      edges=[dict(id="cland_clk__P", kind="clock", src=dict(part="a", bus="fclk_out_x"),
                                  dst=dict(part="b", bus="fclk_in_y"))]))
    assert network_lane_cycles(p) == {"L": 4}
    del p["clock"]["landing_network"]["count_aligned_cycles"]
    with pytest.raises(LandingError, match="count_aligned_cycles"):
        network_lane_cycles(p)


def ca_relay_vehicle(parts=True):
    """DIE-KV-3/CAORIGIN: region r1 holds b (origin, tree port P lands there) and c (relay, crossing Q a -> c)"""
    p, t = ca_vehicle()
    def pin(name, direction):
        return dict(name=name, dir=direction, width=1, face="E", window_um=[1, 2], layers=["M8"])
    p["partitions"].append(dict(name="c", type="C", origin_um=[10, 5]))
    p["partition_types"]["B"]["outline_um"] = [10, 5]
    p["partition_types"]["C"] = dict(module="c_mod", outline_um=[10, 5], buses=[pin("z", "in"), pin("fclk_in_z", "in"),
        pin("landing_ready_z", "out"), pin("landing_fault_z", "out"), pin("cland_fstart_in_z", "in"),
        pin("cland_rstart_in", "in")])
    p["partition_types"]["B"]["buses"].append(pin("cland_rstart_out", "out"))
    p["partition_types"]["A"]["buses"] += [pin("fclk_out_w", "out"), pin("cland_fstart_out_w", "out")]
    p["ports"].append(dict(id="Q", width=4, kind="data", src=dict(part="a", bus="w"), dst=dict(part="c", bus="z")))
    t["ports"].append(dict(port="Q", width=4, src="a", dst="c", src_region="r0", dst_region="r1", lane="LQ"))
    ca = t["count_aligned"]
    ca["ports"]["Q"] = dict(K=-1, depth=4, sched_lat=3, tree=False)
    ca["regions"]["r0"]["origin_part"] = "a"; ca["regions"]["r1"]["origin_part"] = "b"
    if parts:
        ca["relay_stages"] = 2
        ca["parts"] = dict(a=dict(region="r0", role="origin", src=None, stages=0),
                           b=dict(region="r1", role="origin", src=None, stages=0),
                           c=dict(region="r1", role="relay", src="b", stages=2))
    return p, t


C_BODY = ("module c_mod (\n input wire clk,\n input wire [4:0] z // whole bundle\n);\n wire rst_n, rst_n_t0, rr_parent, run;\n"
          " ot_dp_rgate u_rrl_0 (.clk(clk), .d(rr_parent), .run(run), .q(rst_n_t0));\n wire [4:0] z_q;\n assign z_q = z;\nendmodule\n")


def test_count_aligned_relay_emits_one_origin_and_timed_start_relay():
    p, t = ca_relay_vehicle(); c = Landings(p, t)
    bb = c.type_rtl("B", B_BODY); cc = c.type_rtl("C", C_BODY)
    assert "u_cland_origin" in bb and "output wire cland_rstart_out" in bb
    assert "ot_dp_landing_relay u_cland_rstart_tx (.clk(clk), .rst_raw_n(cland_reset_y), .d(cland_start), .q(cland_rstart_out));" in bb
    assert "u_cland_origin" not in cc and "input wire cland_rstart_in" in cc
    assert "ot_dp_landing_relay u_cland_rstart_rx (.clk(clk), .rst_raw_n(cland_reset_z), .d(cland_rstart_in), .q(cland_start));" in cc
    assert "ot_dp_clk_landing_ca #(.W(5), .DEPTH(4), .K(-1)) u_cland_z" in cc and ".rst_n(cland_start)" in cc
    top = ("module die_bound_top (rst_n, clk_core);\n input wire rst_n;\n input wire clk_core;\n    a_mod a (\n"
           "        .clk(clk_core)\n    );\n    b_mod b (\n        .clk(clk_core)\n    );\n    c_mod c (\n"
           "        .clk(clk_core)\n    );\nendmodule\n")
    tt = c.top_rtl(top)
    assert "wire clock_landing_rstart_b;" in tt
    assert ".cland_rstart_out(clock_landing_rstart_b)" in tt and ".cland_rstart_in(clock_landing_rstart_b)" in tt
    assert c.ca_part_role["c"]["role"] == "relay" and c.ca_part_role["b"]["relay_tx"]


def test_count_aligned_multi_partition_region_without_relay_roles_fails_closed():
    p, t = ca_relay_vehicle(parts=False)
    with pytest.raises(LandingError, match="one partition per region"):
        Landings(p, t)
    p, t = ca_relay_vehicle(); p["partition_types"]["C"]["buses"].pop()
    with pytest.raises(LandingError, match="cland_rstart_in"):
        Landings(p, t)
    p, t = ca_relay_vehicle(); t["count_aligned"]["parts"]["c"]["stages"] = 3
    with pytest.raises(LandingError, match="relay role"):
        Landings(p, t)


def test_plan_relay_pins_and_registered_ctl_ports():
    import clock_landing_plan as CP
    p, t = ca_relay_vehicle()
    assert (CP._ca_relay(t, "a"), CP._ca_relay(t, "b"), CP._ca_relay(t, "c")) == (None, "tx", "rx")
    raw = dict(ports=[]); CP._ca_relay_ports(raw, t)
    assert raw["ports"] == [dict(id="cland_relay__c", src=dict(part="b", bus="cland_rstart_out"),
                                 dst=dict(part="c", bus="cland_rstart_in"), width=1, kind="ctl", epoch=False)]
    ty = dict(outline_um=[10, 5], buses=[dict(name="y", face="W", window_um=[1, 2])])
    CP._ca_relay_pins(ty, t, "b", {"y": dict(port="P")}, set())
    assert ty["buses"][-1]["name"] == "cland_rstart_out" and ty["buses"][-1]["kind"] == "ctl"
    p, t = ca_relay_vehicle(parts=False)
    raw = dict(ports=[]); CP._ca_relay_ports(raw, t)
    assert raw["ports"] == [] and CP._ca_relay(t, "b") is None        # no bind roles: nothing added (old form)


def test_receiver_uses_collector_geometry_when_bus_is_declaration_only():
    p, t, a, b = dataflow_vehicle()
    reference = Landings(p, t).type_rtl("B", b)
    pin = next(v for v in p["partition_types"]["B"]["buses"] if v["name"] == "y")
    saved = dict(pin)
    pin.pop("face"); pin.pop("window_um")
    t["collector"]["types"]["B"]["bus_geometry"] = {"y": saved}
    assert Landings(p, t).type_rtl("B", b) == reference
    del t["collector"]["types"]["B"]["bus_geometry"]
    with pytest.raises(LandingError, match="receiver face geometry not found"):
        Landings(p, t).type_rtl("B", b)


def test_native_top_regions_include_early_core_clock_inputs():
    p, t, _a, _b = dataflow_vehicle()
    c = Landings(p, t)
    top = ("module die_top (\n    input  wire clk,\n    input wire rst_n\n);\n"
           "    a_mod a (\n        .clk(clk),\n        .clk_t3(clk),\n        .clk_c0(clk)\n    );\n"
           "    b_mod b (\n        .clk(clk),\n        .clk_c4(clk)\n    );\nendmodule\n")
    out = c.top_rtl(top)
    assert ".clk_c0(clk_region_r0)" in out
    assert ".clk_c4(clk_region_r1)" in out
    assert ".clk_t3(clk_region_r0)" in out
    assert "input  wire clk," not in out
    assert "(clk)" not in out
    # A clock-looking name outside the generated grid/core families stays rejected.
    with pytest.raises(LandingError, match="still drives a partition pin"):
        Landings(p, t).top_rtl(top.replace(".clk_c0(clk)", ".clk_phy(clk)"))


def test_forwarded_clock_rtl_source_follows_landing_contract():
    """DIE-HEAD-9 FACE (c): fclk_out_* is assigned from the contract's source_clock_port (default clk)."""
    p, t = vehicle()
    p["partition_types"]["A"]["clock"] = dict(landing_contract=dict(pins=[dict(
        name="fclk_out_x", dir="out", kind="clock", layer="M8", xy_um=[9.0, 1.5], epoch=False,
        source_clock_port="clk_t3")]))
    c = Landings(p, t)
    a = "module a_mod (\n input wire clk,\n input wire clk_t3,\n output wire [4:0] x\n);\n assign x = 0;\nendmodule\n"
    assert "assign fclk_out_x = clk_t3;" in c.type_rtl("A", a)
    with pytest.raises(LandingError, match="source_clock_port clk_t3"):
        c.type_rtl("A", a.replace(" input wire clk_t3,\n", ""))


def test_start_relay_without_landed_input_copies_raw_tap_before_start_gate():
    c=Landings.__new__(Landings);c.reset_placements={}
    extra=[]
    body="ot_dp_rgate u_rrl_4 (.clk(clk), .d(rst_rl_3), .run(run), .q(rst_n_t0));"
    rtl="\n".join(c._origin_rtl('T', {'role':('relay','origin',2)}, {}, body, extra))
    assert "ot_dp_rrelay u_cland_origin_rst (.clk(clk), .d(rst_rl_3), .q(cland_origin_reset));" in rtl
    assert ".rst_raw_n(cland_origin_reset)" in rtl
    assert ".rst_raw_n(rst_n_t0)" not in rtl
    assert extra==['    input wire cland_rstart_in']


def test_start_relay_without_landed_input_reuses_an_ungated_tap():
    c=Landings.__new__(Landings);c.reset_placements={}
    body="ot_dp_rrelay u_rrl_4 (.clk(clk), .d(rst_rl_3), .q(rst_n_t0));"
    rtl="\n".join(c._origin_rtl('T', {'role':('relay','origin',2)}, {}, body, []))
    assert ".rst_raw_n(rst_n_t0)" in rtl
    assert "u_cland_origin_rst" not in rtl


def test_root_and_start_pin_share_one_raw_relay():
    from clock_landings import START_PIN_IN
    c=Landings.__new__(Landings);c.reset_placements={};c.tstart=None
    body="ot_dp_rgate u_rrl_4 (.clk(clk), .d(rst_rl_3), .run(run), .q(rst_n_t0));"
    rtl="\n".join(c._origin_rtl('T', {'role':('strap',(START_PIN_IN,),1,64,True)}, {}, body, []))
    assert rtl.count('ot_dp_rrelay u_cland_origin_rst')==1


def test_independent_start_count_frames_preserve_physical_clock_groups():
    p,t=ca_relay_vehicle()
    ca=t['count_aligned']
    ca['regions']['r1c']=dict(ca['regions']['r1'],origin_part='c',tree_port='Q')
    ca['parts']['c']=dict(region='r1c',role='origin',src=None,stages=0)
    ca['ports']['Q']['tree']=True
    ca['frame_clock_regions']={'r0':'r0','r1':'r1','r1c':'r1'}
    c=Landings(p,t,require_geometry=False)
    assert c.region['b']==c.region['c']=='r1'
    assert c.ca_part_role['c']['role']=='child'
    assert not c.ca_type['B']['relay_tx']
    assert not c.ca_type['C']['relay_tx']
    ca['frame_clock_regions']['r1c']='r0'
    with pytest.raises(LandingError,match='count frame clock mismatch'):
        Landings(p,t,require_geometry=False)


def test_explicit_origin_start_face_role_matches_emitted_instance():
    from clock_landings import START_PIN_IN
    c=Landings.__new__(Landings);c.ca=True;c.dataflow=False
    c.by_type={'T':{'inputs':[]}}
    c.ca_type={'T':{'role':('strap',(START_PIN_IN,),1,74,False)}}
    assert c.land_slots('T')['buses']=={START_PIN_IN:{'form':'origin_start','origin':'u_cland_origin'}}
    c.ca_type['T']['role']=('strap',('d',START_PIN_IN),1,74,False)
    assert c.land_slots('T')['buses'][START_PIN_IN]['origin']=='u_cland_origin_t1'
    c.ca_type['T']['role']=('root',74)
    assert c.land_slots('T') is None
