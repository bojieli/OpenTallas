"""CLK-TOOL-8: --clock-edge-alt opt-in (per-stage edge balance, inv2 region DME).  With even legs every branch-node
driver of an inv2 tree has the same output polarity, so its rise/fall asymmetry adds up once per tree level (HEAD hk4:
88 TT / 226 FF taps outside duty 45-55 at ~15 levels).  EDGE_ALT labels region-DME nodes with polarity P = height % 2
(leaves and region roots 0) and rounds each leg to the parity of its two ends, priced in the DME."""
import inspect
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import die_trial as D
from test_die_trial_slice_balance import _c_partition


@pytest.fixture(autouse=True)
def _iso(monkeypatch):
    monkeypatch.setattr(D, "leg_blocked_run", lambda site, a, b: 0.0)
    monkeypatch.setattr(D, "EVEN_LEGS", True)
    monkeypatch.setattr(D, "EDGE_ALT", False)
    monkeypatch.setattr(D, "_LEG_PAR", 0)


def _region(n_extra=0):
    site, taps = _c_partition()
    taps = taps + [("c", f"e{k}", 120.0 + 70.0 * k, 1340.0) for k in range(n_extra)]
    nodes = {0: dict(id=0, x=617.0, y=1309.0, parent=None, level=0, kids=[], taps=[], region=[0, 0, 1, 1],
                     region_root="R0")}
    return site, taps, {t[0]: "R0" for t in taps}, nodes


def _build(alt, monkeypatch, **kw):
    monkeypatch.setattr(D, "EDGE_ALT", alt)
    site, taps, regions, nodes = _region(**kw)
    D.attach_region_dme(nodes, site, taps, regions, delay_rep_um=250.0)
    v = D.tree_netlist(nodes, taps, rep_um=250.0, clock_cell="inv2")[0]
    return nodes, v, taps


def _paths(v):
    """{tap port: [(output inverted?, heavy?)] root -> tap}; heavy = the stage output net has fanout >= 2"""
    drv, fo = {}, {}
    for m in re.finditer(r"^\s+(\S+) (\S+) \(\.A\((\S+)\), \.Y\((\S+)\)\);", v, re.M):
        drv[m.group(4)] = (m.group(1), m.group(3))
        fo[m.group(3)] = fo.get(m.group(3), 0) + 1
    asg = re.findall(r"assign (\S+) = (\S+);", v)
    for _, n in asg:
        fo[n] = fo.get(n, 0) + 1
    out = {}
    for port, n in asg:
        ch = []
        while n != "root":
            cell, a = drv[n]
            ch.append((cell == D.CLK_INV, fo.get(n, 0) >= 2))
            n = a
        ch.reverse()
        par, st = 0, []
        for inv, heavy in ch:
            par ^= int(inv)
            st.append((par, heavy))
        out[port] = st
    return out


def _edge(paths, b_light=1.0, b_heavy=-1.0):
    """toy per-stage asymmetry model (sign by output polarity): fall-rise at every tap"""
    return {p: sum((1 if inv else -1) * (b_heavy if heavy else b_light) for inv, heavy in st)
            for p, st in paths.items()}


def test_default_off_byte_identical(monkeypatch):
    assert D.EDGE_ALT is False
    n0, v0, _ = _build(False, monkeypatch)
    assert all("pol" not in nd for nd in n0.values())
    site, taps = _c_partition()
    dn, _, _ = D.dme_region_tree(site, taps, delay_rep_um=250.0)
    assert all("P" not in d and "H" not in d for d in dn)
    with D.leg_parity(0):
        assert D.leg_ps(600.0, 250.0) == D.leg_ps(600.0, 250.0)
    assert "--clock-edge-alt" in inspect.getsource(D.main)


def test_labels_alternate_by_height_roots_true(monkeypatch):
    monkeypatch.setattr(D, "EDGE_ALT", True)
    site, taps = _c_partition()
    dn, root, st = D.dme_region_tree(site, taps, delay_rep_um=250.0)
    assert dn[root]["P"] == 0
    seen, stack = [], [root]
    while stack:
        i = stack.pop()
        seen.append(i)
        stack += dn[i]["kids"]
    for i in seen:
        d = dn[i]
        if not d["kids"]:
            assert d["P"] == 0 and d["H"] == 0
        elif i != root:
            assert d["P"] == d["H"] % 2
    assert max(dn[i]["H"] for i in seen) >= 4                # deep enough to matter


def test_leg_parity_priced(monkeypatch):
    d0 = D.STAGE_1X_TT[0]
    even = D.leg_ps(600.0, 250.0)                            # 3 -> 4 stages
    with D.leg_parity(1):
        odd = D.leg_ps(600.0, 250.0)                         # 3 stages
        odd1 = D.leg_ps(100.0, 250.0)                        # 1 stage
    assert odd < even and abs(D.leg_ps(100.0, 250.0) - odd1 - d0) < 1.0 + D.STAGE_1X_TT[2] * 1e4
    assert D._LEG_PAR == 0                                   # context restored


@pytest.mark.parametrize("extra", [0, 5])
def test_netlist_true_taps_alternating_branches(monkeypatch, extra):
    nodes, v, taps = _build(True, monkeypatch, n_extra=extra)
    assert D.BUF not in v and " q" not in v                  # no tap parity inverters
    paths = _paths(v)
    assert len(paths) == len(taps)
    assert all(st[-1][0] == 0 for st in paths.values())     # true polarity at every tap
    for i, nd in nodes.items():
        assert nd.get("inv_parity", 0) == nd.get("pol", 0)
        if nd["taps"]:
            assert nd.get("pol", 0) == 0
    assert any(nd.get("pol") == 1 for nd in nodes.values())  # some branch nodes really are inverted
    _, vb, _ = _build(False, monkeypatch, n_extra=extra)
    eb, ea = _edge(_paths(vb)), _edge(paths)
    worst_b, worst_a = max(map(abs, eb.values())), max(map(abs, ea.values()))
    # inv2 base: +2 per level on every path (never cancels); alternation keeps it bounded
    assert worst_b >= 6.0, worst_b
    assert worst_a <= worst_b / 2, (worst_a, worst_b)


def test_model_spread_kept(monkeypatch):
    site, taps = _c_partition()
    base = D.dme_region_tree(site, taps, delay_rep_um=250.0)[2]["spread_um"]
    monkeypatch.setattr(D, "EDGE_ALT", True)
    alt = D.dme_region_tree(site, taps, delay_rep_um=250.0)[2]["spread_um"]
    assert alt <= base + D.STAGE_1X_TT[0], (base, alt)


def test_fail_closed(monkeypatch):
    monkeypatch.setattr(D, "EDGE_ALT", True)
    site, taps = _c_partition()
    with pytest.raises(ValueError, match="delay-priced"):
        D.dme_region_tree(site, taps)
    with pytest.raises(ValueError, match="hang-mode"):
        D.dme_region_tree(site, taps, delay_rep_um=250.0, early={(taps[0][0], taps[0][1]): 60.0})
