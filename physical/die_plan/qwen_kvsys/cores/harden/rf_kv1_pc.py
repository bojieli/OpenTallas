#!/usr/bin/env python3
"""DIE-KV-64/RF-B 11-03 (OWNER TWO-STRIKES -> RE-FORM, batch RF-KV1, CLOSURE rows KV-042/KV-043): right-size form of the
KV PC core family (qkd_kvs_pc r27 + fMX_r27 pin tables, qkd_kvs_pc_h_head_p fMY_r25).

Cause of the strikes (all four routed DBs, same structure): fill 0.21-0.23 in the 397.44 x 362.88 slot (226k std cells,
31.0k um2) -> the bank-scheduler issue loop (u_sched.u_ctl.core.on: wq_v/open/sb_oh -> bank[*].rtp/ras/wrr,
col_context, 16 logic levels + fanout-64 nets) is spread over the whole slot and carries 4-6 wire/placement buffers
(~200 ps of the 814 ps data path) -> TT -8..-57 ps, DRV slew on the long nets.

Form: the SAME logic, faces and pin order in a slot right-sized to fill ~0.40 (target band 0.35-0.45):
  outline 293.76 x 267.84 um (68 x 62 x 4.32; aspect 1.10), core area 73.9k um2 -> 31.0k/73.9k = 0.42 routed.
  Pins: every face pin stays on its face in the same order; the coordinate is mapped proportionally over the face
  (2.16 um corner keep-out), snapped to the symmetric plan tracks (pitch 0.048, offset 0.024, every orient on track),
  min spacing 2 tracks.  Interior ports (ck/rst_n centre entry, clock-island ft pairs) keep their offset from the
  slot centre / scale with the slot; island rects snap to the site (0.054) / row (0.27) grid.
  Plan slot: the M4 (W) face keeps its x line in the parent (R0/MX: origin x unchanged; MY/R180: x += 103.68), the
  slot is centred in y (y += 47.52); clock taps move with the ck pin.

    rf_kv1_pc.py PLAN OUT_PLAN DELTA_JSON
writes <pins>_rf1.json next to each source pins file, OUT_PLAN (derived plan for the core kits only; plan_c is not
edited -- DIE-KV-64 folds DELTA_JSON into the RF-KV1 plan event).
"""
import copy
import json
import math
import sys
from pathlib import Path

NW, NH = 293.76, 267.84
OW, OH = 397.44, 362.88
PITCH, OFFS, KEEP, EDGE = 0.048, 0.024, 2.16, 0.096
MODULES = ("qkd_kvs_pc", "qkd_kvs_pc_h_head_p")


def snap_track(c):
    return round(OFFS + round((c - OFFS) / PITCH) * PITCH, 3)


def face_of(p, w, h):
    x, y = p["x"], p["y"]
    if abs(y - (h - EDGE)) < 1e-6:
        return "N"
    if abs(y - EDGE) < 1e-6:
        return "S"
    if abs(x - (w - EDGE)) < 1e-6:
        return "E"
    if abs(x - EDGE) < 1e-6:
        return "W"
    return "I"


def spread(coords, lold, lnew):
    """proportional map + track snap + min 2-track spacing, order kept; coords sorted ascending"""
    lo_i = math.ceil((KEEP - OFFS) / PITCH)
    hi_i = math.floor((lnew - KEEP - OFFS) / PITCH)
    s = (lnew - 2 * KEEP) / (lold - 2 * KEEP)
    idx = [round((KEEP + (c - KEEP) * s - OFFS) / PITCH) for c in coords]
    for k in range(len(idx)):
        idx[k] = max(idx[k], lo_i if k == 0 else idx[k - 1] + 2)
    for k in range(len(idx) - 1, -1, -1):
        idx[k] = min(idx[k], hi_i if k == len(idx) - 1 else idx[k + 1] - 2)
    assert idx[0] >= lo_i and all(b - a >= 2 for a, b in zip(idx, idx[1:])), "face over capacity"
    return [round(OFFS + i * PITCH, 3) for i in idx]


def resize_pins(src, dst):
    d = json.load(open(src))
    assert f"outline {OW:g} x {OH:g}" in d["frame"], d["frame"]
    pins = copy.deepcopy(d["pins"])
    faces = {}
    for p in pins:
        faces.setdefault(face_of(p, OW, OH), []).append(p)
    for f, grp in faces.items():
        if f == "I":
            continue
        along = "x" if f in "NS" else "y"
        grp.sort(key=lambda p: p[along])
        new = spread([p[along] for p in grp], OW if f in "NS" else OH, NW if f in "NS" else NH)
        for p, c in zip(grp, new):
            p[along] = c
            if f == "N":
                p["y"] = round(NH - EDGE, 3)
            elif f == "E":
                p["x"] = round(NW - EDGE, 3)
    # interior ports: island ft rects scale with the slot (site/row grid); ft pins keep their offset to the rect;
    # other interior pins (ck/rst_n centre entry) keep their offset to the slot centre
    isl = copy.deepcopy(d.get("island_ft"))
    rect_of = {}
    for a in (isl or {}).get("arcs", []):
        x0, y0, x1, y1 = a["rect_um"]
        nx0 = round(round(x0 * NW / OW / 0.054) * 0.054, 3)
        ny0 = round(round(y0 * NH / OH / 0.27) * 0.27, 3)
        a["rect_um"] = [nx0, ny0, round(nx0 + (x1 - x0), 3), round(ny0 + (y1 - y0), 3)]
        rect_of[a["source"]] = rect_of[a["sink"]] = ((x0, y0), (nx0, ny0))
    for p in faces.get("I", []):
        if p["name"] in rect_of:
            (x0, y0), (nx0, ny0) = rect_of[p["name"]]
            p["x"] = snap_track(nx0 + (p["x"] - x0))
            p["y"] = round(ny0 + (p["y"] - y0), 3)
        else:
            p["x"] = snap_track(NW / 2 + (p["x"] - OW / 2))
            p["y"] = round(NH / 2 + (p["y"] - OH / 2), 3)
    out = dict(d)
    out["frame"] = f"core R0, origin (0,0), outline {NW:g} x {NH:g}"
    out["source"] = d["source"] + (f" | RF-KV1 DIE-KV-64/RF-B 11-03: right-size re-form {OW:g} x {OH:g} -> {NW:g} x {NH:g} "
                                   "(rf_kv1_pc.py: same faces/order, proportional + track snap)")
    out["pins"] = pins
    if isl is not None:
        out["island_ft"] = isl
    Path(dst).write_text(json.dumps(out, indent=0))
    return {f: len(g) for f, g in faces.items()}


def place(orient, ox, oy, x, y, w, h, tro):
    X = {"R0": x, "MX": x, "MY": w - x, "R180": w - x}[orient]
    Y = {"R0": y, "MY": y, "MX": h - y, "R180": h - y}[orient]
    return [round(ox + X + tro[0], 3), round(oy + Y + tro[1], 3)]


def main(plan_path, out_plan, delta_path):
    plan = json.load(open(plan_path))
    pdir = Path(plan_path).resolve().parent
    done, delta = {}, dict(schema="opentallas.kv.rf_kv1_delta.v1", lane="DIE-KV-64/RF-B", form="right-size PC family",
                           outline_old=[OW, OH], outline_new=[NW, NH], pins_files={}, hard_cores=[], clock_taps=[])
    for t, v in plan["partition_types"].items():
        for c in v.get("hard_cores") or []:
            if c.get("module") not in MODULES:
                continue
            assert c["outline_um"] == [OW, OH], (t, c["inst"], c["outline_um"])
            pf = c["pins_file"]
            nf = pf[:-5] + "_rf1.json"
            if pf not in done:
                done[pf] = resize_pins(pdir / pf, pdir / nf)
                delta["pins_files"][pf] = dict(new=nf, faces=done[pf])
            src = json.load(open(pdir / pf))
            ck_old = next(p for p in src["pins"] if p["name"] == "ck[0]")
            ck_new = next(p for p in json.load(open(pdir / nf))["pins"] if p["name"] == "ck[0]")
            ox, oy = c["origin_um"]
            nox = ox + (OW - NW if c["orient"] in ("MY", "R180") else 0.0)
            noy = oy + (OH - NH) / 2
            tro = c.get("track_offset_um") or [0.0, 0.0]
            old_tap = place(c["orient"], ox, oy, ck_old["x"], ck_old["y"], OW, OH, tro)
            new_tap = place(c["orient"], nox, noy, ck_new["x"], ck_new["y"], NW, NH, tro)
            delta["hard_cores"].append(dict(type=t, inst=c["inst"], module=c["module"], orient=c["orient"],
                                            origin_old=[ox, oy], origin_new=[round(nox, 3), round(noy, 3)],
                                            outline_new=[NW, NH], pins_file_new=nf))
            c["origin_um"] = [round(nox, 3), round(noy, 3)]
            c["outline_um"] = [NW, NH]
            c["pins_file"] = nf
            c["note"] = (c.get("note") or "") + " | RF-KV1 right-size (DIE-KV-64/RF-B 11-03, derived plan)"
            for tap in (v.get("clock") or {}).get("taps") or []:
                if tap.get("name") == f"{c['inst']}.ck[0]" and [round(a, 3) for a in tap["xy"]] == old_tap:
                    delta["clock_taps"].append(dict(type=t, name=tap["name"], xy_old=tap["xy"], xy_new=new_tap))
                    tap["xy"] = new_tap
    Path(out_plan).write_text(json.dumps(plan, indent=1))
    Path(delta_path).write_text(json.dumps(delta, indent=1))
    print(f"RF_KV1_PC pins {len(done)} hard_cores {len(delta['hard_cores'])} taps {len(delta['clock_taps'])}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
