import pytest
from landing_collector import build_local


def tree():
    return dict(root=[0,0],relays=[
        dict(q="rst_n_t0",d="rst_root_n",xy=[100,0]),
        dict(q="rst_n_t1",d="rst_n_t0",xy=[200,0]),
        dict(q="rst_n_t2",d="rst_root_n",xy=[0,300])])


def test_reverse_tree_prunes_unused_child_and_publishes_real_depth():
    t=tree();s=[dict(name="ring",tap=1,ready="r",fault="f",xy_um=[200,0])]
    body="wire rst_root_n;\nwire rr_t0;\n"
    r=build_local(t,s,body)
    assert r["depth"]==3
    assert r["max_hop_um"]==100
    assert all("rst_n_t2" not in x for x in r["rtl"])
    assert sum(i["module"]=="ot_dp_landing_collect" for i in r["instances"])==3
    assert any(i["role"]=="raw pre-START reset copy" for i in r["instances"] if "role" in i)
    assert ".ready_o(cland_up_ready)" in "\n".join(r["rtl"])
    assert all("1'b" not in x for x in r["rtl"])


def test_no_active_source_emits_no_status_pin_tie():
    assert build_local(tree(),[],"")["rtl"]==[]


def test_long_reversed_edge_is_reported_not_blocking(capsys):
    # LIMIT-BIND-1 11-14 (OWNER: remove the conservative limits): the 405-um collector reach is info only
    t=tree();t["relays"][1]["xy"]=[600,0]
    s=[dict(name="ring",tap=1,ready="r",fault="f",xy_um=[600,0])]
    build_local(t,s,"wire rr_t0;")
    assert "COLLECTOR-REACH-INFO" in capsys.readouterr().err


def test_real_two_inputs_remain_two_inputs():
    s=[dict(name="a",tap=0,ready="ra",fault="fa"),dict(name="b",tap=0,ready="rb",fault="fb")]
    r=build_local(tree(),s,"wire rr_t0;")
    assert any(i.get("active_inputs")==2 for i in r["instances"])
    assert any("{ra, rb}" in line for line in r["rtl"])


def test_raw_reset_requires_exact_relay_and_raw_parent():
    import pytest
    from landing_collector import raw_reset
    tree=dict(relays=[dict(q="rst_n_t2", d="rst_n_t1", xy=[20,30])])
    with pytest.raises(ValueError,match="relay absent"):
        raw_reset(tree,"rst_n_t99","wire rst_root_n;")
    with pytest.raises(ValueError,match="raw reset parent rr_t1 absent"):
        raw_reset(tree,"rst_n_t2","wire rst_root_n;")
    name,rtl,inst=raw_reset(tree,"rst_n_t2","wire rr_t1;")
    assert name=="cland_reset_rst_n_t2"
    assert ".d(rr_t1)" in rtl[-1]
    assert inst[0]["xy_um"]==[20,30]
    assert raw_reset(tree,"rst_n_t2","wire rr_t1;\n"+"\n".join(rtl))==(name,[],[])


def test_raw_reset_never_reuses_a_registered_reset_out_face_flop():
    """DIE-KV-32 10-29 face_guard 'shared' (KV hub_Ei rst_o_0 = rr_t21 with 5 monitor/collector loads): a raw tap
    that is the wrapper's registered reset OUT (reset_tree `assign rst_o_k = rr_tN`) stays that port's face flop; a
    pre-START consumer gets its own copy at the same parent/xy (cycle-equal), reused by later consumers."""
    from landing_collector import raw_reset
    t = dict(root=[0, 0], relays=[dict(q="rst_n_t0", d="rst_root_n", xy=[100, 0]),
                                  dict(q="rst_n_t1", d="rst_rl_5", xy=[200, 0])])
    plain = "wire rst_root_n;\nwire rst_rl_5;\nwire rr_t1;\n"
    assert raw_reset(t, "rst_n_t1", plain) == ("rr_t1", [], [])            # not a face: reuse unchanged
    face = plain + "assign rst_o_0 = rr_t1;  // registered reset out (wavefront)\n"
    name, rtl, inst = raw_reset(t, "rst_n_t1", face)
    assert name == "cland_reset_rst_n_t1" and inst[0]["xy_um"] == [200, 0]
    assert rtl == ["    wire cland_reset_rst_n_t1;",
                   "    ot_dp_rrelay u_cland_reset_rst_n_t1 (.clk(clk), .d(rst_rl_5), .q(cland_reset_rst_n_t1));"]
    assert raw_reset(t, "rst_n_t1", face + "\n".join(rtl)) == (name, [], [])  # second consumer shares the copy


def test_raw_reset_copies_an_undeclared_wire_relay_parent_chain():
    from landing_collector import raw_reset
    tree=dict(relays=[dict(q="rst_rl_1", d="rst_n_t0", xy=[1,2]), dict(q="rst_rl_2", d="rst_rl_1", xy=[3,4]),
                      dict(q="rst_rl_3", d="rst_rl_2", xy=[5,6])])
    name,rtl,inst=raw_reset(tree,"rst_rl_3","wire rr_t0;\nwire rst_rl_1;")
    assert name=="cland_reset_rst_rl_3"
    assert [i["xy_um"] for i in inst]==[[3,4],[5,6]]
    text="\n".join(rtl)
    assert ".d(rst_rl_1), .q(cland_reset_rst_rl_2)" in text
    assert ".d(cland_reset_rst_rl_2), .q(cland_reset_rst_rl_3)" in text
    body="wire rr_t0;\nwire rst_rl_1;\n"+text
    assert raw_reset(tree,"rst_rl_3",body)==(name,[],[])
    assert raw_reset(tree,"rst_rl_2",body)==("cland_reset_rst_rl_2",[],[])


def _stale_vehicle():
    """QC-TYPES-10/CLAND 11-08 (slw_fe_v1 u_cland_reset_rst_n_t29 .d(rst_rl_45), 946 um): the collector tree and the
    bound body share relay NAMES but not sites.  Collector tree: root (332,600) -> rst_rl_45 (332,951) -> rst_n_t29 (332,1322).
    Bound body: rst_rl_45 is a pad at (592.4,56.2), rst_n_t29 a gate at (17.8,427.7)."""
    tree = dict(root=[332, 600], relays=[dict(q="rst_rl_45", d="rst_root_n", xy=[332, 951], depth=1),
                                     dict(q="rst_n_t29", d="rst_rl_45", xy=[332, 1322], depth=2)])
    body = ("wire rst_root_n;\nwire rst_rl_45;\nwire rst_n_t29;\n"
            "    ot_dp_rrelay u_rrl_45 (.clk(clk), .d(rst_rl_44), .q(rst_rl_45));  // raw pad tap 7 depth 1 @ (592.4, 56.2)\n"
            "    ot_dp_rgate u_rrl_134 (.clk(clk), .d(rst_rl_133), .run(rn), .q(rst_n_t29));  "
            "// gated tap tap 29 depth 2 @ (17.8, 427.7)\n")
    return tree, body


def test_raw_reset_never_reuses_a_same_named_relay_of_another_tree():
    from landing_collector import raw_reset
    tree, body = _stale_vehicle()
    name, rtl, inst = raw_reset(tree, "rst_n_t29", body)
    text = "\n".join(rtl)
    assert name == "cland_reset_rst_n_t29"
    assert ".d(rst_rl_45)" not in text                       # the old far wiring (946 um)
    assert "u_cland_reset_rst_rl_45 (.clk(clk), .d(rst_root_n), .q(cland_reset_rst_rl_45))" in text
    assert "u_cland_reset_rst_n_t29 (.clk(clk), .d(cland_reset_rst_rl_45), .q(cland_reset_rst_n_t29))" in text
    assert [i["xy_um"] for i in inst] == [[332, 951], [332, 1322]]   # every copy at its collector-tree site
    # a collector on the relay node takes the copy too, never the far bound rst_rl_45
    assert raw_reset(tree, "rst_rl_45", body + text) == ("cland_reset_rst_rl_45", [], [])


def test_raw_reset_reuses_the_bound_relay_when_it_is_the_tree_relay():
    """Agreeing trees: byte-identical to the old rule (reuse by name)."""
    from landing_collector import raw_reset
    tree, _ = _stale_vehicle()
    body = ("wire rst_root_n;\nwire rst_rl_45;\n"
            "    ot_dp_rrelay u_rrl_45 (.clk(clk), .d(rst_root_n), .q(rst_rl_45));  // raw pad tap 7 depth 1 @ (332.0, 951.0)\n")
    assert raw_reset(tree, "rst_rl_45", body) == ("rst_rl_45", [], [])
    name, rtl, inst = raw_reset(tree, "rst_n_t29", body)
    assert rtl[-1] == "    ot_dp_rrelay u_cland_reset_rst_n_t29 (.clk(clk), .d(rst_rl_45), .q(cland_reset_rst_n_t29));"
    assert len(inst) == 1
    # same site, other depth: another relay (not cycle-equal) -> copy
    deep = body.replace("depth 1 @", "depth 3 @")
    assert raw_reset(tree, "rst_rl_45", deep)[0] == "cland_reset_rst_rl_45"


def test_build_local_on_a_stale_tree_keeps_every_reset_on_the_collector_tree():
    from landing_collector import build_local, check_local_resets
    tree, body = _stale_vehicle()
    s = [dict(name="ring", node="rst_n_t29", ready="r", fault="f", xy_um=[332, 1322])]
    r = build_local(tree, s, body)
    text = "\n".join(r["rtl"])
    assert ".rst_n(rst_rl_45)" not in text and ".d(rst_rl_45)" not in text
    assert ".rst_n(cland_reset_rst_rl_45)" in text and ".rst_n(cland_reset_rst_n_t29)" in text
    assert check_local_resets(tree, body + text) == 5      # 2 copies + 3 collectors (the root on rst_root_n)


def test_check_local_resets_rejects_the_old_name_wiring():
    """Mutants: the 11-08 form (copy .d = a same-named relay at another site; collector on such a relay) must raise."""
    import pytest
    from landing_collector import check_local_resets
    tree, body = _stale_vehicle()
    copy_mut = body + ("    wire cland_reset_rst_n_t29;\n"
                       "    ot_dp_rrelay u_cland_reset_rst_n_t29 (.clk(clk), .d(rst_rl_45), .q(cland_reset_rst_n_t29));\n")
    with pytest.raises(ValueError, match="not its collector-tree parent rst_rl_45"):
        check_local_resets(tree, copy_mut)
    coll_mut = body + ("    ot_dp_landing_collect #(.N(1)) u_cland_collect_rst_rl_45 (\n"
                       "        .clk(clk), .rst_n(rst_rl_45), .ready_i({r}),\n"
                       "        .fault_i({f}), .ready_o(a), .fault_o(b));\n")
    with pytest.raises(ValueError, match="u_cland_collect_rst_rl_45: rst_n rst_rl_45"):
        check_local_resets(tree, coll_mut)
    skip_mut = body + ("    ot_dp_rrelay u_cland_reset_rst_n_t29 (.clk(clk), .d(rst_root_n), .q(cland_reset_rst_n_t29));\n")
    with pytest.raises(ValueError, match="not its collector-tree parent"):
        check_local_resets(tree, skip_mut)           # a skipped level (not cycle-equal) also fails
