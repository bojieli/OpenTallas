"""DIE-HEAD-29 (COORD RULING 10-29 10:01): clock_ocv_fn charges the hard-core class-B latency (core_lat, nB stages)
per tap, and a virtual START tap (part None, '__st__' port: die-level start flop clock pin outside every hard core)
carries none.  Core / partition taps and any part-None tap without the '__st__' name are unchanged."""
import json
import math
from pathlib import Path

import clk_aocv as A
import die_sta_related as R


def _T():
    c = dict(mu_cell_ps=50.0, mu_stage_ps=100.0, cell_share=0.5, s_cell=0.04, rho=[])
    return dict(schema=A.SCHEMA, k_sigma=3.0, classes=dict(A=dict(TT=c, FF=c), B=dict(TT=c, FF=c)),
                systematic=dict(g_per_mm=0.004), droop=dict(one_sided_late_frac=0.0511),
                net_flat=dict(late=1.03, early=0.97))


META = dict(corner="TT", node_stages={"h0": 4, "h": 0}, node_xy_um={"h0": [50, 50], "h": [0, 0]},
            node_late_ps={"h0": 400.0, "h": 0.0}, node_early_ps={"h0": 395.0, "h": 0.0})


def _tap(port, part, late, stages=10, x=0):
    return dict(port=port, part=part, late_ps=late, early_ps=late - 10.0, cppr_node="h0", stages_from_root=stages,
                xy_um=[x, 0])


def _taps():
    return {"c1": _tap("c1", "p0", 1000.0), "c2": _tap("c2", "p1", 1050.0, x=100),
            "__st__h01": _tap("__st__h01", None, 1010.0, x=20), "__st__h02": _tap("__st__h02", None, 1030.0, x=80),
            "glue": _tap("glue", None, 1020.0, x=40)}       # part None but not a START tap (no '__st__' name)


def _fns(tmp_path, taps, lat=450.0, mode="table"):
    t = tmp_path / "t.json"
    t.write_text(json.dumps(dict(clock_aocv=_T())))
    return R.clock_ocv_fn(mode, "shared", META, taps, lat, t), R.clock_ocv_fn(mode, "shared", META, taps, 0.0, t)


def test_predicate():
    tp = _taps()
    assert [k for k, r in tp.items() if R.is_start_virtual_tap(r)] == ["__st__h01", "__st__h02"]
    assert not R.is_start_virtual_tap(dict(port="__st__x", part="p0"))     # a named START tap inside a core keeps it


def test_virtual_virtual_pair_drops_core_latency(tmp_path):
    # (a) the virtual-tap delta: both branches lose core_lat -> exactly the core_lat = 0 pessimism of the old model
    for mode in ("table", "flat"):
        f, f0 = _fns(tmp_path, _taps(), mode=mode)
        for chk in ("setup", "hold"):
            v = f("__st__h01", "__st__h02", chk)
            assert math.isclose(v, f0("__st__h01", "__st__h02", chk))
    f, _ = _fns(tmp_path, _taps())
    tp = _taps()
    for k in ("__st__h01", "__st__h02"):
        tp[k]["port"] = "x" + k             # same geometry, no longer START taps -> old model (core_lat charged)
    fo, _ = _fns(tmp_path, tp)
    for chk in ("setup", "hold"):
        assert fo("__st__h01", "__st__h02", chk) - f("__st__h01", "__st__h02", chk) > 10.0


def test_core_pairs_and_non_start_part_none_unchanged(tmp_path):
    tp = _taps()
    f, _ = _fns(tmp_path, tp)
    # pre-fix reference: the same taps with the START names removed (no tap is virtual)
    ref = {("x" + k if k.startswith("__st__") else k): dict(r, port="x" + r["port"]) if k.startswith("__st__") else r
           for k, r in tp.items()}
    fr, _ = _fns(tmp_path, ref)
    for a, b in (("c1", "c2"), ("c2", "c1"), ("c1", "glue"), ("glue", "c2")):
        for chk in ("setup", "hold"):
            assert f(a, b, chk) == fr(a, b, chk)       # bit-identical float


def test_mixed_pair_keeps_core_side_only(tmp_path):
    # virtual launch -> core capture: the core side keeps core_lat, the virtual side does not -> strictly between
    tp = _taps()
    f, f0 = _fns(tmp_path, tp)
    ref = dict(tp, xs=dict(tp["__st__h01"], port="xs"))
    fr, _ = _fns(tmp_path, ref)
    for chk in ("setup", "hold"):
        new, old, zero = f("__st__h01", "c2", chk), fr("xs", "c2", chk), f0("__st__h01", "c2", chk)
        assert zero < new < old


def test_unmeasured_start_port_stays_fail_closed(tmp_path):
    # 12.19: the fix only changes pessimism numbers; a START port with no measured data delay / no tap still fails
    tp = _taps()
    f, _ = _fns(tmp_path, tp)
    b = dict(regions={"r": dict(sync_values=1)},
             start_ports={"sp0": dict(launch="__st__h01", capture="c2", dst="r", d_lo_ps=0, d_hi_ps=0),
                          "sp1": dict(launch="__st__h01", capture="nope", dst="r", d_lo_ps=0, d_hi_ps=0)})
    rows = {r["port"]: r for r in R.count_align_start_ports(b, tp, None, 833.333, {}, f, data_delay={})}
    assert rows["sp0"]["ok"] is False and "fail closed" in rows["sp0"]["reason"]
    rows = {r["port"]: r for r in R.count_align_start_ports(b, tp, None, 833.333, {}, f)}
    assert rows["sp1"]["ok"] is False and rows["sp1"]["reason"] == "no taps"
