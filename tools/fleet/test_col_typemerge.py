"""S81-TYPEMERGE-IMPL tests: sibling groups, R2 depth unify, R4 tap re-derive, R1 layout merge across clock classes."""
import copy
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
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
