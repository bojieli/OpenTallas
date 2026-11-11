#!/usr/bin/env python3
"""DIE-S81-85 LEPW-EFACE-1111 (VIS-TRIAGE-S81 class F, DO_NOT_COUNT): move the lepk face windows of the S-side LP slice
off its lane core u_bound.u_u_ln3, with the abutted neighbour's W-face windows moved to match.  Positions only,
EQ-gated (no RTL, netlist, pin-count, outline, core-origin or cycle change).

Finding: dsdv_slice_lepw_mus_LP__t2 (s_0S_LP, R0) puts its 2 x 1105-pin E-face buses lepk_i0 [6.144, 246.108] and
lepk_o0 [247.296, 487.26] (M6/M4) beside u_bound.u_u_ln3 (dsfd_coll_lane_w_safe8_ntf, origin 1131.84,129.6, 295.92 x
444.96: OBS full M1-M5 + 19k M6 shapes, only 25 % of its M6 tracks run free across it).  The lep logic those pins
feed sits north of the lane-core row (y 595..1222), so every lepk net has to climb the 10.8-um core strip between
un3 and the E face or hop over un3 on its blocked M6: GRT 463k overflow (M6 291k, M7 128k), 99 % over un3
(kw43-wave-1109n e9eda32d41c attempt_9 5_1_grt).  The mirrored sister dsdv_slice_lepw_mu_LP__t2 (MX: un3 at y
648..1093, lep logic at y 0..630) already has the same windows clear of un3 and next to its logic: NOT touched.

Fix (option (a), one translation): both lepk windows of mus_LP move +590.016 um (= 3073 x 0.192, on the M4/M6 track
lcm) to [596.16, 836.124] / [837.312, 1077.276]: 21.6 um above un3's top edge (574.56), beside free core area (the
E-edge column x >= 1407.9 holds no macro; the tx/rx SRAM rows west of it obstruct M4 only).  Widths, layers and order
are unchanged.  The abutted neighbour s_0S_C (dsdv_slice_lepw_mus_C__t1, the only instance of that type) moves its
matching W-face windows lepk_o0 / lepk_i0 by the same amount, and the two die ports kd_s_0S__0 / ku_s_0S__0 follow
(die window = partition origin y + type window, asserted on BASE).  The small E-face buses (flt_o0, lepf_i0, lpc_i0;
4 pins) and the lpc_i0 internal station are left where they are.

The delta (delta_lepw_eface_1111.json) is {type: {bus: {"window_um": [lo, hi], "layers": [...]}}}; this script
applies it to a plan whose touched keys still hold the BASE (99f40d35071d) values, so DIE-S81-85 can re-apply it on
a later base: it asserts every touched bus still has the BASE window, re-derives the die ports, and asserts that
nothing else in the plan changed.

usage: delta_lepw_eface_1111.py PLAN_IN PLAN_OUT [REPORT.json]
       delta_lepw_eface_1111.py --check PLAN_IN PLAN_OUT"""
import copy
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVENT = "LEPW-EFACE-1111"
DELTA = HERE / "delta_lepw_eface_1111.json"
BASE_SHA = "99f40d35071d66bf2edd2b81f4d7046598f297bbf0b1b3884006252e85172eb9"   # FEED-BAL-2-1111 out2, POR of record
# BASE windows of every touched bus (asserted before the move, so a re-apply on a later base fails loudly if any of
# them moved in between)
OLD = {"dsdv_slice_lepw_mus_LP__t2": {"lepk_i0": ("E", [6.144, 246.108]), "lepk_o0": ("E", [247.296, 487.26])},
       "dsdv_slice_lepw_mus_C__t1": {"lepk_o0": ("W", [6.144, 246.108]), "lepk_i0": ("W", [247.296, 487.26])}}
DY = 590.016
PORTS = {"kd_s_0S__0": ("s_0S_C", "lepk_o0", "s_0S_LP", "lepk_i0"),
         "ku_s_0S__0": ("s_0S_LP", "lepk_o0", "s_0S_C", "lepk_i0")}
EPS = 1e-6


def r6(v):
    return round(v, 6)


def derive(text, strict_base=True):
    if strict_base:
        assert hashlib.sha256(text.encode()).hexdigest() == BASE_SHA, "base is not 99f40d35071d (use --rebase)"
    raw = json.loads(text)
    compact = json.dumps(raw) + "\n" == text
    orig = copy.deepcopy(raw)
    delta = json.loads(DELTA.read_text())
    assert set(delta) == set(OLD), sorted(delta)
    parts = {p["name"]: p for p in raw["partitions"]}
    rep = dict(event=EVENT, DO_NOT_COUNT=True, base_plan_sha256=hashlib.sha256(text.encode()).hexdigest(),
               delta_sha256=hashlib.sha256(DELTA.read_bytes()).hexdigest(), buses={}, ports={})

    # ---- type buses
    for tn, buses in delta.items():
        t = raw["partition_types"][tn]
        by = {b["name"]: b for b in t["buses"]}
        h = t["outline_um"][1]
        for bn, d in buses.items():
            b = by[bn]
            face, old = OLD[tn][bn]
            assert b["face"] == face and [r6(v) for v in b["window_um"]] == old, (tn, bn, b["face"], b["window_um"])
            assert d["layers"] == b["layers"], (tn, bn, "layers must not change")
            new = [r6(v) for v in d["window_um"]]
            assert all(abs(n - o - DY) < EPS for n, o in zip(new, old)), (tn, bn, "not the planned translation")
            assert 0 <= new[0] < new[1] <= h, (tn, bn, new)
            # no overlap with any other window on the same face (buses + ft slots)
            for o in t["buses"]:
                if o is not b and o["face"] == face:
                    lo, hi = o["window_um"] if o["name"] not in buses else buses[o["name"]]["window_um"]
                    assert hi <= new[0] + EPS or lo >= new[1] - EPS, (tn, bn, "overlaps", o["name"])
            for s in t.get("ft_slots", []):
                for fk, wk in (("in_face", "in_window_um"), ("out_face", "out_window_um")):
                    if s.get(fk) == face:
                        lo, hi = s[wk]
                        assert hi <= new[0] + EPS or lo >= new[1] - EPS, (tn, bn, "overlaps ft", s["name"])
            b["window_um"] = new
            rep["buses"][f"{tn}.{bn}"] = dict(face=face, old=old, new=new, layers=b["layers"], width=b["width"])
    # mus_C has one instance, mus_LP has one instance: a type edit moves exactly the two abutted faces
    for tn in delta:
        assert [p for p in parts if parts[p]["type"] == tn] in (["s_0S_LP"], ["s_0S_C"]), tn

    # ---- die ports: window = partition origin y + type window (R0 instances, E/W faces), asserted on BASE first
    tw = {(q, bn): raw["partition_types"][parts[q]["type"]] for q in ("s_0S_LP", "s_0S_C") for bn in ("lepk_i0", "lepk_o0")}
    for pid, (sp, sb, dp, db) in PORTS.items():
        pr = next(p for p in raw["ports"] if p["id"] == pid)
        assert (pr["src"], pr["dst"]) == ({"part": sp, "bus": sb}, {"part": dp, "bus": db}), pid
        for q in (sp, dp):
            assert parts[q]["orient"] == "R0", q
        oy_s, oy_d = parts[sp]["origin_um"][1], parts[dp]["origin_um"][1]
        assert abs(oy_s - oy_d) < EPS, (pid, "ends not side by side")
        old_t = OLD[parts[sp]["type"]][sb][1]
        assert [r6(v) for v in pr["window_um"]] == [r6(oy_s + v) for v in old_t], (pid, pr["window_um"])
        ws = next(b["window_um"] for b in tw[(sp, sb)]["buses"] if b["name"] == sb)
        wd = next(b["window_um"] for b in tw[(dp, db)]["buses"] if b["name"] == db)
        assert ws == wd, (pid, "src/dst type windows differ", ws, wd)
        new = [r6(oy_s + v) for v in ws]
        rep["ports"][pid] = dict(old=pr["window_um"], new=new)
        pr["window_um"] = new
    # abutment: the two parts really share the LP E / C W edge
    lp, c = parts["s_0S_LP"], parts["s_0S_C"]
    assert abs(lp["origin_um"][0] + raw["partition_types"][lp["type"]]["outline_um"][0] - c["origin_um"][0]) < EPS

    out_text = json.dumps(raw) + "\n" if compact else json.dumps(raw)
    # ---- EQ gate: only partition_types.<2 types>.buses[<2 each>].window_um and ports[<2>].window_um differ
    for k in raw:
        if k not in ("partition_types", "ports"):
            assert raw[k] == orig[k], k
    for tn in raw["partition_types"]:
        if tn not in delta:
            assert raw["partition_types"][tn] == orig["partition_types"][tn], tn
            continue
        for k in raw["partition_types"][tn]:
            if k != "buses":
                assert raw["partition_types"][tn][k] == orig["partition_types"][tn][k], (tn, k)
        for b, o in zip(raw["partition_types"][tn]["buses"], orig["partition_types"][tn]["buses"]):
            if b["name"] in delta[tn]:
                assert {k: v for k, v in b.items() if k != "window_um"} == {k: v for k, v in o.items() if k != "window_um"}
            else:
                assert b == o, (tn, b["name"])
    assert len(raw["ports"]) == len(orig["ports"])
    for p, o in zip(raw["ports"], orig["ports"]):
        if p["id"] in PORTS:
            assert {k: v for k, v in p.items() if k != "window_um"} == {k: v for k, v in o.items() if k != "window_um"}
        else:
            assert p == o, p["id"]
    rep["eq_gate"] = dict(rtl_change=False, netlist_change=False, pin_count_change=False, outline_change=False,
                          core_origin_change=False, cycle_change=False, lane_change=False,
                          changed_paths=[f"partition_types.{k} window_um" for k in rep["buses"]] +
                                        [f"ports.{k} window_um" for k in rep["ports"]])
    return out_text, rep


def main():
    a = sys.argv[1:]
    strict = "--rebase" not in a
    a = [x for x in a if x != "--rebase"]
    if a[0] == "--check":
        text, _ = derive(open(a[1]).read(), strict)
        assert open(a[2]).read() == text, "output differs from re-derivation"
        print("CHECK PASS", hashlib.sha256(text.encode()).hexdigest())
        return
    text, rep = derive(open(a[0]).read(), strict)
    open(a[1], "w").write(text)
    rep["output_plan_sha256"] = hashlib.sha256(text.encode()).hexdigest()
    if len(a) > 2:
        Path(a[2]).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(dict(out=rep["output_plan_sha256"], buses=len(rep["buses"]), ports=rep["ports"])))


if __name__ == "__main__":
    main()
