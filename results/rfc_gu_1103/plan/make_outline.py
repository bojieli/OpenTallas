#!/usr/bin/env python3
"""S81-RF1 RE-FORM core outline event (DIE-S81-51/RF-C/gu 11-03): a plan COPY of plan_h2_2249.json with new hard-core
outlines for the gunit family (PLAN folds it into the S81-RF1 plan event; plan_h2_2249.json itself is not edited).

Per core: new outline W x H; every pin keeps its name, layer and face.  N/S face pins keep their order along x, scaled
by W_new / W_old, snapped to the M5 pin grid (0.108 + 0.048 k) and spread to >= 0.192 um pitch; E/W face pins keep y
(clamped into the new height, same pitch rule); the N face moves to y = H - 0.042, the E face to x = W - 0.042;
an interior (face C) clock entry moves to the new centre on its M5 track.  The plan LEF is rewritten with the new SIZE,
each PIN rect translated with its pin, and a plan-abstract OBS (M1-M3 full outline).
    python3 make_outline.py <repo> <out plan json>     (writes the pins / LEF files under the repo)
"""
import json
import math
import re
import sys
from pathlib import Path

CORES = {  # module: (new outline, note)
    "dsdv_gunit_l4": ((302.4, 108.0), "RF-1: was 345.6x64.8 (aspect 5.3, fill 0.57); aspect 2.8, fill ~0.37-0.40"),
}
PITCH = 0.192
GX0, GXS = 0.108, 0.048          # N/S face pin grid (M5)
GY0, GYS = 0.036, 0.048          # E/W face pin grid (M4)


def snap(v, g0, gs):
    return g0 + round((v - g0) / gs) * gs


def spread(vals, lo, hi, g0, gs):
    """keep order; snap; enforce PITCH within [lo, hi] (forward then backward pass)."""
    out = []
    for v in vals:
        x = max(snap(v, g0, gs), lo)
        if out and x < out[-1] + PITCH - 1e-6:
            x = out[-1] + math.ceil((PITCH - 1e-6) / gs) * gs
        out.append(x)
    for i in range(len(out) - 1, -1, -1):
        cap = hi if i == len(out) - 1 else out[i + 1] - math.ceil((PITCH - 1e-6) / gs) * gs
        if out[i] > cap + 1e-6:
            out[i] = snap(cap - gs / 2 + 1e-9, g0, gs) if snap(cap, g0, gs) > cap + 1e-6 else snap(cap, g0, gs)
    assert out[0] >= lo - 1e-6, "face overflow"
    assert all(b - a >= PITCH - 1e-6 for a, b in zip(out, out[1:]))
    return out


def face(p, W, H):
    x, y = p["x"], p["y"]
    return "W" if x < 1 else "E" if x > W - 1 else "S" if y < 1 else "N" if y > H - 1 else "C"


def main():
    repo, outp = Path(sys.argv[1]), Path(sys.argv[2])
    s81 = repo / "physical/die_plan/s81"
    plan = json.loads((s81 / "plan_h2_2249.json").read_text())
    pt = plan["partition_types"]["gunit__t1"]
    rec = []
    for hc in pt["hard_cores"]:
        m = hc["module"]
        if m not in CORES:
            continue
        (W, H), note = CORES[m]
        W0, H0 = hc["outline_um"]
        pj = json.loads((s81 / hc["pins_file"]).read_text())
        pins = pj["pins"]
        F = {}
        for p in pins:
            F.setdefault(face(p, W0, H0), []).append(p)
        new = {}
        for f, ps in F.items():
            if f in "NS":
                ps.sort(key=lambda p: p["x"])
                xs = spread([p["x"] * W / W0 for p in ps], 0.5, W - 0.5, GX0, GXS)
                for p, x in zip(ps, xs):
                    new[p["name"]] = (p["layer"], round(x, 3), round(0.042 if f == "S" else H - 0.042, 3))
            elif f in "EW":
                ps.sort(key=lambda p: p["y"])
                ys = spread([min(p["y"], H - 0.5) for p in ps], 0.5, H - 0.5, GY0, GYS)
                for p, y in zip(ps, ys):
                    xx = p["x"] if f == "W" else round(W - (W0 - p["x"]), 3)
                    new[p["name"]] = (p["layer"], xx, round(y, 3))
            else:   # face C clock entry: new centre on its M5 track (0.012 + 0.048 k), y on the 0.048 grid
                for p in ps:
                    new[p["name"]] = (p["layer"], round(snap(W / 2, 0.012, 0.048), 3), round(snap(H / 2, 0.012, 0.048), 3))
        npins = [dict(p, x=new[p["name"]][1], y=new[p["name"]][2]) for p in pins]
        rel_pins = f"inputs/core_pins/rfc_1103/{m}.json"
        rel_lef = f"physical/die_plan/s81/cores/legacy/lef/rfc_1103/{m}.lef"
        nj = dict(pj, lef=rel_lef, pins=npins,
                  source=pj.get("source", "") + f"; S81-RF1 RE-FORM outline {W0}x{H0} -> {W}x{H} (results/rfc_gu_1103/plan/make_outline.py)")
        (s81 / rel_pins).parent.mkdir(parents=True, exist_ok=True)
        (s81 / rel_pins).write_text(json.dumps(nj, indent=1) + "\n")
        # LEF: SIZE, PIN rects translated with their pin centre, plan-abstract OBS
        lt = (repo / hc["lef"]).read_text()
        old = {p["name"]: (p["x"], p["y"]) for p in pins}
        def pin_blk(mo):
            name = mo.group(1)
            if name not in new:
                return mo.group(0)
            dx, dy = new[name][1] - old[name][0], new[name][2] - old[name][1]
            def rr(r):
                a = [float(v) for v in r.group(1).split()]
                return "RECT %.3f %.3f %.3f %.3f ;" % (a[0] + dx, a[1] + dy, a[2] + dx, a[3] + dy)
            return re.sub(r"RECT\s+([-\d.\s]+?)\s*;", rr, mo.group(0))
        lt = re.sub(r"  PIN (\S+)\n.*?  END \1\n", pin_blk, lt, flags=re.S)
        lt = re.sub(r"SIZE [\d.]+ BY [\d.]+ ;", f"SIZE {W} BY {H} ;", lt)
        obs = "  OBS\n" + "".join(f"    LAYER {L} ;\n     RECT  0 0 {W} {H} ;\n" for L in ("M1", "M2", "M3")) + "  END\n"
        lt = re.sub(r"(  # [^\n]*\n)*  OBS\n.*?  END\n(?=END " + m + ")", obs, lt, flags=re.S)
        (repo / rel_lef).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel_lef).write_text(lt)
        rec.append(dict(module=m, outline_old=[W0, H0], outline_new=[W, H], pins=len(pins), note=note,
                        faces={f: len(v) for f, v in F.items()}, pins_file=rel_pins, lef=rel_lef))
        hc.update(outline_um=[W, H], pins_file=rel_pins, lef=rel_lef)
        hc["note"] = (hc.get("note", "") + " | " + note).strip(" |")
    outp.write_text(json.dumps(plan, indent=1) + "\n")
    print(json.dumps(rec, indent=1))


if __name__ == "__main__":
    main()
