#!/usr/bin/env python3
"""DIE-HBM-5 C20i = C20h + (1) q2 ring_ag qid[1:0] pin move (DIE-HBM-4-KITS apply_q2_qid_mid.py, GEOM-40 fix) +
(2) G0C hard_cores lattice fix: every hard core whose origin is off the 8.64 die lattice (C20g G0C: 57 cores on the 4.32 /
2.16 / 2.808 sub-lattice in root, q_hub_nw, q_hub_ne; remainders >= the 2.16 base unit, so track_offset_um cannot hold them)
moves to the 8.64 lattice by the smallest shift that keeps it inside the type outline, off every other hard core, and with
no ft-slot / internal-station register inside it.  Moved with the core: its clock tap (type clock.taps, name == inst),
its die-frame tap in clock_taps_die.json, and the from_um / to_um end of every internal station it launches / captures.
(3) plan-made (c20g) pins_files of R0 cores (u_tkm_SW_root chain, 4 clk pins): M3/M5 pins off the plan tracks snapped to the nearest free track (same layer, <= half pitch).
usage: apply_c20i.py TOOLS SRC_DIR DST_DIR [QID_SCRIPT]"""
import json, hashlib, shutil, sys, subprocess, itertools
from pathlib import Path
tools, src, dst = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
qid = sys.argv[4] if len(sys.argv) > 4 else None
sys.path.insert(0, tools); import schema as S, check as C
if dst.exists():
    raise SystemExit(f"{dst} exists")
shutil.copytree(src, dst, ignore=shutil.ignore_patterns("gates", "gates_*", "*.otrun.log", "gates20h.sh"))
rep = dict(event="C20i lattice + q2 qid", base=str(src))
if qid:
    out = subprocess.run([sys.executable, qid, str(dst), "--report", str(dst / "q2_qid_mid_delta_report.json")],
                         capture_output=True, text=True, check=True).stdout
    rep["q2_qid"] = json.loads(out.strip().splitlines()[-1])
P = json.load(open(dst / "die_plan.json"))
G = float(P["die"].get("grid_um", 8.64)); EPS = 1e-6
def rem(v):
    r = v % G
    return 0.0 if r < EPS or G - r < EPS else r
def shifts(v):                      # candidate lattice shifts, smallest first
    r = rem(v)
    if r == 0.0:
        return [0.0]
    c = [-r, G - r, -r - G, 2 * G - r, -r - 2 * G, 3 * G - r]
    return sorted((round(x, 4) for x in c), key=abs)
taps_die = json.load(open(dst / "clock_taps_die.json"))
parts = {p["name"]: p for p in P["partitions"]}
moved = []
for tn, t in P["partition_types"].items():
    hcs = t.get("hard_cores", [])
    W, H = t["outline_um"]
    regs = [r for s in t.get("ft_slots", []) for r in s.get("regs_um", [])]
    regs += [r for e in t.get("internal_stations", []) for r in e["regs_um"]]
    def inside(b, r):
        return b[0] + EPS < r[0] < b[2] - EPS and b[1] + EPS < r[1] < b[3] - EPS
    def box(hc, d=(0, 0)):
        (x, y), (w, h) = hc["origin_um"], hc["outline_um"]; dx, dy = hc.get("track_offset_um", [0, 0])
        return (x + dx + d[0], y + dy + d[1], x + dx + d[0] + w, y + dy + d[1] + h)
    def ok(hc, d):
        b = box(hc, d)
        if b[0] < -EPS or b[1] < -EPS or b[2] > W + EPS or b[3] > H + EPS:
            return False
        for o in hcs:
            if o is hc: continue
            q = box(o)
            if b[0] < q[2] - EPS and b[2] > q[0] + EPS and b[1] < q[3] - EPS and b[3] > q[1] + EPS:
                return False
        b0 = box(hc)
        return not any(inside(b, r) and not inside(b0, r) for r in regs)
    # process cores on the sub-lattice; low-y/low-x first so stacked groups (tkm tiles) shift consistently
    todo = [hc for hc in hcs if rem(hc["origin_um"][0]) or rem(hc["origin_um"][1])]
    for hc in sorted(todo, key=lambda h: (h["origin_um"][1], h["origin_um"][0])):
        ox, oy = hc["origin_um"]
        cand = sorted(itertools.product(shifts(ox), shifts(oy)), key=lambda d: (abs(d[0]) + abs(d[1]), abs(d[1])))
        d = next((d for d in cand if ok(hc, d)), None)
        push = []
        if d is None:                                  # fallback: face registers swept by the shift ride with the core
            for dd in cand:
                b = box(hc, dd); b0 = box(hc)
                if b[0] < -EPS or b[1] < -EPS or b[2] > W + EPS or b[3] > H + EPS:
                    continue
                if any(o is not hc and b[0] < box(o)[2] - EPS and b[2] > box(o)[0] + EPS and b[1] < box(o)[3] - EPS
                       and b[3] > box(o)[1] + EPS for o in hcs):
                    continue
                rr = [r for r in regs if inside(b, r) and not inside(b0, r)]
                if all(not any(inside(box(o), (r[0] + dd[0], r[1] + dd[1])) for o in hcs if o is not hc) for r in rr):
                    d, push = dd, rr
                    break
        if d is None:
            moved.append(dict(type=tn, core=hc["inst"], before=[ox, oy], after=None, shift=None, note="NO FREE LATTICE SLOT"))
            continue
        inr = push                                     # in-core regs stay (G0 hop <= 405 unchanged); only swept face regs move
        for r in inr:
            r[0], r[1] = round(r[0] + d[0], 4), round(r[1] + d[1], 4)
        hc["origin_um"] = [round(ox + d[0], 4), round(oy + d[1], 4)]
        nt = 0
        for tp in t.get("clock", {}).get("taps", []):
            if tp["name"] == hc["inst"]:
                tp["xy"] = [round(tp["xy"][0] + d[0], 4), round(tp["xy"][1] + d[1], 4)]; nt += 1
        nd = 0
        for e in taps_die:
            if e.get("type") == tn and e.get("tap") == hc["inst"]:
                o = parts[e["part"]].get("orient", "R0")
                sx = -1 if o in ("MY", "R180") else 1; sy = -1 if o in ("MX", "R180") else 1
                e["xy_die_um"] = [round(e["xy_die_um"][0] + sx * d[0], 4), round(e["xy_die_um"][1] + sy * d[1], 4)]; nd += 1
        ns = 0
        for e in t.get("internal_stations", []):
            for k, key in (("from_um", "launch"), ("to_um", "capture")):
                if (e.get(key) or "").split(".")[0] == hc["inst"]:
                    e[k] = [round(e[k][0] + d[0], 4), round(e[k][1] + d[1], 4)]; ns += 1
        moved.append(dict(type=tn, core=hc["inst"], before=[ox, oy], after=hc["origin_um"], shift=list(d), taps=nt, pushed_face_regs=len(push),
                          die_taps=nd, station_ends=ns))
rep["lattice"] = moved
# (3) off-track plan pins of the tkm root chain view (plan pins_file, not a native view)
Pl = S.Plan(P, dst / "die_plan.json")
snap = []
for tn, t in P["partition_types"].items():
    for hc in t.get("hard_cores", []):
        if not hc.get("pins_file") or hc.get("orient", "R0") != "R0" or not any(
                not C.on_track(hc["origin_um"][0 if Pl.layers[ln]["dir"] == "V" else 1] + (x if Pl.layers[ln]["dir"] == "V" else y), Pl.layers[ln])
                for _, ln, x, y in C.core_pins(hc, str(dst)) if ln in Pl.layers and ln != "M1"):
            continue
        assert "c20g" in hc["pins_file"] or hc["inst"] == "u_tkm_SW_root", hc["pins_file"]    # plan-made views only
        pf = dst / hc["pins_file"]; pins = json.loads(pf.read_text())
        cen = [hc["outline_um"][0] / 2, hc["outline_um"][1] / 2]
        lst = pins.get("pins", pins) if isinstance(pins, dict) else pins
        used = {(q["layer"], round(q["x"], 4), round(q["y"], 4)) for q in lst}
        for q in lst:
            L = Pl.layers.get(q["layer"])
            if L is None or q["layer"] == "M1": continue
            ax = "x" if L["dir"] == "V" else "y"
            c = hc["origin_um"][0 if ax == "x" else 1] + q[ax]
            if C.on_track(c, L): continue
            k = round((c - L["offset_um"]) / L["pitch_um"])
            for kk in sorted((k, k - 1, k + 1), key=lambda j: (round(abs(L["offset_um"] + j * L["pitch_um"] - c), 4),
                                                         abs(L["offset_um"] + j * L["pitch_um"] - hc["origin_um"][0 if ax == "x" else 1] - cen[0 if ax == "x" else 1]))):
                nv = round(L["offset_um"] + kk * L["pitch_um"] - hc["origin_um"][0 if ax == "x" else 1], 4)
                key = (q["layer"], nv if ax == "x" else round(q["x"], 4), nv if ax == "y" else round(q["y"], 4))
                if key not in used:
                    used.discard((q["layer"], round(q["x"], 4), round(q["y"], 4))); used.add(key)
                    snap.append([hc["inst"], q.get("name") or f"{q['bus']}[{q.get('bit', 0)}]", q["layer"], ax, q[ax], nv]); q[ax] = nv
                    break
        new = pf.parent / (pf.stem + "__c20i.json"); new.write_text(json.dumps(pins, indent=1) + "\n")
        hc["pins_file"] = str(new.relative_to(dst))
rep["pins_snapped"] = snap
P["note"] = (P.get("note", "") + " | C20i (DIE-HBM-5): q2 ring_ag qid pin move; %d hard cores to the 8.64 lattice; %d tkm root pins on track"
             % (sum(1 for m in moved if m["after"]), len(snap)))
txt = json.dumps(P, indent=1)
(dst / "die_plan.json").write_text(txt)
(dst / "clock_taps_die.json").write_text(json.dumps(taps_die, indent=1))
sha = hashlib.sha256(txt.encode()).hexdigest()
(dst / "die_plan.sha256").write_text(sha + "  die_plan.json\n")
rep["sha"] = sha
(dst / "c20i_event_report.json").write_text(json.dumps(rep, indent=1))
print(sha[:12], "moved", sum(1 for m in moved if m["after"]), "failed", [m["core"] for m in moved if not m["after"]],
      "max_shift", max((abs(m["shift"][0]) + abs(m["shift"][1]) for m in moved if m["shift"]), default=0), "pins_snapped", len(snap))
