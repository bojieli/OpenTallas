#!/usr/bin/env python3
"""CLOCK-128-R2 tests: no loadless tree net by construction (plan error otherwise), plan-site placement with only the
PG snap allowed (a farther move is a plan error), slice -> die-frame site export.
python3 -m pytest tools/die_plan/test_clock128_r2.py"""
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_clock_mesh as CM  # noqa: E402
import die_clock_128 as C128  # noqa: E402
import clock_plan_sites as CPS  # noqa: E402

LIBDIR = Path("~/.cache/opentallas/asap7_nldm").expanduser()
need_lib = pytest.mark.skipif(not (LIBDIR / "asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz").exists(),
                              reason="ASAP7 NLDM liberty")


def _plan():
    rects = dict(A=(0., 0., 800., 800.), B=(800., 0., 1600., 800.))
    P = SimpleNamespace(W=1600., H=800., clock={}, types=dict(ta={}), layer_budget=dict(partition_signal_max="M7"),
                        parts=dict(A=dict(type="ta"), B=dict(type="ta")), rect=lambda n: rects[n],
                        to_die=lambda n, xy: xy)
    taps = [("A", "clk", 300., 300., 0.), ("B", "clk", 1200., 500., 0.)]
    return P, taps


def _build(ko=(), allow=False, sites=None, **kw):
    P, taps = _plan()
    with patch.object(CM.DC, "keepouts", return_value=list(ko)), patch.object(CM.DC, "plan_taps", return_value=taps), \
            patch.object(CM.DC, "plan_tap_early", return_value={}):
        return CM.build(P, 4, 4, m=2, max_move=50., rule128=dict(libdir=str(LIBDIR), allow_plan_errors=allow),
                        plan_sites=sites, **kw)


def test_fixed_wires_refuses_loadless_net():
    M = dict(taps=[], meta=dict(root_um=[0., 0.]))
    with pytest.raises(C128.PlanError) as e:
        C128.fixed_wires(M, {}, [dict(name="ckm_w_x", drv="port:root", loads=[])], 1.0, 0.27)
    assert e.value.rows[0]["kind"] == "empty_tree_net" and e.value.rows[0]["name"] == "ckm_w_x"


@need_lib
def test_dead_leaf_pair_is_pruned_and_reported_not_crashing():
    # keep-out over lattice points (0,0) and (0,1) (x 200, y 100 / 300): before R2 their leaf node net had no load
    # and fixed_wires crashed on max() of an empty sequence
    ko = [(0., 0., 400., 400., "A/core")]
    with pytest.raises(C128.PlanError) as e:
        _build(ko)
    kinds = {r["kind"] for r in e.value.rows}
    assert "unplaced" in kinds and "empty_tree_net" not in kinds
    cells, nets, ports, M = _build(ko, allow=True)           # diagnostic build: written, never qualifies
    assert all(n["loads"] for n in nets)
    assert M["meta"]["plan_errors"] >= 2 and M["meta"]["pruned_branches"] >= 1
    assert "plan errors (diagnostic --allow-plan-errors build)" in CM.banned_means_12_8d(M)
    assert M["meta"]["unplaced"]                              # combo refuses it


def _lattice_sites(dxy=(0.3, 0.0)):
    """sites at every lattice point of the clean build, offset by dxy (a PG-track snap)."""
    cells, nets, ports, M = _build()
    pts = [("drv", d["ideal"]) for d in M["drivers"].values()]
    for h in M["htree"]:
        if not h["leaf"]:
            pts.append(("node", h["b"]))
        a, b, n = h["a"], h["b"], h["n_seg"]
        pts += [("rep", (a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n)) for k in range(1, n)]
    pts.append(("root", ((M["xs"][0] + M["xs"][-1]) / 2, (M["ys"][0] + M["ys"][-1]) / 2)))
    sites = [dict(name=f"I{k}:isl0", role=r, inst=f"I{k}", island="isl0", xy_um=[p[0] + dxy[0], p[1] + dxy[1]])
             for k, (r, p) in enumerate(pts)]
    return dict(schema=C128.SITES_SCHEMA, snap_um=0.5, sites=sites)


@need_lib
def test_plan_sites_place_every_driver_and_node_on_site():
    S = _lattice_sites((0.3, 0.0))
    cells, nets, ports, M = _build(sites=S)
    assert M["meta"]["plan_sites"]["used"] == len(S["sites"])
    assert not M.get("plan_errors")
    xy = {s["name"]: s["xy_um"] for s in S["sites"]}
    for d in M["drivers"].values():
        assert d["move_um"] <= 0.5 and d["cell_site"] == [round(v, 4) for v in xy[d["plan_site"]]]
        assert d["pushdown"]["island"] == "isl0"
    for h in M["htree"]:
        if not h["leaf"]:
            assert h["node_move_um"] <= 0.5 and h["plan_site"] in xy


@need_lib
def test_plan_site_beyond_snap_is_a_plan_error():
    S = _lattice_sites((0.3, 0.0))
    s0 = next(s for s in S["sites"] if s["role"] == "drv")
    s0["xy_um"][0] += 2.0                                       # 2.3 um off: more than the PG snap
    with pytest.raises(C128.PlanError) as e:
        _build(sites=S)
    bad = [r for r in e.value.rows if r["kind"] == "no_plan_site"]
    assert len(bad) == 1 and bad[0]["role"] == "mesh_driver" and bad[0]["nearest_um"] == pytest.approx(2.3)


@need_lib
def test_plan_sites_need_rule_12_8():
    P, taps = _plan()
    with patch.object(CM.DC, "keepouts", return_value=[]), patch.object(CM.DC, "plan_taps", return_value=taps), \
            patch.object(CM.DC, "plan_tap_early", return_value={}), pytest.raises(ValueError):
        CM.build(P, 4, 4, plan_sites=_lattice_sites())


def test_site_index_taken_vs_missing():
    SI = C128.SiteIndex([dict(name="a", xy_um=[10., 10.])])
    st, d, err = SI.take((10.2, 10.), "c1")
    assert st["name"] == "a" and d == pytest.approx(0.2)
    st, d, err = SI.take((10., 10.1), "c2")
    assert st is None and err["kind"] == "site_taken" and err["taken_by"] == "c1"
    st, d, err = SI.take((50., 10.), "c3")
    assert st is None and err["kind"] == "no_plan_site"


def test_load_plan_sites_checks_plan_sha(tmp_path):
    f = tmp_path / "s.json"
    f.write_text(json.dumps(dict(schema=C128.SITES_SCHEMA, plan_sha256="ab" * 32, sites=[dict(name="x", xy_um=[0, 0])])))
    assert C128.load_plan_sites(f, "ab" * 32)["sites"]
    with pytest.raises(ValueError):
        C128.load_plan_sites(f, "cd" * 32)


def test_sites_from_slices_maps_partition_and_core_instances():
    # two partitions of type ta (second one offset by 1000 in x), one hard core per type, MY-mirrored
    P = SimpleNamespace(parts=dict(A=dict(type="ta"), B=dict(type="ta")),
                        types=dict(ta=dict(hard_cores=[dict(inst="u0", module="cm", origin_um=[100., 50.],
                                                            outline_um=[200., 100.], orient="MY")])),
                        to_die=lambda n, xy: (xy[0] + (1000. if n == "B" else 0.), xy[1]))
    isl = lambda name, role, c: dict(name=name, role=role, centre_um=list(c),
                                     rect_um=[c[0] - 4.32, c[1] - 4.32, c[0] + 4.32, c[1] + 4.32],
                                     ft_ports=[dict(name=f"mp_{name}_ck_i")])
    slices = [dict(kind="partition", type="ta", pushdown=dict(islands=[isl("isl0", "die_node", (400., 400.))],
                                                              clock_repeaters=[dict(name="crep0", xy_um=[20., 30.])])),
              dict(kind="core", type="cm", module="cm", pushdown=dict(islands=[isl("isl1", "tree_leaf", (40., 60.))]))]
    sites = {s["name"]: s for s in CPS.sites_from_slices(P, slices)}
    assert sites["A:isl0"]["xy_um"] == [400., 400.] and sites["B:isl0"]["xy_um"] == [1400., 400.]
    assert sites["B:crep0"]["role"] == "clock_rep" and sites["B:crep0"]["xy_um"] == [1020., 30.]
    # core-local (40, 60) mirrored about the core's y axis: x = 100 + (200 - 40) = 260, y = 50 + 60 = 110
    assert sites["A/u0:isl1"]["xy_um"] == [260., 110.] and sites["B/u0:isl1"]["xy_um"] == [1260., 110.]
    assert sites["A/u0:isl1"]["rect_um"] == [255.68, 105.68, 264.32, 114.32]
    assert not CPS.collisions(list(sites.values()))

