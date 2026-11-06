#!/usr/bin/env python3
"""QC SU-l1 conservative form: harden six existing forwarded-clock landing rings.

Two SU-l1 classes failed GRT with123k/133k overflow. Each exact existing ring becomes
one small registered-face child in its original face band; parent geometry and pins stay
fixed. This reuses the QC-SLECTL splitter, pin planner and proven parameter wrapper.
No data-cycle change. Re-solving the reset collector may add boot cycles; report these separately.
Children remain UNSIGNED until their own kit signs off.
Usage: delta_sul1_ring_split_1106.py PLAN_IN PLAN_OUT [REPORT [SIDECAR_IN SIDECAR_OUT]].
"""
import copy
import hashlib
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "tools" / "die_plan"))
sys.path.insert(0, str(HERE / "cores"))
import schema as S  # noqa: E402
import reset_tree as RT  # noqa: E402
import gen_phys as G  # noqa: E402
import sle_ctl_pins as SP  # noqa: E402

ID = "QC-SUL1/RING-SPLIT-1106"
TYPES = ("slw_su_l1__clcc9d0155", "slw_su_l1__cla2a78701")
P5 = {"DEPTH": 4, "WFALL": 1, "WREG": 1, "DSREP": 1}
BASE = "ot_dp_clk_landing_cas"
# band, W, face of the d pins (= the face its parent pins enter)

TOFF = [0.012, 0.012]
TT, FF = 250.0, 202.5
G4 = 0.432


def snap_in(r):
    x0, y0 = math.ceil(r[0] / G4 - 1e-6) * G4, math.ceil(r[1] / G4 - 1e-6) * G4
    x1, y1 = math.floor(r[2] / G4 + 1e-6) * G4, math.floor(r[3] / G4 + 1e-6) * G4
    return [round(x0, 3), round(y0, 3)], [round(x1 - x0, 3), round(y1 - y0, 3)]


def ring_cells(W):
    import cells as C
    return C.ring_cells(W - 1)


def ring_order(P, tn, band, face):
    pins = [(b, x, y) for n, b, _l, x, y, f in G.type_pins(P, tn) if n == band]
    pins.sort(key=lambda r: (r[2] if face in "WE" else r[1], r[0]))
    return [b for b, _x, _y in pins]


def main():
    pin, pout = sys.argv[1:3]
    rep_p = sys.argv[3] if len(sys.argv) > 3 else None
    text = open(pin).read()
    P0 = json.loads(text)
    seps = next((sp for sp in ((", ", ": "), (",", ":")) if json.dumps(P0, separators=sp) + "\n" == text), None)
    assert seps, "plan text style is not one-line json.dumps"
    P = copy.deepcopy(P0)
    SP0 = S.Plan(P0, pin)
    odir = Path(pout).resolve().parent
    masters, rep = {}, dict(event=ID, types={}, added_cycles=0)
    for tn in TYPES:
        t = P["partition_types"][tn]
        tree0 = RT.for_type(SP0, tn)
        assert len(t["hard_cores"]) == 4 and t["clock"]["core_taps"] == "early", tn
        bands = t["clock"]["landing_contract"]["bands"]
        hcs, taps = [], []
        rings = []
        for band in t["clock"]["landing_ring_wreg"]["buses"]:
            pins = [(bit, face) for name, bit, _l, _x, _y, face in G.type_pins(SP0, tn) if name == band]
            faces = {f for _, f in pins}
            assert len(faces) == 1 and pins, (tn, band, faces)
            rings.append((band, len(pins), faces.pop()))
        assert len(rings) == 6, (tn, rings)
        for band, W, face in rings:
            b = bands[band]
            assert b["instance"] == f"u_cland_{band}" and b.get("ring_place") == "ff", (tn, band)
            org, outl = snap_in(b["rect_um"])
            # Registered child faces need space for data plus clock/reset/status/strap pins.
            # Existing soft-bank bands did not reserve the child's opposite face.
            axis = 1 if face in "WE" else 0
            minimum = math.ceil(((W + 16) * 0.096 + 4.32) / G4) * G4
            if outl[axis] < minimum:
                outl[axis] = round(minimum, 3)
                b["rect_um"][axis + 2] = round(org[axis] + minimum, 3)
                b["hardening_face_expansion"] = "reserve >=0.096um registered face pin pitch"
            order = ring_order(SP0, tn, band, face)
            assert len(order) == W, (tn, band, len(order), W)
            key = (W, face, tuple(outl), tuple(order))
            if key not in masters:
                k = sum(1 for m in masters.values() if m["W"] == W and m["face"] == face)
                name = f"sle_cland_w{W}_{face.lower()}_{100+k}"
                tbl = SP.ring_pins(name, W, face, outl, order)
                masters[key] = dict(name=name, W=W, face=face, outline=outl, table=tbl,
                                    pins_file=f"cores/sul1_ring/{name}_pins.json")
            m = masters[key]
            inst = f"cl_{band}"
            ck = next(p for p in m["table"]["pins"] if p["name"] == "clk")
            hcs.append(dict(inst=inst, module=m["name"], origin_um=org, outline_um=list(outl), orient="R0",
                            track_offset_um=list(TOFF), pins_file=m["pins_file"], physical_inst=f"u_bound.u_cland_{band}",
                            physical_master=m["name"], param_wrap=dict(base=BASE, params=dict(W=W, **P5)),
                            reset_net="cland_start", cells=ring_cells(W),
                            cells_basis="cells.ring_cells (LAND-KV-1 measured ring model)",
                            note=f"{ID}: landing ring u_cland_{band} as a hard child on its band; registered faces by "
                                 f"construction; 0 added cycles; UNSIGNED until its kit signs off"))
            taps.append(dict(name=f"{inst}.clk", kind="core",
                             xy=[round(org[0] + ck["x"] + TOFF[0], 3), round(org[1] + ck["y"] + TOFF[1], 3)],
                             insertion_ps=TT, insertion_ff_ps=FF,
                             budget_owner=f"{ID}: target 250/202.5 ESTIMATE, re-measure from the child's own kit"))
            b["hard_core"] = inst
        for h in hcs:
            assert h["origin_um"][0] >= 0 and h["origin_um"][1] >= 0
            assert h["origin_um"][0] + h["outline_um"][0] <= t["outline_um"][0]
            assert h["origin_um"][1] + h["outline_um"][1] <= t["outline_um"][1]
        t["hard_cores"] += hcs
        t["clock"]["core_taps"] = "early"
        t["clock"]["taps"] += taps
        tree1 = RT.for_type(S.Plan(P, pout), tn)
        moved = json.dumps(tree1, sort_keys=True) != json.dumps(tree0, sort_keys=True)
        if moved:
            assert RT.consumer_count(tree1) == RT.consumer_count(tree0), "consumer count moved"
            t["clock"]["landing_contract"]["collector_tree"] = json.loads(json.dumps(tree1))
        rep["types"][tn] = dict(reset_tree_moved=moved, hard_cores_added=len(hcs),
                                reset_depth_before=tree0["depth"], reset_depth_after=tree1["depth"],
                                boot_cycles_added=tree1["depth"]-tree0["depth"])
    for tn in P["partition_types"]:
        if tn not in TYPES:
            assert P["partition_types"][tn] == P0["partition_types"][tn]
    assert {k: v for k, v in P.items() if k != "partition_types"} == {k: v for k, v in P0.items() if k != "partition_types"}
    for m in masters.values():
        f = odir / m["pins_file"]
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(m["table"], indent=1) + "\n")
    out = json.dumps(P, separators=seps) + "\n"
    open(pout, "w").write(out)
    rep.update(masters=sorted(m["name"] for m in masters.values()),
               src_sha256=hashlib.sha256(text.encode()).hexdigest(), dst_sha256=hashlib.sha256(out.encode()).hexdigest())
    if len(sys.argv) > 5:
        stext = open(sys.argv[4]).read()
        side = json.loads(stext)
        sst = next((k for k in (1, None) if json.dumps(side, indent=k) + "\n" == stext), 1)
        ch = False
        for tn in TYPES:
            if rep["types"][tn]["reset_tree_moved"]:
                side["collector"]["types"][tn]["tree"] = copy.deepcopy(
                    P["partition_types"][tn]["clock"]["landing_contract"]["collector_tree"])
                ch = True
        open(sys.argv[5], "w").write(json.dumps(side, indent=sst) + "\n")
        rep["sidecar_changed"] = ch
    if rep_p:
        open(rep_p, "w").write(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(dict(masters=rep["masters"], types=rep["types"])))


if __name__ == "__main__":
    main()
