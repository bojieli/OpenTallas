#!/usr/bin/env python3
"""DIE-KV-14a 10-28: core_tx plan delta (KV-KITS-14 ASK / COORD 16:33, GEOM-46 (1)-(3)). Die-local, opt-in, deterministic.

qkd_hr_core_tx had a 276.48 x 267.84 um plan slot sized by a two-face pin table (W 1047 / S 2539 at 9.3 /um / N 40 / E 0)
around only ~9.0k um2 of logic (fill .12, r2r 516 um, clock reach 263 um).  This generator writes the replacement:

  (1) a square outline, the smallest multiple of the 8.64-um plan grid whose 4 faces hold every pin at <= CAP pins/um
      (usable face = outline - 2 x 2.16-um corner keep-out) with SLACK spare;
  (2) pins on all 4 faces: every pin group (bus) with core partners (core_conns.json) goes to the face with the lowest
      mean Manhattan distance to its partner slots (greedy by regret under the per-face cap); groups with no core-only
      partner (the partition-glue status pins, resets, unmapped pins -- the 40 old N-face pins among them) go to the face
      where their module's logic sits = the module's dominant face of its partner-assigned pins (reserved first);
      inside a face, groups are ordered by their partner position along the face and spread evenly on the die
      symmetric tracks (M4 0.024 + k 0.048 on E/W, M5 on N/S; pins 0.096 um inside the face, as core_pins_hr.py);
  (3) the clock entry ck[0] (interior M5 pin, 12.8a) at the logic centroid = centroid of the pin registers (each pin is
      registered at its face, METHODOLOGY 1.9), snapped to an M5 track and the 2.16-um row/track grid;
  and the new slot origin: the 8.64-grid position INSIDE the old slot with the least partner wire length, so the die
  floorplan and the neighbours do not change.

usage:
  core_tx_plan.py build --plan PLAN.json[.gz] --pins OLD_PINS.json --conns core_conns.json --out-dir DIR [--tag r26q14]
  core_tx_plan.py apply --plan IN.json[.gz] --delta DIR/core_tx_plan_delta.json --out OUT.json
`apply` rewrites only the hub_Wi hard_core slot (origin/outline/pins_file/note) and the core's partition clock tap xy;
everything else is byte-for-byte the input plan content (json re-dump).  The kit generator (gen_core_kit_kv.py --plan OUT)
then reads the new outline/pins/entry unchanged."""
import argparse
import bisect
import copy
import gzip
import hashlib
import json
import math
import re
import sys
from pathlib import Path

GRID = 8.64            # plan outline / origin grid (all hub_Wi slots are multiples)
KEEP = 2.16            # corner keep-out per face end (core_pins_hr.py)
INSET = 0.096          # pin centre inside the face
PITCH = 0.048          # M4 / M5 die symmetric tracks
OFFS = 0.024
CORE_MARGIN = 4.32     # CORE_AREA inset of the kits (config.mk)
ENTRY_GRID = 2.16      # lcm(row 0.27, track 0.048)
FACES = ("N", "E", "S", "W")
LAYER = {"N": "M5", "S": "M5", "E": "M4", "W": "M4"}
CLOCK_PINS = ("ck[0]",)
WINDOW = 10.0          # pin_density window of the auto-geom check (um)


def load(path):
    p = Path(path)
    raw = p.read_bytes()
    return json.loads(gzip.decompress(raw) if p.suffix == ".gz" else raw)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def bus_of(name):
    return re.sub(r"\[\d+\]$", "", name)


def bit_of(name):
    m = re.search(r"\[(\d+)\]$", name)
    return int(m.group(1)) if m else -1


def module_of(name):
    return name.split("__")[0]


def rect_dist(px, py, r):
    x0, y0, x1, y1 = r
    return max(x0 - px, 0, px - x1) + max(y0 - py, 0, py - y1)


def face_xy(f, c, w, h):
    return {"N": (c, round(h - INSET, 6)), "S": (c, INSET), "E": (round(w - INSET, 6), c), "W": (INSET, c)}[f]


def face_len(f, w, h):
    return w if f in "NS" else h


def cap_of(f, w, h, cap):
    return int(math.floor((face_len(f, w, h) - 2 * KEEP) * cap + 1e-9))


def tracks(f, w, h):
    L = face_len(f, w, h)
    lo = math.ceil((KEEP - OFFS) / PITCH - 1e-9)
    hi = math.floor((L - KEEP - OFFS) / PITCH + 1e-9)
    return lo, hi


def choose_side(npins, cap, slack, min_side=0.0):
    k = max(1, math.ceil(min_side / GRID - 1e-9))
    while True:
        s = round(k * GRID, 4)
        if 4 * (s - 2 * KEEP) * cap >= npins * (1.0 + slack):
            return s
        k += 1


def slot_of(plan, ptype, inst):
    hc = next(h for h in plan["partition_types"][ptype]["hard_cores"] if h["inst"] == inst)
    return hc


def partner_rects(plan, ptype):
    out = {}
    for h in plan["partition_types"][ptype]["hard_cores"]:
        (x, y), (w, hh) = h["origin_um"], h["outline_um"]
        if h.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90"):
            w, hh = hh, w
        out["core:" + h["inst"]] = (x, y, x + w, y + hh)
    return out


def groups_of(pins_doc, conns):
    """bus -> dict(names (bit order), module, targets [partner keys] or None (logic-face group))."""
    g = {}
    for p in pins_doc["pins"]:
        if p["name"] in CLOCK_PINS:
            continue
        b = bus_of(p["name"])
        d = g.setdefault(b, dict(bus=b, names=[], module=module_of(b), targets=None))
        d["names"].append(p["name"])
    for b, d in g.items():
        d["names"].sort(key=bit_of)
        part = conns.get(b)
        if part and all(x.startswith("core:") for x in part):
            d["targets"] = sorted(part)
    return g


def face_cost(f, targets, rects, ox, oy, w, h, n=16):
    """mean Manhattan distance (um) from n evenly spread pin sites of face f (parent frame) to the partner slots."""
    L = face_len(f, w, h)
    tot = 0.0
    for i in range(n):
        c = KEEP + (i + 0.5) * (L - 2 * KEEP) / n
        x, y = face_xy(f, c, w, h)
        tot += sum(rect_dist(ox + x, oy + y, rects[t]) for t in targets) / len(targets)
    return tot / n


def module_faces(out, groups):
    dom = {}
    for f in FACES:
        for b, n in out[f]:
            if groups[b]["targets"]:
                dom.setdefault(groups[b]["module"], {}).setdefault(f, 0)
                dom[groups[b]["module"]][f] += 1
    return {m: max(sorted(c), key=lambda f: (c[f], -FACES.index(f))) for m, c in dom.items()}


def assign(groups, rects, ox, oy, w, h, cap, exact=True):
    """logic face of a module = the face holding most of its partner-assigned pins in the FINAL assignment (iterated to a
    fixed point, start = each group's uncapacitated best face)."""
    cost = {b: {f: face_cost(f, d["targets"], rects, ox, oy, w, h) for f in FACES}
            for b, d in groups.items() if d["targets"]}
    dom = {}
    for b, d in groups.items():
        if d["targets"]:
            f = min(FACES, key=lambda f: (cost[b][f], FACES.index(f)))
            dom.setdefault(d["module"], {}).setdefault(f, 0)
            dom[d["module"]][f] += len(d["names"])
    logic_face = {m: max(sorted(c), key=lambda f: (c[f], -FACES.index(f))) for m, c in dom.items()}
    seen = []
    while True:
        out, caps = _assign(groups, cost, w, h, cap, logic_face, exact)
        lf = module_faces(out, groups)
        if lf == logic_face or lf in seen or not exact:
            return out, caps, logic_face, cost
        seen.append(logic_face)
        logic_face = lf


def _assign(groups, cost, w, h, cap, logic_face, exact):
    caps = {f: cap_of(f, w, h, cap) for f in FACES}
    out = {f: [] for f in FACES}          # face -> [(bus, name)]
    left = dict(caps)
    # 1. logic-face groups first (status / reset / unmapped pins next to their module's logic)
    for b in sorted(b for b, d in groups.items() if not d["targets"]):
        d = groups[b]
        f = logic_face.get(d["module"]) or "N"
        for n in d["names"]:
            if left[f] <= 0:
                f = max(FACES, key=lambda x: (left[x], -FACES.index(x)))
            out[f].append((b, n))
            left[f] -= 1
    # 2. partner groups, greedy by regret (best vs second-best face), larger groups first on ties
    order = []
    for b, c in cost.items():
        s = sorted(c.values())
        order.append((-(s[1] - s[0]), -len(groups[b]["names"]), b))
    order.sort()
    for _, _, b in order:
        names = list(groups[b]["names"])
        for f in sorted(FACES, key=lambda f: (cost[b][f], FACES.index(f))):
            k = min(left[f], len(names))
            if k <= 0:
                continue
            out[f] += [(b, n) for n in names[:k]]
            names = names[k:]
            left[f] -= k
            if not names:
                break
        if names:
            raise SystemExit(f"{b}: {len(names)} pins do not fit the faces (caps {caps})")
    if exact:
        improve(out, cost, left)
    return out, caps


def improve(out, cost, left):
    """exact transportation optimum: cancel negative cycles / augmenting paths in the 4-face residual graph.
    edge f->g = move one pin of the cheapest-to-move partner group from face f to face g; a cycle visits each face
    once, so the group choices of its edges are independent.  Paths must end on a face with free capacity."""
    import itertools
    while True:
        cnt = {f: {} for f in FACES}
        for f in FACES:
            for b, n in out[f]:
                if b in cost:
                    cnt[f][b] = cnt[f].get(b, 0) + 1

        def edge(f, g):
            best = None
            for b in sorted(cnt[f]):
                d = cost[b][g] - cost[b][f]
                if best is None or d < best[0] - 1e-9:
                    best = (d, b)
            return best
        cand = []
        for k in range(2, 5):
            for seq in itertools.permutations(FACES, k):
                es = [edge(seq[i], seq[i + 1]) for i in range(k - 1)]
                if any(e is None for e in es):
                    continue
                # open path (ends on a face with room) ...
                if left[seq[-1]] > 0:
                    gain = sum(e[0] for e in es)
                    amt = min([cnt[seq[i]][es[i][1]] for i in range(k - 1)] + [left[seq[-1]]])
                    cand.append((gain, seq, tuple(e[1] for e in es), amt, False))
                # ... or closed cycle
                ec = edge(seq[-1], seq[0])
                if ec is not None:
                    es2 = es + [ec]
                    gain = sum(e[0] for e in es2)
                    amt = min(cnt[seq[i]][es2[i][1]] for i in range(k))
                    cand.append((gain, seq + (seq[0],), tuple(e[1] for e in es2), amt, True))
        cand = [c for c in cand if c[0] < -1e-6 and c[3] > 0]
        if not cand:
            return
        gain, seq, bs, amt, closed = min(cand, key=lambda c: (c[0] * c[3], c[1], c[2]))
        for i, b in enumerate(bs):
            f, g = seq[i], seq[i + 1]
            names = [r for r in out[f] if r[0] == b][-amt:]
            for r in names:
                out[f].remove(r)
            out[g] += names
            left[f] += amt
            left[g] -= amt


def place(out, groups, rects, ox, oy, w, h):
    pins = []
    for f in FACES:
        rows = out[f]
        if not rows:
            continue

        def key(r):
            b, n = r
            d = groups[b]
            ts = d["targets"]
            if ts:
                c = sum(((rects[t][0] + rects[t][2]) / 2 - ox) if f in "NS" else ((rects[t][1] + rects[t][3]) / 2 - oy)
                        for t in ts) / len(ts)
            else:
                c = None
            return c, b, bit_of(n)
        # logic-face groups take the mean position of their module's partner pins on that face
        mod_pos = {}
        for r in rows:
            c, b, _ = key(r)
            if c is not None:
                mod_pos.setdefault(groups[b]["module"], []).append(c)
        L = face_len(f, w, h)
        ks = []
        for r in rows:
            c, b, i = key(r)
            if c is None:
                v = mod_pos.get(groups[b]["module"])
                c = sum(v) / len(v) if v else L / 2
            ks.append((min(max(c, 0.0), L), b, i, r[1]))
        ks.sort()
        lo, hi = tracks(f, w, h)
        n = len(ks)
        if n > (hi - lo + 1) // 3 + 1:
            raise SystemExit(f"face {f}: {n} pins exceed one pin per 3 tracks")
        prev = None
        for j, (_, _, _, name) in enumerate(ks):
            t = lo + int(round((j + 0.5) * (hi - lo) / n))
            if prev is not None and t <= prev:
                t = prev + 1
            prev = t
            c = round(OFFS + t * PITCH, 6)
            x, y = face_xy(f, c, w, h)
            pins.append(dict(name=name, layer=LAYER[f], x=x, y=y))
    return pins


def snap_entry(cx, cy, w, h):
    lo, hi = CORE_MARGIN + 1.0, w - CORE_MARGIN - 1.0
    cx = min(max(cx, lo), hi)
    cy = min(max(cy, CORE_MARGIN + 1.0), h - CORE_MARGIN - 1.0)
    x = round(OFFS + round((cx - OFFS) / PITCH) * PITCH, 6)
    y = round(round(cy / ENTRY_GRID) * ENTRY_GRID, 6)
    return x, y


def wirelength(pins, groups, rects, ox, oy):
    by = {}
    for p in pins:
        d = groups.get(bus_of(p["name"]))
        if not d or not d["targets"]:
            continue
        v = sum(rect_dist(ox + p["x"], oy + p["y"], rects[t]) for t in d["targets"]) / len(d["targets"])
        by.setdefault(",".join(d["targets"]), []).append(v)
    return by


def face_of(p, w, h):
    d = [(p["x"], "W"), (w - p["x"], "E"), (p["y"], "S"), (h - p["y"], "N")]
    return min(d)[1]


def build(a):
    plan = load(a.plan)
    old = load(a.pins)
    conns = load(a.conns)[a.type][a.inst]
    slot = slot_of(plan, a.type, a.inst)
    (sx, sy), (sw, sh) = slot["origin_um"], slot["outline_um"]
    if slot.get("orient", "R0") != "R0":
        raise SystemExit("core_tx_plan: R0 slot expected")
    rects = partner_rects(plan, a.type)
    rects.pop("core:" + a.inst, None)
    groups = groups_of(old, conns)
    npins = sum(len(d["names"]) for d in groups.values())
    side = a.side or choose_side(npins, a.cap, a.slack)
    if side > min(sw, sh) + 1e-6:
        raise SystemExit(f"side {side} does not fit the old slot {sw}x{sh}")
    w = h = side
    nx, ny = int(round((sw - w) / GRID)), int(round((sh - h) / GRID))
    quick = []
    for i in range(nx + 1):
        for j in range(ny + 1):
            ox, oy = round(sx + i * GRID, 4), round(sy + j * GRID, 4)
            out, _, _, _ = assign(groups, rects, ox, oy, w, h, a.cap, exact=False)
            pins = place(out, groups, rects, ox, oy, w, h)
            quick.append((sum(sum(v) for v in wirelength(pins, groups, rects, ox, oy).values()), ox, oy))
    quick.sort()
    best = None
    for _, ox, oy in quick[:3]:          # exact assignment on the 3 best greedy anchors
        out, caps, lf, cost = assign(groups, rects, ox, oy, w, h, a.cap)
        pins = place(out, groups, rects, ox, oy, w, h)
        wl = sum(sum(v) for v in wirelength(pins, groups, rects, ox, oy).values())
        if best is None or wl < best[0] - 1e-6:
            best = (wl, ox, oy, out, caps, lf, pins)
    wl, ox, oy, out, caps, lf, pins = best
    data = [p for p in pins]
    cx = sum(p["x"] for p in data) / len(data)
    cy = sum(p["y"] for p in data) / len(data)
    ex, ey = snap_entry(cx, cy, w, h)
    ck = next(p for p in old["pins"] if p["name"] in CLOCK_PINS)
    pins.append(dict(name=ck["name"], layer=ck["layer"], x=ex, y=ey))
    pins.sort(key=lambda p: (FACES.index(face_of(p, w, h)) if p["name"] not in CLOCK_PINS else 9, p["x"], p["y"]))
    names_old = sorted(p["name"] for p in old["pins"])
    if sorted(p["name"] for p in pins) != names_old:
        raise SystemExit("pin set changed")
    win = {}
    for f in FACES:
        cs = sorted((p["x"] if f in "NS" else p["y"]) for p in pins if p["name"] not in CLOCK_PINS and face_of(p, w, h) == f)
        win[f] = round(max((bisect.bisect_right(cs, c + WINDOW) - bisect.bisect_left(cs, c) for c in cs), default=0)
                       / WINDOW, 2)
        if win[f] > a.window_cap + 1e-9:
            raise SystemExit(f"face {f}: {win[f]} pins/um in a {WINDOW:g}-um window > {a.window_cap}")
    fc = {f: sum(1 for p in pins if p["name"] not in CLOCK_PINS and face_of(p, w, h) == f) for f in FACES}
    dens = {f: round(fc[f] / (face_len(f, w, h) - 2 * KEEP), 3) for f in FACES}
    outd = Path(a.out_dir)
    outd.mkdir(parents=True, exist_ok=True)
    pf = outd / f"qkd_hr_core_tx_pins_{a.tag}.json"
    doc = dict(schema=old["schema"], core=old["core"],
               frame=f"core R0, origin (0,0), outline {w:g} x {h:g}",
               source=old["source"] + f" | DIE-KV-14a core_tx_plan.py {a.tag}: outline {w:g}x{h:g}, 4-face pins <= {a.cap:g}/um "
                      "(partner-cost faces; status/reset pins on their module's logic face), ck[0] at the pin-register centroid",
               faces={f: {"pins": fc[f], "layers": [LAYER[f]]} for f in FACES if fc[f]},
               pins=pins)
    pf.write_text(json.dumps(doc, indent=1) + "\n")
    # old geometry for the parent wire-length delta
    ow, oh = sw, sh
    wl_old = wirelength([p for p in old["pins"] if p["name"] not in CLOCK_PINS], groups, rects, sx, sy)
    wl_new = wirelength([p for p in pins if p["name"] not in CLOCK_PINS], groups, rects, ox, oy)
    fold = {p["name"]: face_of(p, ow, oh) for p in old["pins"] if p["name"] not in CLOCK_PINS}
    fnew = {p["name"]: face_of(p, w, h) for p in pins if p["name"] not in CLOCK_PINS}
    per = {}
    for b, d in sorted(groups.items()):
        k = ",".join(d["targets"]) if d["targets"] else "logic-face(" + d["module"] + ")"
        r = per.setdefault(k, dict(pins=0, face_changes={}))
        for n in d["names"]:
            r["pins"] += 1
            if fold[n] != fnew[n]:
                t = fold[n] + "->" + fnew[n]
                r["face_changes"][t] = r["face_changes"].get(t, 0) + 1
    for k, v in wl_new.items():
        per[k]["wl_old_um"] = round(sum(wl_old[k]), 1)
        per[k]["wl_new_um"] = round(sum(v), 1)
        per[k]["mean_old_um"] = round(sum(wl_old[k]) / len(wl_old[k]), 1)
        per[k]["mean_new_um"] = round(sum(v) / len(v), 1)
    corners = [(CORE_MARGIN, CORE_MARGIN), (w - CORE_MARGIN, CORE_MARGIN), (CORE_MARGIN, h - CORE_MARGIN),
               (w - CORE_MARGIN, h - CORE_MARGIN)]
    reach = max(abs(ex - x) + abs(ey - y) for x, y in corners)
    delta = dict(
        schema="opentallas.kv.core_tx_plan_delta.v1", tool="physical/die_plan/qwen_kvsys/cores/core_tx_plan.py",
        type=a.type, inst=a.inst, module=slot.get("module"),
        inputs=dict(plan=str(a.plan), plan_sha256=sha(a.plan), pins=str(a.pins), pins_sha256=sha(a.pins),
                    conns=str(a.conns), conns_sha256=sha(a.conns)),
        params=dict(cap_per_um=a.cap, slack=a.slack, grid_um=GRID, keepout_um=KEEP),
        old=dict(origin_um=[sx, sy], outline_um=[sw, sh], pins_file=slot.get("pins_file"),
                 clock_entry_um=[ck["x"], ck["y"]]),
        new=dict(origin_um=[ox, oy], outline_um=[w, h], pins_file=pf.name, pins_sha256=sha(pf),
                 clock_entry_um=[ex, ey], clock_tap_xy_parent=[round(ox + ex, 4), round(oy + ey, 4)]),
        inside_old_slot=bool(ox >= sx - 1e-6 and oy >= sy - 1e-6 and ox + w <= sx + sw + 1e-6 and oy + h <= sy + sh + 1e-6),
        pins=len(pins), face_pins=fc, face_pins_per_um=dens, face_window_pins_per_um=win, face_caps=caps, logic_face=lf,
        pin_centroid_um=[round(cx, 3), round(cy, 3)],
        clock_reach_bound_um=round(reach, 2),
        r2r_bound_um=round(2 * (w - 2 * CORE_MARGIN), 2),
        partner_wl=per,
        partner_wl_total_um=dict(old=round(sum(sum(v) for v in wl_old.values()), 1),
                                 new=round(sum(sum(v) for v in wl_new.values()), 1)))
    (outd / "core_tx_plan_delta.json").write_text(json.dumps(delta, indent=1, sort_keys=True) + "\n")
    return delta


def apply(a):
    plan = load(a.plan)
    delta = json.loads(Path(a.delta).read_text())
    new = delta["new"]
    out = Path(a.out)
    pins_src = Path(a.delta).parent / new["pins_file"]
    if sha(pins_src) != new["pins_sha256"]:
        raise SystemExit("pins file sha mismatch")
    hc = slot_of(plan, delta["type"], delta["inst"])
    if [round(v, 4) for v in hc["outline_um"]] != delta["old"]["outline_um"] or hc["origin_um"] != delta["old"]["origin_um"]:
        raise SystemExit(f"plan slot {hc['origin_um']} {hc['outline_um']} is not the delta's old slot")
    hc["origin_um"] = new["origin_um"]
    hc["outline_um"] = new["outline_um"]
    hc["pins_file"] = _rel(pins_src.resolve(), out.resolve().parent)
    hc["note"] = hc.get("note", "") + (f" | DIE-KV-14a core_tx_plan.py: outline {new['outline_um'][0]:g}x"
                                        f"{new['outline_um'][1]:g} inside the old slot, 4-face pins, ck entry at logic centroid")
    clk = plan["partition_types"][delta["type"]].get("clock", {})
    hit = 0
    for t in clk.get("taps", []):
        if t.get("name") == f"{delta['inst']}.ck[0]":
            t["xy"] = new["clock_tap_xy_parent"]
            t["note"] = t.get("note", "") + " | DIE-KV-14a: entry moved to the core_tx logic centroid"
            hit += 1
    if hit != 1:
        raise SystemExit(f"clock tap {delta['inst']}.ck[0]: {hit} matches")
    out.write_text(json.dumps(plan, indent=1) + "\n")
    return hc


def _rel(target, base):
    import os
    return os.path.relpath(target, base)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--plan", required=True)
    b.add_argument("--pins", required=True)
    b.add_argument("--conns", required=True)
    b.add_argument("--out-dir", required=True)
    b.add_argument("--type", default="kv3_hub_Wi")
    b.add_argument("--inst", default="host__qkd_hr_core_tx")
    b.add_argument("--cap", type=float, default=5.9, help="pin budget per um of usable face (mean)")
    b.add_argument("--window-cap", type=float, default=6.0, help="max pins/um in any 10-um face window (fail closed)")
    b.add_argument("--slack", type=float, default=0.03, help="spare pin capacity when the side is chosen automatically")
    b.add_argument("--side", type=float, default=None, help="square outline side (um); default = smallest fitting grid side")
    b.add_argument("--tag", default="r26q14")
    p = sub.add_parser("apply")
    p.add_argument("--plan", required=True)
    p.add_argument("--delta", required=True)
    p.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "build":
        d = build(a)
        print(json.dumps({k: d[k] for k in ("new", "face_pins", "face_pins_per_um", "face_window_pins_per_um", "logic_face", "inside_old_slot",
                                            "clock_reach_bound_um", "r2r_bound_um", "partner_wl_total_um")}))
    else:
        hc = apply(a)
        print(json.dumps({k: hc[k] for k in ("inst", "origin_um", "outline_um", "pins_file")}))


if __name__ == "__main__":
    sys.exit(main())
