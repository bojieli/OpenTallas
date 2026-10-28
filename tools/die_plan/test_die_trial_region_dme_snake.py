"""DIE-QC-9: --region-dme-snake opt-in (COORD 10-28: standard zero-skew DME wire elongation, plan-computed, part of the
tree; not a residual meander ECO) and --region-dme-early-ff (corner-averaged early hang target)."""
import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import die_trial as D
from test_die_trial_slice_balance import FakeSite, _c_partition


def _su_like():
    """SU-region pattern: a tight cluster of 3 core pins at the bottom edge + a spread 4 x 4 grid above, one core in
    the middle; the delay DME cannot zero-skew the cluster against the grid without elongation (DIE-QC-8 trial6)."""
    site = FakeSite(1300.0, 1400.0, [(150.0, 300.0, 1150.0, 700.0)])
    taps = [("s", f"c{k}", 400.0 + 30.0 * k, 160.0) for k in range(3)]
    taps += [("s", f"t{i}_{j}", 100.0 + 360.0 * i, 760.0 + 200.0 * j) for i in range(4) for j in range(4)]
    return site, taps


def _arrivals(dn, root, rep, tap_ps=True):
    """model arrival (ps) of every tap: legs priced as tree_netlist builds them (a snaked leg = its buffer chain);
    the tap leg in ps (tap_wire_ps) as --region-dme-snake prices it"""
    out, st = {}, [(root, 0.0)]
    while st:
        i, a = st.pop()
        d = dn[i]
        for t in d["taps"]:
            L = abs(t[2] - d["x"]) + abs(t[3] - d["y"])
            out[t[1]] = a + (D.tap_wire_ps(L) if tap_ps else L)
        for k in d["kids"]:
            sp = (d.get("snakes") or {}).get(k)
            p, c = (d["x"], d["y"]), (dn[k]["x"], dn[k]["y"])
            st.append((k, a + (D.chain_ps([p] + [tuple(x) for x in sp] + [c]) if sp else D.leg_ps(D._man(p, c), rep))))
    return out


def _spread(a):
    return max(a.values()) - min(a.values())


def test_snake_balances_what_the_delay_dme_cannot():
    site, taps = _su_like()
    base, br, bst = D.dme_region_tree(site, taps, delay_rep_um=250.0)
    dn, root, st = D.dme_region_tree(site, taps, delay_rep_um=250.0, snake=True)
    a0, a = _arrivals(base, br, 250.0, tap_ps=False), _arrivals(dn, root, 250.0)
    assert sorted(a) == sorted(a0)                                    # every tap delivered once
    assert _spread(a0) > 15.0, _spread(a0)                            # the fixture really is unbalanced without it
    assert _spread(a) <= 0.5 * _spread(a0) and _spread(a) <= 15.0, (_spread(a0), _spread(a))
    assert st["snakes"] >= 1 and st["snake_buffers"] >= 1 and st["snake_wire_um"] >= 0.0
    for d in dn:                                                      # every snake buffer is on a legal site
        for pts in (d.get("snakes") or {}).values():
            assert all(site.legal(tuple(p)) for p in pts)


def test_snake_leg_hits_its_target_on_legal_sites():
    site, _ = _su_like()
    pa, q = (100.0, 900.0), (100.0, 1000.0)
    plain = D.leg_ps(100.0, 250.0)
    pts, ps, wire = D.snake_leg(site, pa, q, plain + 60.0, 250.0)
    assert abs(ps - plain - 60.0) <= 3.0, ps
    assert wire > 0 and all(site.legal(tuple(p)) for p in pts)
    assert abs(D.chain_ps([pa] + [tuple(p) for p in pts] + [q]) - ps) < 1e-6
    assert all(D._man(a, b) <= 250.0 + 1e-6 for a, b in zip([pa] + pts, pts + [q]))   # stages within rep_um


def test_netlist_places_snake_buffers_as_planned():
    site, taps = _su_like()
    nodes = {0: dict(x=650.0, y=1300.0, parent=None, kids=[1], taps=[], level=0),
             1: dict(x=100.0, y=900.0, parent=0, kids=[], taps=[taps[3]], level=1,
                     snake=[[400.0, 1380.0], [100.0, 1380.0]])}
    _, place, *_ = D.tree_netlist(nodes, taps, rep_um=250.0, site=site)
    reps = [(x, y) for n, x, y in place if n.startswith("r1_")]
    assert reps == [(400.0, 1380.0), (100.0, 1380.0)]
    assert nodes[1]["detour_um"] == 160.0                         # 2 x 80 um above the pa/q box


def test_default_unchanged_and_opt_in():
    site, taps = _c_partition()
    a, ra, sa = D.dme_region_tree(site, taps, delay_rep_um=250.0)
    b, rb, sb = D.dme_region_tree(site, taps, delay_rep_um=250.0, snake=False)
    assert a == b and ra == rb and sa == sb
    for f in (D.clock_kit, D.write_kit):
        ps = inspect.signature(f).parameters
        assert ps["region_dme_snake"].default is None and ps["region_dme_early_ff"].default is None
    assert inspect.signature(D.dme_region_tree).parameters["snake"].default is False
    assert inspect.signature(D.attach_region_dme).parameters["snake"].default is None
    src = inspect.getsource(D.main)
    assert "--region-dme-snake" in src and "--region-dme-early-ff" in src


def test_early_tap_snake_removes_over_delivery():
    site, taps = _su_like()
    t = taps[5]
    e = 40.0
    dn, root, st = D.dme_region_tree(site, taps, delay_rep_um=250.0, early={(t[0], t[1]): e}, snake=True)
    row = st["early_taps"][0]
    assert row["miss_ps"] >= -3.0                    # hung where it is early by >= e, never under-delivered
    if row.get("miss_unsnaked_ps", 0.0) > D.SNAKE_TOL_PS:
        assert abs(row["miss_ps"]) <= 3.0, row       # the hang leg elongation takes the over-delivery out
    a = _arrivals(dn, root, 250.0)
    rest = [v for k, v in a.items() if k != t[1]]
    got = sum(rest) / len(rest) - a[t[1]]
    assert abs(got - e) <= 15.0, (got, row)


def test_in_core_tap_leg_priced_in_ps():
    """a core pin 100 um inside a core: its tap leg is ~1.4 + 3.4 ps of wire, not 100 'ps' (DIE-QC-9 trial7 finding)"""
    assert abs(D.tap_wire_ps(100.0) - (0.013984 * 100 + 0.00033554 * 1e4)) < 1e-9
    site = FakeSite(1300.0, 1400.0, [(150.0, 300.0, 1150.0, 700.0)])
    taps = [("s", "pin", 650.0, 400.0)] + [("s", f"t{i}", 100.0 + 360.0 * i, 900.0) for i in range(4)]
    dn, root, st = D.dme_region_tree(site, taps, delay_rep_um=250.0, snake=True)
    a = _arrivals(dn, root, 250.0)
    assert _spread(a) <= 12.0, a


def test_early_deeper_than_the_tree_gets_a_deeper_root():
    """an early larger than the whole region tree: a new top node with an elongated leg to the old root, never a late tap"""
    site, taps = _su_like()
    t = taps[0]
    base, br, _ = D.dme_region_tree(site, taps, delay_rep_um=250.0, snake=True)
    e = base[br]["S"] + 80.0
    dn, root, st = D.dme_region_tree(site, taps, delay_rep_um=250.0, early={(t[0], t[1]): e}, snake=True)
    row = st["early_taps"][0]
    assert abs(row["miss_ps"]) <= 5.0, row
    a = _arrivals(dn, root, 250.0)
    rest = [v for k, v in a.items() if k != t[1]]
    assert abs(sum(rest) / len(rest) - a[t[1]] - e) <= 15.0
    assert max(rest) - min(rest) <= 15.0
