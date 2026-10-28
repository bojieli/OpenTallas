#!/usr/bin/env python3
"""HBM-R16/C17: apply joint.py solutions IN PLACE on a C17 work copy (refuses the C16r basis dir).
For each selected master: set the chosen orient per instance (die_plan hard_cores[].orient; type clock taps of the
core mirrored about the core centre with it) and move each chosen port group to its new core face with the
apply_hubpin legality (W/E M4, N/S M5, 0.048 pitch / 0.024 offset / 0.019 inset, >= 8.64 um from corners, no shared
track, destination face <= 5.5 pins/um = pin6 capacity). usage: apply_joint.py PLANDIR joint.json REPORT.json [master-substr ...]"""
import sys, json, re, math, collections, hashlib
from pathlib import Path
pd = Path(sys.argv[1]).resolve()
assert "hbm-r15-1027" not in str(pd), "never write the C16r basis"
J = json.load(open(sys.argv[2])); outp = sys.argv[3]; sel = sys.argv[4:]
PITCH, OFF, INSET, END, CAP = 0.048, 0.024, 0.019, 8.64, 5.5
LAYER = dict(W="M4", E="M4", N="M5", S="M5")
raw = json.loads((pd / "die_plan.json").read_text()); T = raw["partition_types"]
def pname(p): return p.get("name") or (p["bus"] + ("" if p.get("bit") is None else f"[{p['bit']}]"))
def gbase(n): return re.sub(r"\[\d+\]$", "", n)
def lface(x, y, w, h): return min([(x, "W"), (w - x, "E"), (y, "S"), (h - y, "N")])[1]
def place(ps, w, hh, lf, src, along, exclude):
    L = hh if lf in "WE" else w
    onf = [p for p in ps if lface(p["x"], p["y"], w, hh) == lf and gbase(pname(p)) not in exclude]
    used = {round(((p["y"] if lf in "WE" else p["x"]) - OFF) / PITCH) for p in onf}
    lo = int(math.ceil((END - OFF) / PITCH - 1e-9)); hi = int(math.floor((L - END - OFF) / PITCH + 1e-9))
    cap = int(CAP * (L - 2 * END)); n = len(src)
    if len(onf) + n > cap:
        return None, f"face {lf}: {len(onf)}+{n} > pin6 cap {cap}"
    kt = (along - OFF) / PITCH
    free = sorted((k for k in range(lo, hi + 1) if k not in used), key=lambda k: (abs(k - kt), k))
    taken = set(used); pick = []
    for k in free:
        if len(pick) == n: break
        if k - 1 not in taken and k + 1 not in taken: pick.append(k); taken.add(k)
    for k in free:
        if len(pick) == n: break
        if k not in taken: pick.append(k); taken.add(k)
    if len(pick) < n: return None, f"face {lf}: free tracks < {n}"
    pick.sort(); res = []
    for p, k in zip(sorted(src, key=lambda p: (len(pname(p)), pname(p))), pick):
        pos = round(OFF + k * PITCH, 6)
        x, y = {"W": (INSET, pos), "E": (w - INSET, pos), "S": (pos, INSET), "N": (pos, hh - INSET)}[lf]
        res.append(dict(name=pname(p), layer=LAYER[lf], x=round(x, 6), y=round(y, 6)))
    return res, None
rep = dict(plan=str(pd), applied={}, skipped={})
for f, sol in J.items():
    if sel and not any(s in f for s in sel):
        continue
    if sol["after"][0] >= sol["before"][0]:
        rep["skipped"][f] = "no gain"; continue
    us = [(tn, h) for tn, t in T.items() for h in t.get("hard_cores", []) if h.get("pins_file") == f]
    w, hh = us[0][1]["outline_um"]
    ps = json.loads((pd / f).read_text()); old_sha = hashlib.sha256((pd / f).read_bytes()).hexdigest()[:12]
    moves = {}
    for port, spec in sol["face_moves"].items():
        F = spec.split("->")[1]
        src = [p for p in ps if gbase(pname(p)) == port]
        new, err = place(ps, w, hh, F, src, (hh if F in "WE" else w) / 2, {port})
        if new is None:
            moves[port] = "FAIL " + err; continue
        ps[:] = [p for p in ps if gbase(pname(p)) != port] + new
        moves[port] = spec
    orients = {}
    for key, spec in sol["orient_changes"].items():
        tn, ci = key.split(".", 1); o0, o1 = spec.split("->")
        h = next(x for x in T[tn]["hard_cores"] if x["inst"] == ci)
        assert h.get("orient", "R0") == o0
        if o1 == "R0": h.pop("orient", None)
        else: h["orient"] = o1
        cw, ch = h["outline_um"]; dx, dy = h.get("track_offset_um", [0, 0])
        cx, cy = h["origin_um"][0] + dx + cw / 2, h["origin_um"][1] + dy + ch / 2
        flipx = (o0 in ("MY", "R180")) != (o1 in ("MY", "R180")); flipy = (o0 in ("MX", "R180")) != (o1 in ("MX", "R180"))
        taps = [tp for tp in T[tn].get("clock", {}).get("taps", []) if tp["name"] == ci or tp["name"].startswith(ci + ".")]
        for tp in taps:
            x, y = tp["xy"]
            tp["xy"] = [round(2 * cx - x, 6) if flipx else x, round(2 * cy - y, 6) if flipy else y]
        orients[key] = dict(change=spec, clock_taps_mirrored=[tp["name"] for tp in taps])
    (pd / f).write_text(json.dumps(ps) + "\n")
    rep["applied"][f] = dict(old_sha=old_sha, new_sha=hashlib.sha256((pd / f).read_bytes()).hexdigest()[:12],
                             moves=moves, orients=orients, predicted=sol["after"])
    print(Path(f).name[:50], "moves", moves, "orients", {k: v["change"] for k, v in orients.items()})
(pd / "die_plan.json").write_text(json.dumps(raw, indent=1) + "\n")
json.dump(rep, open(outp, "w"), indent=1)
