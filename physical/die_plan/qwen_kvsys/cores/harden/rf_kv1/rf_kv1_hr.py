#!/usr/bin/env python3
"""DIE-KV-64/RF-C 11-03 (RE-FORM batch RF-KV1, OWNER TWO-STRIKES): right-sized HR core slots + face-ordered pin tables.

    python3 rf_kv1_hr.py pins --plan PLAN --spec rf_kv1_hr.json --out-plan DERIVED_PLAN.json

spec = {module: {"outline_um": [W, H]}}.  For each planned hard core slot of the module the pin table is re-mapped onto
the new outline: every pin stays on its face, layer and order; its along-face coordinate is scaled by newspan/oldspan
and snapped to the die symmetric track (offset pitch/2, M4/M5 0.048), keeping at least min(2, original gap) tracks between
neighbours; interior pins (the centre clock entry) scale to the new centre track.  The derived plan (outline + pins_file
replaced) is for kit generation only; the plan of record changes only through the DIE-KV-64 RF-KV1 plan event.
"""
import argparse, copy, json, os
from pathlib import Path

PITCH = dict(M4=0.048, M5=0.048, M6=0.064, M7=0.064, M3=0.036)
OFFS = dict(M4=0.024, M5=0.024, M6=0.032, M7=0.032, M3=0.009)
EDGE = 0.096


def face(p, w, h):
    if abs(p["y"] - EDGE) < 1e-6: return "S"
    if abs(p["y"] - (h - EDGE)) < 1e-6: return "N"
    if abs(p["x"] - EDGE) < 1e-6: return "W"
    if abs(p["x"] - (w - EDGE)) < 1e-6: return "E"
    return "I"


def remap(doc, ow, oh, nw, nh):
    pins = doc["pins"]
    out = {id(p): dict(p) for p in pins}
    by = {}
    for p in pins:
        by.setdefault(face(p, ow, oh), []).append(p)
    for f, ps in by.items():
        if f == "I":
            for p in ps:
                q = out[id(p)]
                for ax, o, n in (("x", ow, nw), ("y", oh, nh)):
                    pt, of = PITCH[p["layer"]], OFFS[p["layer"]]
                    q[ax] = round(of + round((p[ax] * n / o - of) / pt) * pt, 6)
            continue
        ax = "x" if f in "NS" else "y"
        o, n = (ow, nw) if ax == "x" else (oh, nh)
        lay = {p["layer"] for p in ps}
        assert len(lay) == 1, (f, lay)
        pt, of = PITCH[lay.pop()], OFFS[ps[0]["layer"]]
        ps = sorted(ps, key=lambda p: p[ax])
        kmax = int((n - EDGE - of) / pt)
        prev, prev_old = None, None
        ks = []
        for p in ps:
            k = round((p[ax] * n / o - of) / pt)
            if prev is not None:
                og = round((p[ax] - prev_old) / pt)
                k = max(k, prev + max(1, min(2, og)))
            ks.append(k); prev, prev_old = k, p[ax]
        over = ks[-1] - kmax
        if over > 0:   # shift back from the far end, keeping the gaps
            for i in range(len(ks) - 1, -1, -1):
                lim = kmax if i == len(ks) - 1 else ks[i + 1] - 1
                ks[i] = min(ks[i], lim)
        assert ks[0] * pt + of >= EDGE - 1e-9 or ks[0] >= 0, f
        for p, k in zip(ps, ks):
            out[id(p)][ax] = round(of + k * pt, 6)
            perp = "y" if ax == "x" else "x"
            out[id(p)][perp] = {"S": EDGE, "N": round(nh - EDGE, 6), "W": EDGE, "E": round(nw - EDGE, 6)}[f]
    nd = copy.deepcopy(doc)
    nd["pins"] = [out[id(p)] for p in pins]
    nd["frame"] = f"core R0, origin (0,0), outline {nw} x {nh}"
    nd["source"] = (f"RF-KV1 (DIE-KV-64/RF-C 11-03) right-sized slot {ow} x {oh} -> {nw} x {nh}: same faces/layers/order, "
                    f"along-face scaled + track-snapped (rf_kv1_hr.py) | was: " + str(doc.get("source", ""))[:400])
    names = [p["name"] for p in nd["pins"]]
    assert len(set((p["layer"], p["x"], p["y"]) for p in nd["pins"])) == len(names), "pin overlap"
    return nd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["pins"])
    ap.add_argument("--plan", required=True)
    ap.add_argument("--spec", required=True)
    ap.add_argument("--out-plan", required=True)
    ap.add_argument("--pins-dir", required=True, help="repo dir for the new pin tables")
    a = ap.parse_args()
    plan = json.load(open(a.plan)); spec = json.load(open(a.spec))
    pdir = Path(a.plan).resolve().parent
    odir = Path(a.out_plan).resolve().parent
    delta = {}
    for t, v in plan["partition_types"].items():
        for c in (v.get("hard_cores") or []) if isinstance(v, dict) else []:
            m = c.get("module")
            if m not in spec: continue
            ow, oh = c["outline_um"]; nw, nh = spec[m]["outline_um"]
            doc = json.load(open(pdir / c["pins_file"]))
            nd = remap(doc, ow, oh, nw, nh)
            pf = Path(a.pins_dir) / f"{m}_pins_rfkv1.json"
            pf.parent.mkdir(parents=True, exist_ok=True)
            pf.write_text(json.dumps(nd, indent=1) + "\n")
            old_pf = c["pins_file"]
            c["outline_um"] = [nw, nh]
            c["pins_file"] = os.path.relpath(pf.resolve(), odir)
            c["note"] = (c.get("note", "") + f" | RF-KV1 RE-FORM (DIE-KV-64/RF-C 11-03): outline {ow}x{oh} -> {nw}x{nh}")
            delta[f"{t}.{c['inst']}"] = dict(module=m, origin_um=c["origin_um"], outline_old=[ow, oh], outline_new=[nw, nh],
                                            pins_old=old_pf, pins_new=str(pf), pins=len(nd["pins"]),
                                            area_old_um2=round(ow * oh, 2), area_new_um2=round(nw * nh, 2))
    Path(a.out_plan).write_text(json.dumps(plan) + "\n")
    print(json.dumps(delta, indent=1))


if __name__ == "__main__":
    main()
