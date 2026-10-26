#!/usr/bin/env python3
"""D-HBM-B1 G0C core-face fix, COORD 2026-10-26 06:01 ruling 2 order (PATH-HBM-R2, b1n4 -> b1n5 stage 1).

 (a) orient: latency-neutral instance orient/mirror flips were exhausted in b1n3 (path_hbm_g0c_fix.py: 12 taken, 6
     rejected because they add internal stations); this pass re-probes every failing core and takes a flip only when
     the core has no internal stations (latency-neutral by construction) and the type's error ports fall.
 (b) superset-face pin set on the shared master: for each still-failing (core, port) the master gets a copy of the
     port's pins on the face that faces its partners ("<port>__<core-frame face>[i]", same bit indices, M4 on E/W
     faces / M5 on N/S faces, on the tracks of the master's existing pins of that layer, centred on the partner
     direction).  Copies are shared: one copy per (master, port, face) serves every instance that needs it.  Each
     instance declares hc.pin_select {port: copy} (the copy it binds) and hc.unused_pins (every superset pin group it
     leaves unbound: registered inside the master, declared, never tied/stubbed).  The master's new pins live in a
     new pins file (<module>_pins_ss.json) so the plan JSON SHA covers the change.  Internal stations launched from /
     captured at a re-faced port move their endpoint to the copy and are re-sited with the SAME station count
     (0 cycles); a link that cannot keep its count is reported (cycle_delta) and the copy is not taken.
 (c) per-instance pin variants: only for what (b) cannot fix (none expected); listed in the report.
 Clock/reset ports (conn-model): a core clock pin is fed by its own die clock tap (12.3: one 250-ps zero-early tap
 per core pin) and reset by the regional reset tree, not by peer cores sharing the net; with --clkrst-tap the
 peer-core partners of *clk / *rst_n ports are replaced by "tap:<core>.<port>" in core_conns.json (face rule then
 skips them, as it does for any port without a placed partner).  Recorded as its own category for COORD review.
Usage: path_hbm_superset_faces.py <WT> <src plan dir> <out plan dir> [--clkrst-tap]
"""
import json, sys, copy, math, re, shutil
from pathlib import Path
WT, SRC, OUT = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
CLKRST = "--clkrst-tap" in sys.argv
sys.path.insert(0, WT + "/tools/die_plan"); sys.path.insert(0, WT + "/physical/die_plan/hbm_arch")
import check as C, schema as S
from cores_b2 import RelayRouter, free_point
LIM = 364.0
if OUT.exists(): raise SystemExit(f"{OUT} exists")
shutil.copytree(SRC, OUT)
raw = json.loads((OUT / "die_plan.json").read_text()); T = raw["partition_types"]
conns = json.loads((OUT / "core_conns.json").read_text())
log = dict(orient=[], orient_rejected=[], superset=[], variants=[], clkrst_tap=[], stations=[], cycle_delta={}, fails=[],
           per_error=[])
OPPF = dict(N="S", S="N", E="W", W="E")

def to_core_face(o, f):          # orient maps are involutions: type-frame face <-> core-frame face
    if o in ("MX", "R180") and f in "NS": f = OPPF[f]
    if o in ("MY", "R180") and f in "EW": f = OPPF[f]
    return f

def plan():
    return S.Plan(raw, OUT / "die_plan.json")

def errs(tn):
    """{(core, port): (face hint, [(what, ux, uy)] type-frame dirs)} of core_faces ERRORs of one type."""
    P = plan(); P.types = {tn: T[tn]}; R = C.Report(True); cap = []; got = []
    bf0 = C.best_face; err0 = R.err
    C.best_face = lambda d: (cap.append(d), bf0(d))[1]
    def err(chk, msg, **k):
        if chk == "core_faces" and " port " in msg and "re-pin to face" in msg: got.append((msg, cap[-1]))
        return err0(chk, msg, **k)
    R.err = err
    try:
        C.check_core_faces(P, R, str(OUT), max_msgs=10**6)
    finally:
        C.best_face = bf0
    out = {}
    for m, d in got:
        ci = m.split(" core ")[1].split(" port ")[0]; lp = m.split(" port ")[1].split(":")[0]
        out[(ci, lp)] = (m.rsplit("re-pin to face ", 1)[1].rstrip(")"), d)
    return out

def boxes(t):
    return [(h["origin_um"][0] + h.get("track_offset_um", [0, 0])[0], h["origin_um"][1] + h.get("track_offset_um", [0, 0])[1],
             *h["outline_um"]) for h in t["hard_cores"]]

def restation(t, e, why):
    """keep the station count; re-site on the L route (macro-free points), else RelayRouter + pad."""
    w, h = t["outline_um"]; bx = boxes(t)
    if C._hops_ok(e["from_um"], e["regs_um"], e["to_um"], LIM): return 0
    n0 = len(e["regs_um"]); fr = lambda p: free_point(p, bx, w, h)
    a, b = tuple(e["from_um"]), tuple(e["to_um"])
    for seg in ([a, (b[0], a[1]), b], [a, (a[0], b[1]), b]):
        Lr = C.plen(seg)
        cand = [fr(C.point_at(seg, Lr * j / (n0 + 1))) for j in range(1, n0 + 1)]
        if n0 and C._hops_ok(a, cand, b, LIM):
            e["regs_um"] = [[round(v, 3) for v in p] for p in cand]
            e["note"] = e.get("note", "") + f" | G0C-SUPERSET {why}: {n0} station(s) re-sited (count kept)"
            log["stations"].append(dict(conn=e.get("conn"), why=why, before=n0, after=n0)); return 0
    try:
        regs = list(RelayRouter(bx, w, h, 360.0)(a, fr(b)))
    except ValueError as ex:
        log["fails"].append(f"{why} {e.get('conn')}: {ex}"); return None
    while len(regs) < n0: regs.append(regs[-1])
    if not C._hops_ok(a, regs, b, LIM): return None
    e["regs_um"] = [[round(v, 3) for v in p] for p in regs]
    e["note"] = e.get("note", "") + f" | G0C-SUPERSET {why}: re-stationed {n0}->{len(regs)}"
    log["stations"].append(dict(conn=e.get("conn"), why=why, before=n0, after=len(regs)))
    return len(regs) - n0

# ------------------------------------------------------------------ conn-model: clock / reset partners
CR = re.compile(r"(^|_)(clk|clock|rst_n|rst|reset_n)$")
if CLKRST:
    for tn in T:
        for ci, ports in conns.get(tn, {}).items():
            for lp, tg in ports.items():
                if CR.search(lp) and tg and all(v.startswith("core:") for v in tg):
                    ports[lp] = [f"tap:{ci}.{lp}"]
                    log["clkrst_tap"].append(dict(type=tn, core=ci, port=lp, was=tg))
    (OUT / "core_conns.json").write_text(json.dumps(conns, indent=1) + "\n")

TYPES = [tn for tn, t in T.items() if t.get("hard_cores")]
start = {tn: errs(tn) for tn in TYPES}
start = {tn: e for tn, e in start.items() if e}
print("start", {tn: len(e) for tn, e in start.items()}, flush=True)
if CLKRST:
    # the clk/rst conn change applied before `start`: count what it fixed against the source plan's report
    pass

# ------------------------------------------------------------------ (a) orient re-probe (latency-neutral only)
for tn in list(start):
    t = T[tn]
    for hc in t["hard_cores"]:
        ci = hc["inst"]; base = errs(tn)
        own0 = sum(1 for k in base if k[0] == ci)
        if not own0: continue
        has_ist = any(str(e.get("launch", "")).startswith(ci + ".") or str(e.get("capture", "")).startswith(ci)
                      for e in t.get("internal_stations", []))
        taps = [tp for tp in t.get("clock", {}).get("taps", []) if tp["name"].startswith(ci + ".")]
        o0 = hc.get("orient", "R0"); best = None
        for o in ("R0", "MX", "MY", "R180"):
            if o == o0: continue
            hc["orient"] = o; b = errs(tn)
            own = sum(1 for k in b if k[0] == ci)
            if len(b) < len(base) and own <= own0 and (best is None or len(b) < best[1]): best = (o, len(b), own)
        hc["orient"] = o0
        if best is None: continue
        if has_ist or taps:
            log["orient_rejected"].append(dict(type=tn, core=ci, before=o0, after=best[0], type_err=[len(base), best[1]],
                                               why="core has internal stations / clock taps: flip would re-site latency-bearing links"))
            continue
        hc["orient"] = best[0]
        hc["note"] = hc.get("note", "") + f" | G0C-SUPERSET orient {o0} -> {best[0]} (latency-neutral: no stations/taps)"
        log["orient"].append(dict(type=tn, core=ci, before=o0, after=best[0], type_err=[len(base), best[1]]))

# ------------------------------------------------------------------ (b) superset faces on the shared master
pinfiles = {}          # pins_file -> list of pin dicts (mutable, written as <module>_pins_ss.json)
def master_pins(pf):
    if pf not in pinfiles:
        js = json.loads((OUT / pf).read_text()); js = js.get("pins", js) if isinstance(js, dict) else js
        pinfiles[pf] = [dict(q) for q in js]
    return pinfiles[pf]
copies = {}            # (pins_file, port, core-face) -> copy base name
LAYER = dict(E="M4", W="M4", N="M5", S="M5")

def face_of(q, cw, ch):
    return min([(q["x"], "W"), (cw - q["x"], "E"), (q["y"], "S"), (ch - q["y"], "N")])[1]

def make_copy(hc, lp, cf, dirs_core):
    pf = hc["pins_file"]; pins = master_pins(pf); cw, ch = hc["outline_um"]
    key = (pf, lp, cf)
    if key in copies: return copies[key]
    orig = [q for q in pins if re.sub(r"\[\d+\]$", "", q.get("name") or q["bus"]) == lp]
    if not orig: raise ValueError(f"{pf}: port {lp} has no pins")
    ln = LAYER[cf]; L = C.P_LAYERS[ln]; pitch = L["pitch_um"]
    along = "y" if cf in "EW" else "x"; span = ch if cf in "EW" else cw
    same = [q for q in pins if q["layer"] == ln]
    ref = same[0][along] if same else L["offset_um"]
    on_face = [q for q in pins if face_of(q, cw, ch) == cf]
    used = {round((q[along] - ref) / pitch) for q in on_face if q["layer"] == ln}
    depth = [q["x"] if cf in "EW" else q["y"] for q in on_face]
    dep = (sorted(depth)[len(depth) // 2] if depth else (cw - 0.019 if cf == "E" else ch - 0.019 if cf == "N" else 0.019))
    n = len(orig)
    # spacing: the original port's own pitch (tracks), at least 2 tracks, shrunk to fit the face
    oc = sorted(q["y" if face_of(q, cw, ch) in "EW" else "x"] for q in orig)
    dd = sorted(b - a for a, b in zip(oc, oc[1:]))
    st = max(2, round((dd[len(dd) // 2] if dd else 2 * pitch) / pitch))
    m = 2.0
    while st > 1 and n * st * pitch > span - 2 * m: st -= 1
    ux = sum(d[0] for d in dirs_core) / len(dirs_core); uy = sum(d[1] for d in dirs_core) / len(dirs_core)
    c = span / 2 + (uy if cf in "EW" else ux) * span / 2
    lo_k = math.ceil((m - ref) / pitch); hi_k = math.floor((span - m - ref) / pitch)
    want = n * st
    k0 = int(round((c - ref) / pitch - want / 2)); k0 = max(lo_k, min(k0, hi_k - want))
    ks = []; k = k0
    # take n free tracks at stride st from k0 (skip occupied); wrap to the face start if the end is hit
    tried = 0
    while len(ks) < n and tried < 4 * (hi_k - lo_k):
        if k > hi_k: k = lo_k
        if all(abs(k - u) >= 2 for u in used) and all(abs(k - q) >= st for q in ks[-1:]): ks.append(k); k += st
        else: k += 1
        tried += 1
    if len(ks) < n: raise ValueError(f"{pf}: face {cf} has no room for {n} pins of {lp}")
    name = f"{lp}__{cf}"
    bk = lambda q: int((re.search(r"\[(\d+)\]$", q.get("name") or "") or [0, 0])[1])
    for q, kk in zip(sorted(orig, key=bk), sorted(ks)):
        nm = q.get("name") or f"{q['bus']}[{q.get('bit', 0)}]"
        bit = re.search(r"\[(\d+)\]$", nm)
        p = dict(name=name + (f"[{bit.group(1)}]" if bit else ""), layer=ln)
        p[along] = round(ref + kk * pitch, 4); p["x" if along == "y" else "y"] = round(dep, 4)
        p["superset_of"] = lp
        pins.append(p)
    copies[key] = name
    log["superset"].append(dict(master=hc["module"], pins_file=pf, port=lp, core_face=cf, copy=name, pins=n,
                                stride_tracks=st, layer=ln))
    return name

C.P_LAYERS = plan().layers
for tn in list(start):
    t = T[tn]; E = errs(tn)
    for (ci, lp), (bf, dirs) in sorted(E.items()):
        hc = [h for h in t["hard_cores"] if h["inst"] == ci][0]; o = hc.get("orient", "R0")
        cf = to_core_face(o, bf)
        fx = -1 if o in ("MY", "R180") else 1; fy = -1 if o in ("MX", "R180") else 1
        dcore = [(fx * ux, fy * uy) for _, ux, uy in dirs]
        try:
            name = make_copy(hc, lp, cf, dcore)
        except ValueError as ex:
            log["fails"].append(str(ex)); continue
        snap = copy.deepcopy(t)
        hc.setdefault("pin_select", {})[lp] = name
        new_pf = hc["pins_file"].replace("_pins.json", "_pins_ss.json") if "_pins_ss" not in hc["pins_file"] else hc["pins_file"]
        # every instance of the master points at the superset pins file (written below)
        cpin = [q for q in master_pins(hc["pins_file"]) if q.get("superset_of") == lp and q["name"].startswith(name)]
        X0 = hc["origin_um"][0] + hc.get("track_offset_um", [0, 0])[0]; Y0 = hc["origin_um"][1] + hc.get("track_offset_um", [0, 0])[1]
        cw, ch = hc["outline_um"]
        tp = lambda q: [round(X0 + C._orient_pt(o, cw, ch, q["x"], q["y"])[0], 4), round(Y0 + C._orient_pt(o, cw, ch, q["x"], q["y"])[1], 4)]
        mid = tp(cpin[len(cpin) // 2])
        ok = True
        for e in t.get("internal_stations", []):
            if e.get("launch") == f"{ci}.{lp}": e["from_um"] = mid; k = "launch"
            elif e.get("capture") == f"{ci}.{lp}": e["to_um"] = mid; k = "capture"
            else: continue
            d = restation(t, e, f"superset {ci}.{lp}")
            if d is None or d:
                ok = False; log["cycle_delta"][e.get("conn")] = d
        if not ok:
            t.clear(); t.update(snap); log["fails"].append(f"{tn} {ci}.{lp}: superset copy needs stations; not taken"); continue
        log["per_error"].append(dict(type=tn, core=ci, port=lp, step="superset", copy=name, type_face=bf, core_face=cf))

# write superset pins files + per-instance declarations for every instance of an affected master
for pf, pins in pinfiles.items():
    npf = pf.replace("_pins.json", "_pins_ss.json")
    (OUT / npf).write_text(json.dumps(pins, indent=0) + "\n")
    groups = sorted({q["name"].rsplit("[", 1)[0] for q in pins if q.get("superset_of")})
    origs = sorted({q["superset_of"] for q in pins if q.get("superset_of")})
    for tn, t in T.items():
        for hc in t.get("hard_cores", []):
            if hc.get("pins_file") != pf: continue
            hc["pins_file"] = npf; sel = hc.get("pin_select", {})
            hc["unused_pins"] = sorted([g for g in groups if g not in sel.values()] + [p for p in origs if p in sel])
            hc["unused_pins_policy"] = ("superset-face master (COORD 06:01 ruling 2b): unused pin groups stay registered "
                                        "inside the master and are declared here; never tied or stubbed")
log["supersets_by_pins_file"] = {}
for (pf, lp, cf), name in copies.items():
    log["supersets_by_pins_file"].setdefault(pf.replace("_pins.json", "_pins_ss.json"), {})[name] = dict(of=lp, core_face=cf)

end = {tn: errs(tn) for tn in TYPES}; end = {tn: e for tn, e in end.items() if e}
for tn, E in end.items():
    for (ci, lp), (bf, _) in E.items():
        log["variants"].append(dict(type=tn, core=ci, port=lp, face=bf, why="needs a per-instance pin variant"))
log["start_errors"] = {tn: len(e) for tn, e in start.items()}; log["end_errors"] = {tn: len(e) for tn, e in end.items()}
(OUT / "die_plan.json").write_text(json.dumps(raw, indent=1) + "\n")
(OUT / "superset_faces_report.json").write_text(json.dumps(log, indent=1, default=str) + "\n")
print(json.dumps({k: (len(v) if isinstance(v, (list, dict)) else v) for k, v in log.items()}))
print("start", log["start_errors"], "end", log["end_errors"], "fails", log["fails"][:10])
