#!/usr/bin/env python3
"""HBM-MU-QUAD-5 delta A (G0C residue), deterministic.  Usage: fix_g0c.py IN_PLAN OUT_PLAN TOOLS COLLAR_PINS [--report R]
 A1 collar u_col_idx pins = R5 re-issue verbatim (claude/hbm-core-lat-r5-1027@8857eba848 pins_r5.json, clk M5 43.224).
 A2 track_offset_um not a whole pitch (0.048) -> nearest whole pitch toward 0 (u_svg_Q2 -0.072 -> -0.048).
 A3 core clock taps: a tap naming a core replicated as <inst>__qN is split into one tap per replica; every core tap is
    re-sited onto the clock pin of its core (plan centre entry) when it is >1 um away (stale after repacks).
 A4 core_faces: every core port that faces away (check.py rule, mean cos < FACE_AWAY_COS) gets a superset-face copy
    '<port>__<F>' on the face check.py suggests, in its family's ONE canonical table (no new pin-hash types), on free
    tracks (face use <= 0.6); the instance binds it via pin_select and declares the other group unused (COORD 06:01
    ruling 2b superset-face master)."""
import json, sys, re, shutil, math, collections, hashlib, argparse
from pathlib import Path
ap = argparse.ArgumentParser(); ap.add_argument("inp"); ap.add_argument("out"); ap.add_argument("tools"); ap.add_argument("collar")
ap.add_argument("--report"); ap.add_argument("--skip-a4", action="store_true"); a = ap.parse_args()
sys.path.insert(0, a.tools)
import schema as S, check as C
PITCH, OFF, INSET, END, TRK = 0.048, 0.024, 0.019, 8.64, 0.6
OPP = dict(N="S", S="N", E="W", W="E")
src, out = Path(a.inp), Path(a.out)
if out.exists():
    shutil.rmtree(out)
shutil.copytree(src, out, symlinks=True)
raw = json.loads((out / "die_plan.json").read_text()); T = raw["partition_types"]
rep = dict(A1=None, A2=[], A3=dict(split=[], moved=[], unresolved=[]), A4=dict(added=[], blocked=[]))
# A1
hc = next(h for h in T["root"]["hard_cores"] if h["inst"] == "u_col_idx")
shutil.copyfile(a.collar, out / hc["pins_file"])
rep["A1"] = dict(file=hc["pins_file"], sha=hashlib.sha256(Path(a.collar).read_bytes()).hexdigest()[:12])
_ce = out / "clock_entries.json"
if _ce.exists():
    _E = json.loads(_ce.read_text()); _e = _E.get("root", {}).get("u_col_idx")
    if _e:   # entry island on the 4.32 PG lattice at the new 86.4^2 centre; the M5 pin sits on track 43.224 inside it
        _e["xy_um"] = [43.2, 43.2]; _e["island_um"] = [38.88, 38.88, 47.52, 47.52]
        _e["note"] = "QUAD-5 A1: R5 collar 86.4^2 (pins_r5 8857eba848, clk M5 43.224,43.2)"
        _ce.write_text(json.dumps(_E, indent=1) + "\n")
# A2
for tn, t in T.items():
    for h in t.get("hard_cores", []):
        off = h.get("track_offset_um")
        if not off:
            continue
        new = [round(math.trunc(round(v / PITCH, 6)) * PITCH, 6) if abs(v / PITCH - round(v / PITCH)) > 1e-6 else v for v in off]
        if new != off:
            rep["A2"].append((tn, h["inst"], off, new)); h["track_offset_um"] = new
cache = {}


def pins_of(f):
    if f not in cache:
        d = json.loads((out / f).read_text()); cache[f] = d.get("pins", d) if isinstance(d, dict) else d
    return cache[f]


def pname(p):
    return p.get("name") or (p["bus"] + ("" if p.get("bit") is None else f"[{p['bit']}]"))


def to_type(h, x, y):
    w, hh = h["outline_um"]; o = h.get("orient", "R0"); dx, dy = h.get("track_offset_um", [0, 0])
    if o in ("MX", "R180"):
        y = hh - y
    if o in ("MY", "R180"):
        x = w - x
    return round(h["origin_um"][0] + dx + x, 4), round(h["origin_um"][1] + dy + y, 4)


CLK = re.compile(r"^(clk|clock|tile_clk|hck|ck)(_|\[|$)")


def clk_xy(h, pin):
    if not h.get("pins_file"):
        return None
    ps = pins_of(h["pins_file"])
    c = [p for p in ps if pname(p) == pin] if pin != "*" else []
    if not c:
        c = [p for p in ps if pname(p) == "clk"] or [p for p in ps if CLK.match(pname(p))]
    return to_type(h, c[0]["x"], c[0]["y"]) if c else None


# A3: core taps sit at the plan centre entry (clock_entries.json, core-local, 12.8a); a tap naming a core that the
# quad repack replicated as <inst>__qN is split per replica; a tap off its entry (stale after repack) is re-sited.
ENT = json.loads((out / "clock_entries.json").read_text()) if (out / "clock_entries.json").exists() else {}


def entry_xy(tn, inst, h):
    e = ENT.get(tn, {}).get(inst) or ENT.get(tn, {}).get(re.sub(r"__q\d+$", "", inst))
    if e:
        return to_type(h, *e["xy_um"]), "entry"
    w, hh = h["outline_um"]
    return to_type(h, round(w / 2 / 4.32) * 4.32, round(hh / 2 / 4.32) * 4.32), "centre"


for tn, t in T.items():
    cl = t.get("clock", {}); taps = cl.get("taps", [])
    if not taps:
        continue
    insts = {h["inst"]: h for h in t.get("hard_cores", [])}
    new = []
    for tp in taps:
        if tp.get("kind") != "core" or "core_group" in tp:
            new.append(tp); continue
        nm = tp["name"]; hit = None
        for i in sorted(insts, key=len, reverse=True):
            if nm == i or nm.startswith(i + "."):
                hit = i; break
        if not hit:
            bi, dot, pn = nm.partition(".")
            reps = sorted(i for i in insts if re.fullmatch(re.escape(bi) + r"__q\d+", i))
            if reps:
                for r_ in reps:
                    q = dict(tp, name=r_ + dot + pn)
                    q["note"] = (tp.get("note", "") + f" | QUAD-5 A3: tap {nm} split per replica {r_} (quad repack)").strip(" |")
                    q["xy"] = list(entry_xy(tn, r_, insts[r_])[0]); new.append(q)
                rep["A3"]["split"].append((tn, nm, reps)); continue
            rep["A3"]["unresolved"].append((tn, nm)); new.append(tp); continue
        xy, how = entry_xy(tn, hit, insts[hit])
        if abs(xy[0] - tp["xy"][0]) + abs(xy[1] - tp["xy"][1]) > 1.0:
            rep["A3"]["moved"].append((tn, nm, tp["xy"], list(xy), how)); tp["xy"] = list(xy)
            tp["note"] = (tp.get("note", "") + f" | QUAD-5 A3: tap re-sited onto the plan centre {how} (stale after repack)").strip(" |")
        new.append(tp)
    cl["taps"] = new
(out / "die_plan.json").write_text(json.dumps(raw, indent=1) + "\n")


def away_list():
    rawp = S.load(str(out / "die_plan.json")); P = S.Plan(rawp, out / "die_plan.json"); R = C.Report(True)
    C.check_core_faces(P, R, out, None, max_msgs=10 ** 9)
    res = []
    for i in R.errors():
        m = re.match(r"type (\S+) core (\S+) port (\S+): (\d+) pins .* \(re-pin to face ([NSEW])\)$", i["msg"])
        if m:
            res.append((m.group(1), m.group(2), m.group(3), int(m.group(4)), m.group(5)))
    return res


def lface(x, y, w, h):
    return min([(x, "W"), (w - x, "E"), (y, "S"), (h - y, "N")])[1]


def tface(o, f):
    if o in ("MX", "R180") and f in "NS":
        f = OPP[f]
    if o in ("MY", "R180") and f in "EW":
        f = OPP[f]
    return f


POL = "superset-face master (COORD 06:01 ruling 2b): unused pin groups stay registered inside the master and are declared here; never tied or stubbed"
for it in range(0 if a.skip_a4 else 3):
    al = away_list(); print("iter", it, "away ports", len(al), flush=True)
    rep["A4"].setdefault("iters", []).append(len(al))
    if not al:
        break
    done = 0
    for tn, ci, port, n, bf in al:
        h = next(x for x in T[tn]["hard_cores"] if x["inst"] == ci)
        f = h["pins_file"]; ps = pins_of(f); w, hh = h["outline_um"]; o = h.get("orient", "R0")
        cur = h.get("pin_select", {}).get(port, port)
        lf = None
        for cand in [bf] + [g for g in "NSEW" if g not in (bf, OPP[bf])]:
            # capacity fallback: the faces perpendicular to the suggested one give cos ~0 (WARN, not ERROR)
            l_ = tface(o, cand); L_ = hh if l_ in "WE" else w
            cur_p = [p for p in ps if re.sub(r"\[\d+\]$", "", pname(p)) == cur]
            if cur_p and lface(cur_p[0]["x"], cur_p[0]["y"], w, hh) == l_:
                continue
            onf_ = sum(1 for p in ps if lface(p["x"], p["y"], w, hh) == l_)
            nb_ = sum(1 for p in ps if re.sub(r"\[\d+\]$", "", pname(p)) == re.sub(r"__[NSEW]$", "", cur))
            have_ = any(re.sub(r"\[\d+\]$", "", pname(p)) == re.sub(r"__[NSEW]$", "", cur) + "__" + l_ for p in ps)
            if have_ or onf_ + nb_ <= int(TRK * int((L_ - 2 * END) / PITCH)):
                lf = l_; break
        if lf is None:
            rep["A4"]["blocked"].append((tn, ci, port, "all faces over capacity")); continue
        base = re.sub(r"__[NSEW]$", "", cur)
        grp = f"{base}__{lf}"
        src_pins = [p for p in ps if re.sub(r"\[\d+\]$", "", pname(p)) == base]
        if not src_pins:
            rep["A4"]["blocked"].append((tn, ci, port, "no pins")); continue
        if lface(src_pins[0]["x"], src_pins[0]["y"], w, hh) == lf:
            grp = base
        have = [p for p in ps if re.sub(r"\[\d+\]$", "", pname(p)) == grp]
        if not have:
            L = hh if lf in "WE" else w
            ntr = int((L - 2 * END) / PITCH); cap = int(TRK * ntr)
            onf = [p for p in ps if lface(p["x"], p["y"], w, hh) == lf]
            if len(onf) + len(src_pins) > cap:
                rep["A4"]["blocked"].append((tn, ci, port, f"face {lf} {len(onf)}+{len(src_pins)} > cap {cap}")); continue
            used = {round(((p["y"] if lf in "WE" else p["x"]) - OFF) / PITCH) for p in onf}
            lo = int(math.ceil((END - OFF) / PITCH)); hi = int((L - END - OFF) / PITCH)
            free = [k for k in range(lo, hi + 1) if k not in used]
            step = len(free) / len(src_pins)
            ks = [free[int((j + 0.5) * step)] for j in range(len(src_pins))]
            layer = "M4" if lf in "WE" else "M5"
            for p, k in zip(src_pins, ks):
                pos = round(OFF + k * PITCH, 6)
                x, y = {"W": (INSET, pos), "E": (w - INSET, pos), "S": (pos, INSET), "N": (pos, hh - INSET)}[lf]
                nm = pname(p)
                ps.append(dict(name=grp + nm[len(base):], layer=layer, x=round(x, 6), y=round(y, 6)))
            (out / f).write_text(json.dumps(ps) + "\n")
        if grp == base:
            h.get("pin_select", {}).pop(port, None)
        else:
            h.setdefault("pin_select", {})[port] = grp
        rep["A4"]["added"].append((tn, ci, port, n, bf, grp)); done += 1
    # declare unused groups: every instance of a table declares the superset groups it does not bind
    groups = collections.defaultdict(set)
    for f, ps in cache.items():
        for p in ps:
            m = re.match(r"^(.*)__([NSEW])(\[\d+\])?$", pname(p))
            if m:
                groups[f].add((m.group(1), m.group(1) + "__" + m.group(2)))
    for tn, t in T.items():
        for h in t.get("hard_cores", []):
            gs = groups.get(h.get("pins_file"))
            if not gs:
                continue
            sel = h.get("pin_select", {})
            allg = {b for b, _ in gs} | {g for _, g in gs}
            bound = {sel.get(b, b) for b, _ in gs}
            un = (set(h.get("unused_pins", [])) - allg) | (allg - bound)
            if un:
                h["unused_pins"] = sorted(un); h["unused_pins_policy"] = h.get("unused_pins_policy", POL)
    (out / "die_plan.json").write_text(json.dumps(raw, indent=1) + "\n")
    if not done:
        break
rep["A3"]["n_moved"] = len(rep["A3"]["moved"]); rep["A4"]["n_added"] = len(rep["A4"]["added"])
rep["A4"]["superset_pins"] = sum(x[3] for x in rep["A4"]["added"])
if a.report:
    Path(a.report).write_text(json.dumps(rep, indent=1))
print("A1", rep["A1"]); print("A2", rep["A2"])
print("A3 split", rep["A3"]["split"], "moved", len(rep["A3"]["moved"]), "unresolved", rep["A3"]["unresolved"][:10])
print("A4 added", len(rep["A4"]["added"]), "pins", rep["A4"]["superset_pins"], "blocked", rep["A4"]["blocked"][:20])
print("sha", hashlib.sha256((out / "die_plan.json").read_bytes()).hexdigest()[:12])
