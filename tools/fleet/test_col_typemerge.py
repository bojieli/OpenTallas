"""S81-TYPEMERGE-IMPL tests: sibling groups, R2 depth unify, R4 tap re-derive, R1 layout merge across clock classes."""
import copy
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "die_plan"))
import col_inherit as CI
import col_typemerge as TM


def core(inst, org):
    return dict(inst=inst, module="ot_rom_4096x72_m8", lef="a.lef", lib="a.lib", origin_um=org, orient="R0")


def ctype(name, cl, pv, tapx, img):
    return dict(module=name, outline_um=[100, 100], buses=[dict(name="ft1_i")], ft_slots=[], internal_stations=[], reset={},
                contents=[dict(inst="u0", module="m")], sources=["x.sv"], hard=False, hard_cores=[core("u_r0.u_e0.u_w", [10, 20])],
                clock=dict(taps=[dict(name="u_r0.u_e0.u_w.ck", kind="core", xy=[tapx, 20.0])],
                           landing_contract=dict(collector_tree=dict(type=name))),
                note="x " + name, param_base_type="b", param_set={"P_A_INSTANCE": '"%s"' % img})


def mkplan():
    names = [("col_h9_r1__t1__cl11111111__pv00000001", 11, 140.0, "i1"), ("col_h9_r1__t1__cl11111111__pv00000002", 11, 140.0, "i2"),
             ("col_h9_r1__t1__cl22222222__pv00000003", 22, 146.0, "i3")]
    pt = {n: ctype(n, c, 0, x, img) for n, c, x, img in names}
    parts = [dict(name="p%d" % i, type=n) for i, (n, *_r) in enumerate(names)]
    ports = [dict(id="a%d" % i, src=dict(part="s", bus="o"), dst=dict(part="p%d" % i, bus="ft1_i")) for i in range(3)]
    return dict(partition_types=pt, partitions=parts, ports=ports)


def test_sibling_group_ignores_image_and_clock():
    plan = mkplan()
    assert len(TM.sibling_groups(plan)) == 1


def test_layout_groups_split_on_taps_then_merge_after_retap():
    plan = mkplan()
    assert len(TM.layout_groups(plan)) == 2        # tap x differs between the clock classes
    taps = [t["clock"]["taps"][0]["xy"][0] for t in TM.col_types(plan).values()]
    new, rep = TM.retap(plan)
    assert rep["taps_moved"] == 1 and rep["max_move_um"] == 6.0
    assert len(TM.layout_groups(new)) == 1         # cl label and pv name are not layout


def test_retap_leaves_input_untouched():
    plan = mkplan()
    before = copy.deepcopy(plan)
    TM.retap(plan)
    assert plan == before


def test_depth_unify_raises_to_group_max_only():
    plan = mkplan()
    table = dict(count_aligned=dict(ports={"a0": dict(K=-3, depth=4, sched_lat=0, tree=False),
                                           "a1": dict(K=-1, depth=8, sched_lat=0, tree=False),
                                           "a2": dict(K=5, depth=4, sched_lat=0, tree=False)}))
    new, rep = TM.depth_unify(plan, table)
    assert [new["count_aligned"]["ports"][k]["depth"] for k in ("a0", "a1", "a2")] == [8, 8, 8]
    assert [new["count_aligned"]["ports"][k]["K"] for k in ("a0", "a1", "a2")] == [-3, -1, 5]    # K untouched
    assert rep["ports_raised"] == 2
    assert table["count_aligned"]["ports"]["a0"]["depth"] == 4                                 # input untouched


def test_merge_classes_groups_across_clock_class():
    plan = mkplan()
    new, _ = TM.retap(plan)
    assert len(CI.groups(new)) == 2                                   # one per clock class label
    g = CI.groups(new, merge_classes=True)
    assert len(g) == 1
    only = next(iter(g.values()))
    assert len(only["members"]) == 3 and only["verdict"] == "OK"


def test_layout_hash_ignores_collector_child_instance_name():
    plan = mkplan()
    new, _ = TM.retap(plan)
    names = list(TM.col_types(new))
    for i, n in enumerate(names):
        new["partition_types"][n]["clock"]["landing_contract"]["collector_children"] = [dict(part="fE%d_p3_b0" % i, xy_um=[1, 2], node="rst_n_t4")]
    assert len(TM.layout_groups(new)) == 1
    new["partition_types"][names[0]]["clock"]["landing_contract"]["collector_children"][0]["xy_um"] = [9, 9]
    assert len(TM.layout_groups(new)) == 2


def test_union_keep_outs_only_changed_types():
    outs = {"a": [0], "b": [0, 2], "c": [2], "d": [5]}
    ko = TM.union_keep_outs(outs, {"g1": ["a", "b", "c"], "g2": ["d"]})
    assert ko == {"a": [0, 2], "c": [0, 2]}          # b already holds the union, d is alone


def _sup_plan():
    import json as _j
    def lc(children, tree):
        return dict(collector_children=children, collector_tree=tree, pins=[dict(name="cland_up_ready"), dict(name="cland_up_fault")]
                    + [dict(name=n % i, dir="in") for i, _c in enumerate(children) for n in ("cland_dn_ready_%d", "cland_dn_fault_%d")],
                    bands={})
    ch = lambda i, x: dict(index=i, xy_um=[x, 5.0], seam=False, node="n%d" % i, part="p%d" % i)
    pt = {}
    for n, kids, tree in (("col_h9_r1__t1__cla__pv1", [ch(0, 10.0)], "T1"), ("col_h9_r1__t1__cla__pv2", [ch(0, 20.0)], "T2"),
                          ("col_h9_r1__t1__cla__pv3", None, None)):
        t = dict(clock=dict(edge_clocks=[], added_taps=[]))
        if kids is not None:
            t["clock"]["landing_contract"] = lc(kids, tree)
        pt[n] = t
    plan = dict(partition_types=pt, partitions=[], clock=dict(landing_network=dict(edges=[])))
    side = dict(collector=dict(types={}, edges=[]))
    return plan, side


def test_superset_collector_only_keeps_plain_and_own_tree():
    import cland_col_superset as SS
    plan, side = _sup_plan()
    SS.build(plan, side, collector_only=True, keep_tree=True)
    pt = plan["partition_types"]
    assert "landing_contract" not in pt["col_h9_r1__t1__cla__pv3"]["clock"]          # no R3b
    a, b = (pt["col_h9_r1__t1__cla__pv%d" % i]["clock"]["landing_contract"] for i in (1, 2))
    assert [c["xy_um"] for c in a["collector_children"]] == [c["xy_um"] for c in b["collector_children"]] and len(a["collector_children"]) == 2
    assert a["collector_tree"] == "T1" and b["collector_tree"] == "T2"               # trees not copied from the template
    assert [t["index"] for t in a["tieable_children"]] == [0, 1]


def test_superset_keeps_own_up_pin_when_template_up_is_far():
    """S81-GEOM-OPUS 11-19 (D8h g fE4_p1_b0 1,045 um): a member keeps its own up pins when the template's would put
    its up edge over max_hop; a member whose up edge stays short takes the template contract."""
    import cland_col_superset as SS
    UPN = ("cland_up_ready", "cland_up_fault", "fclk_out_cland_up")

    def lc(children, upxy):
        pins = [dict(name=n, xy_um=list(upxy)) for n in UPN]
        pins += [dict(name=n % c["index"], xy_um=c["xy_um"]) for c in children for n in ("cland_dn_ready_%d", "cland_dn_fault_%d")]
        return dict(collector_children=children, pins=pins, bands={})
    ch = lambda i, xy: dict(index=i, xy_um=list(xy), seam=False, node="n%d" % i)
    pt = {
        # template (2 children) has its up pin on the E face; pv2 has it on the N face, right under its parent's dn child
        "col_h9_r0_p1__t1__pv1": dict(outline_um=[1000, 1000], clock=dict(edge_clocks=[], added_taps=[],
                                      landing_contract=lc([ch(0, (5, 300)), ch(1, (5, 700))], (995, 500)))),
        "col_h9_r0_p1__t1__pv2": dict(outline_um=[1000, 1000], clock=dict(edge_clocks=[], added_taps=[],
                                      landing_contract=lc([ch(0, (5, 700))], (500, 995)))),
        "col_h9_r1__t1__pvP": dict(outline_um=[1000, 1000], clock=dict(edge_clocks=[], added_taps=[],
                                   landing_contract=lc([ch(0, (500, 5))], (5, 5)))),
    }
    parts = [dict(name="a", type="col_h9_r0_p1__t1__pv1", origin_um=[0, 0], orient="R0"),
             dict(name="b", type="col_h9_r0_p1__t1__pv2", origin_um=[2000, 0], orient="R0"),
             dict(name="pa", type="col_h9_r1__t1__pvP", origin_um=[0, 1000], orient="R0"),
             dict(name="pb", type="col_h9_r1__t1__pvP", origin_um=[2000, 1000], orient="R0")]
    edges = [dict(id="mon_%s" % s, src=dict(part=s, bus="cland_up_ready"), dst=dict(part=d, bus="cland_dn_ready_0"), max_hop_um=405)
             for s, d in (("a", "pa"), ("b", "pb"))]
    plan = dict(partition_types=pt, partitions=parts, clock=dict(landing_network=dict(edges=edges)))
    side = dict(collector=dict(types={}, edges=[]))
    rep = SS.build(plan, side, fam_re="col_h9_r0_p1", collector_only=True, keep_taps=True)
    up = lambda k: next(p["xy_um"] for p in pt[k]["clock"]["landing_contract"]["pins"] if p["name"] == "cland_up_ready")
    assert list(rep["_up_kept"]) == ["col_h9_r0_p1__t1__pv2"]
    assert up("col_h9_r0_p1__t1__pv2") == [500, 995] and up("col_h9_r0_p1__t1__pv1") == [995, 500]
    assert len(pt["col_h9_r0_p1__t1__pv2"]["clock"]["landing_contract"]["collector_children"]) == 2   # dn union kept
    assert SS.die_xy(dict(origin_um=[10, 20], orient="R180"), dict(outline_um=[100, 50]), (1, 2)) == (109, 68)
