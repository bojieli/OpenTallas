"""DIE-QC-3: --clock-rc 1x and --slice-balance opt-ins (builder bugs (i) model RC, (ii) balance after legalization)."""
import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import die_trial as D
from test_die_trial_slice_spine import FakeSite, two_slices


def _legalize(nodes, site):
    """the --slice-spine site pass of clock_kit (balanced_site + round_legal)"""
    for i, nd in sorted(nodes.items()):
        nd["req_xy"] = [nd["x"], nd["y"]]
        if site.legal((nd["x"], nd["y"])):
            continue
        par = (nodes[nd["parent"]]["x"], nodes[nd["parent"]]["y"]) if nd["parent"] is not None else None
        kids = [(nodes[k]["x"], nodes[k]["y"]) for k in nd["kids"]] + [tuple(t[2:4]) for t in nd["taps"]]
        q, _ = D.balanced_site(site, (nd["x"], nd["y"]), par, kids, nd.get("split"))
        nd["x"], nd["y"] = D.round_legal(site, q if q is not None else site.nearest((nd["x"], nd["y"])))


def _leaf_spread(nodes, R):
    """per region: spread of root -> leaf length + the leaf's mean last mile (the quantity balance_legalize equalises)"""
    L = D.path_lengths(nodes)
    out = {}
    for i, nd in nodes.items():
        if nd["taps"]:
            v = L[i] + sum(abs(t[2] - nd["x"]) + abs(t[3] - nd["y"]) for t in nd["taps"]) / len(nd["taps"])
            out.setdefault(R[nd["taps"][0][0]], []).append(v)
    return {r: max(v) - min(v) for r, v in out.items()}


def _cored():
    """two_slices + 'cores' over off-centre local merge points, so the site pass must move them along a split axis"""
    P, taps, R, site = two_slices()
    site.blocked += [(60.0, 130.0, 140.0, 280.0), (70.0, 70.0, 130.0, 130.0), (260.0, 960.0, 340.0, 1090.0),
                     (480.0, 2560.0, 560.0, 2700.0), (640.0, 1360.0, 760.0, 1440.0)]
    return P, taps, R, site


def test_slice_balance_restores_equal_lengths_after_the_site_pass():
    P, taps, R, site = _cored()
    nodes, _ = D.build_slice_spine_tree(P, taps, R, leaf_um=200.0, site=site, top_leaf_um=20.0)
    _legalize(nodes, site)
    before = _leaf_spread(nodes, R)
    col_x = {i: n["x"] for i, n in nodes.items() if n.get("spine") == "column"}
    sel = [i for i, nd in nodes.items() if nd["parent"] is not None and nd.get("spine") != "top"]
    st = D.balance_legalize(nodes, site, select=sel)
    after = _leaf_spread(nodes, R)
    assert max(before.values()) > 20.0, before                 # the site pass did unbalance the tree
    assert max(after.values()) < max(before.values()) and max(after.values()) <= 22.0, (before, after, st)
    # 20 um = the floor of this fixture: every strip root sits beside the blocked centre column (10 um halo each side)
    for i, n in nodes.items():
        assert site.legal((n["x"], n["y"])), (i, n["x"], n["y"])
    for i, x in col_x.items():                                 # column nodes stay on their column
        assert abs(nodes[i]["x"] - x) < 1e-6
    for n in nodes.values():                                   # top spine untouched
        if n.get("spine") == "top":
            assert n["x"] == n["req_xy"][0] and n["y"] == n["req_xy"][1]


def test_default_balance_legalize_unchanged_without_select():
    sig = inspect.signature(D.balance_legalize)
    assert sig.parameters["select"].default is None
    assert inspect.signature(D.clock_kit).parameters["slice_balance"].default is False


def test_clock_rc_1x_is_the_asap7_setrc_and_default_is_unchanged():
    r, c = D.WIRE_RC_1X
    assert abs(r - 2 * D.WIRE_R) < 1e-12 and abs(c * 1.1 - D.WIRE_C) < 1e-12
    assert abs(r - 8.6716e-3) < 1e-6                           # 8.67 ohm/um: ASAP7 M8/M9 setRC mean
    assert inspect.signature(D.clock_kit).parameters["clock_rc"].default == "ndr"
    assert inspect.signature(D.write_kit).parameters["clock_rc"].default == "ndr"
    src = inspect.getsource(D.main)
    assert "--clock-rc" in src and "--slice-balance" in src


def test_blocked_bisector_takes_the_near_site_not_a_far_locus_point():
    """two kids symmetric about a blocked line: the exact locus (x = 200) is legal only 600 um away; the near site wins"""
    site = FakeSite(400.0, 1000.0, [(190.0, 5.0, 210.0, 995.0)])
    nodes = {0: dict(x=200.0, y=900.0, parent=None, kids=[1], taps=[], fixed=True, spine="top", req_xy=[200.0, 900.0]),
             1: dict(x=210.0, y=600.0, parent=0, kids=[2, 3], taps=[], req_xy=[200.0, 600.0]),
             2: dict(x=100.0, y=600.0, parent=1, kids=[], taps=[("p", "a", 100.0, 650.0)], req_xy=[100.0, 600.0]),
             3: dict(x=300.0, y=600.0, parent=1, kids=[], taps=[("p", "b", 300.0, 650.0)], req_xy=[300.0, 600.0])}
    st = D.balance_legalize(nodes, site, select=[1, 2, 3])
    assert abs(nodes[1]["y"] - 600.0) < 1.0 and site.legal((nodes[1]["x"], nodes[1]["y"]))
    assert st["worst_imbalance_um"] <= 21.0, st


def _c_partition():
    """QC c-partition pattern (cbf_q01, partition-relative um): 2 x 2 hard cores with a centre cross channel; 24 core
    taps on the channel-side core edges (3 rows per core) + 4 glue taps in the centre row"""
    site = FakeSite(1235.5, 2617.9, [(84.2, 75.6, 546.5, 1237.7), (689.0, 75.6, 1151.3, 1237.7),
                                     (84.2, 1388.9, 546.5, 2551.0), (689.0, 1388.9, 1151.3, 2551.0)])
    taps = [("c", f"k{x}_{y}", x, y) for x in (76.7, 554.0, 681.5, 1158.8) for y in (187.0, 561.0, 934.8, 1683.2, 2056.9, 2430.9)]
    taps += [("c", f"g{x}", x, 1309.0) for x in (154.5, 463.3, 772.2, 1081.1)]
    return site, taps


def _dme_lengths(dn, root):
    out, st = [], [(root, 0.0)]
    while st:
        i, L = st.pop()
        d = dn[i]
        for t in d["taps"]:
            out.append(L + abs(t[2] - d["x"]) + abs(t[3] - d["y"]))
        st += [(k, L + abs(dn[k]["x"] - d["x"]) + abs(dn[k]["y"] - d["y"])) for k in d["kids"]]
    return out


def test_region_dme_zero_skew_on_legal_sites_in_a_core_field():
    site, taps = _c_partition()
    dn, root, st = D.dme_region_tree(site, taps)
    L = _dme_lengths(dn, root)
    assert len(L) == len(taps)
    assert max(L) - min(L) <= 2.0, (max(L) - min(L), st)          # the stock slid H-tree: 736-994 um on QC
    st_ = [root]
    while st_:
        d = dn[st_.pop()]
        st_ += d["kids"]
        assert site.legal((d["x"], d["y"])), (d["x"], d["y"])
    assert st["spread_um"] <= 2.0 and st["merges"] == len(taps) - 1


def test_join_merges_a_shallow_subtree_down_instead_of_leaving_skew():
    """one mode only ('gap' cuts the 4 glue taps off as a shallow pair): join() still reaches zero skew"""
    site, taps = _c_partition()
    dn, root, st = D.dme_region_tree(site, taps, modes=("gap",))
    L = _dme_lengths(dn, root)
    assert max(L) - min(L) <= 2.0, st


def test_region_dme_flag_is_opt_in():
    assert inspect.signature(D.build_slice_spine_tree).parameters["region_dme"].default is False
    assert inspect.signature(D.clock_kit).parameters["region_dme"].default is False
    assert "--region-dme" in inspect.getsource(D.main)


def test_leg_ps_prices_a_stage_per_leg():
    assert D.leg_ps(10.0, 250.0) > D.STAGE_1X_TT[0]                # a short leg still costs a whole stage
    assert abs(D.leg_ps(500.0, 250.0) - 2 * D.leg_ps(250.0, 250.0)) < 1e-9
    assert D.leg_ps(251.0, 250.0) > D.leg_ps(250.0, 250.0) + 10.0     # one more stage, shorter stages


def test_region_dme_delay_mode_balances_stage_priced_delay():
    site, taps = _c_partition()
    dn, root, st = D.dme_region_tree(site, taps, delay_rep_um=250.0)
    assert st["spread_um"] <= 25.0, st                               # ps in delay mode (S / Smin are leg_ps sums)
    st_ = [root]
    while st_:
        d = dn[st_.pop()]
        st_ += d["kids"]
        assert site.legal((d["x"], d["y"]))
