#!/usr/bin/env python3
"""HARD-QC-FORMS-1 guarded form delta.  usage: hqf_apply.py PLAN_IN FORM.json PLAN_OUT REPORT.json
FORM = {"name":..., "ops":[...]}.  ops:
  {"op":"move_core","type":T,"inst":I,"from":[x,y],"to":[x,y],"from_orient":O,"to_orient":O2}
      moves the hard core; the matching contents[] origin and every plan point of the type that lies inside the old
      core rectangle (core taps, pin-side station ends, footprints) move by the same vector (rigid).  A rotation or
      mirror is allowed only for a core with no such interior points (LEF memory macros).
      "rigid": false (LEF memory macros): no plan point moves with the core; the report lists the plan points now
      under the new rectangle (relay / strap / station sites the die owner's re-site step must clear).
  {"op":"shift_ft","type":T,"slot":S,"box":[x0,y0,x1,y1],"d":[dx,dy],"from_regs":[...]}
      moves the planned stations (regs_um and their bit_sites_um) of one ft slot that lie inside box by d.
  {"op":"add_define","type":T,"define":D}
  {"op":"set","type":T,"path":[k1,k2,...],"from":V,"to":V}      generic guarded scalar / list replace
Guards: every from-value must equal the plan (CONFLICT exit 3) unless the plan already holds the to-value (no-op), so
a second run on its own output is a byte no-op.  No shape (outline_um) is ever written."""
import json, sys, hashlib, copy
PKEYS = {"xy", "xy_um", "from_um", "to_um", "leaf_um", "start_um", "tap_um", "site_um"}
LKEYS = {"regs_um", "sites_um", "bit_sites_um", "relay_sites_um"}
RKEYS = {"rect_um", "origin_rect_um", "footprints_um"}
def near(a, b, tol=1e-6): return abs(a - b) <= tol
def eqv(a, b):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)): return near(a, b)
    if isinstance(a, list) and isinstance(b, list): return len(a) == len(b) and all(eqv(x, y) for x, y in zip(a, b))
    return a == b
def wh(h, orient=None):
    w, hh = h["outline_um"]
    return (hh, w) if (orient or h.get("orient", "R0")) in ("R90", "R270", "MXR90", "MYR90") else (w, hh)
GROW = [0.02]            # rigid moves take the plan points within 4.32 um of the core (pin-side chain ends, core taps: RESID view-zone rule)
def inside(p, r, g=None):
    g = GROW[0] if g is None else g
    return r[0] - g <= p[0] <= r[2] + g and r[1] - g <= p[1] <= r[3] + g
def ispt(v): return isinstance(v, list) and len(v) >= 2 and all(isinstance(x, (int, float)) for x in v[:2])
def walk_move(o, rect, d, cnt, key=None, skip=None):
    """shift points / rects under whitelisted keys that lie inside rect"""
    if isinstance(o, dict):
        for k, v in o.items():
            if skip and (k in skip): continue
            if k in PKEYS and ispt(v) and len(v) in (2, 3):
                if inside(v, rect): v[0] = round(v[0] + d[0], 6); v[1] = round(v[1] + d[1], 6); cnt[k] = cnt.get(k, 0) + 1
            elif k in RKEYS and isinstance(v, list) and len(v) == 4 and all(isinstance(x, (int, float)) for x in v):
                if inside(v[:2], rect) and inside(v[2:], rect):
                    for i in (0, 2): v[i] = round(v[i] + d[0], 6)
                    for i in (1, 3): v[i] = round(v[i] + d[1], 6)
                    cnt[k] = cnt.get(k, 0) + 1
            elif k in LKEYS or k in RKEYS: walk_list(v, rect, d, cnt, k)
            else: walk_move(v, rect, d, cnt, k, skip)
    elif isinstance(o, list):
        for v in o: walk_move(v, rect, d, cnt, key, skip)
def walk_list(v, rect, d, cnt, k):
    if ispt(v) and len(v) in (2, 3):
        if inside(v, rect): v[0] = round(v[0] + d[0], 6); v[1] = round(v[1] + d[1], 6); cnt[k] = cnt.get(k, 0) + 1
    elif k in RKEYS and isinstance(v, list) and len(v) == 4 and all(isinstance(x, (int, float)) for x in v):
        if inside(v[:2], rect) and inside(v[2:], rect):
            for i in (0, 2): v[i] = round(v[i] + d[0], 6)
            for i in (1, 3): v[i] = round(v[i] + d[1], 6)
            cnt[k] = cnt.get(k, 0) + 1
    elif isinstance(v, list):
        for x in v: walk_list(x, rect, d, cnt, k)
    elif isinstance(v, dict) and k in RKEYS:
        # Layer-name maps retain the owning rectangle key; arbitrary four-value lists do not become geometry.
        for x in v.values(): walk_list(x, rect, d, cnt, k)
    elif isinstance(v, dict): walk_move(v, rect, d, cnt, k)
def main():
    pin, form, pout, rep = sys.argv[1:5]
    raw = open(pin, "rb").read(); P = json.loads(raw); F = json.load(open(form)); pt = P["partition_types"]
    R = {"form": F.get("name"), "plan_in_sha256": hashlib.sha256(raw).hexdigest(), "ops": [], "conflicts": []}
    for op in F["ops"]:
        T = pt.get(op["type"])
        if T is None: R["conflicts"].append({"op": op, "why": "no such type"}); continue
        if op["op"] == "move_core":
            hs = [h for h in T.get("hard_cores", []) if h["inst"] == op["inst"]]
            if len(hs) != 1: R["conflicts"].append({"op": op, "why": "core not found"}); continue
            h = hs[0]; fo, to = op["from"], op["to"]; o0 = op.get("from_orient", h.get("orient", "R0")); o1 = op.get("to_orient", o0)
            if eqv(h["origin_um"], to) and h.get("orient", "R0") == o1: R["ops"].append({"op": op, "state": "already"}); continue
            if not (eqv(h["origin_um"], fo) and h.get("orient", "R0") == o0):
                R["conflicts"].append({"op": op, "why": f"from mismatch: plan has {h['origin_um']} {h.get('orient')}"}); continue
            w, hh = wh(h); rect = [fo[0], fo[1], fo[0] + w, fo[1] + hh]; d = [to[0] - fo[0], to[1] - fo[1]]
            rigid = op.get("rigid", True)
            cnt = {}; probe = copy.deepcopy(T); pc = {}; GROW[0] = 4.32 if rigid else 0.02
            walk_move(probe, rect, [0, 0], pc, skip={"hard_cores", "contents"})
            if rigid and o1 != o0 and pc: R["conflicts"].append({"op": op, "why": f"orient change with interior points {pc}"}); continue
            if rigid: walk_move(T, rect, d, cnt, skip={"hard_cores", "contents"})
            GROW[0] = 0.02
            w1, h1 = wh(h, o1); nrect = [to[0], to[1], to[0] + w1, to[1] + h1]; un = {}
            walk_move(copy.deepcopy(T), nrect, [0, 0], un, skip={"hard_cores", "contents"})
            under = {"left_under_old_rect": 0 if rigid else pc, "under_new_rect": un}
            for c in T.get("contents", []):
                if c.get("inst") == op["inst"] and ispt(c.get("origin_um")):
                    c["origin_um"] = [round(c["origin_um"][0] + d[0], 6), round(c["origin_um"][1] + d[1], 6)]; cnt["contents.origin_um"] = 1
            ce = h.get("clock_entry_access")
            if ce: walk_move(ce, [-1e9, -1e9, 1e9, 1e9], d, cnt)
            h["origin_um"] = [to[0], to[1]]; h["orient"] = o1
            R["ops"].append({"op": op, "state": "applied", "moved_points": cnt, "points": under})
        elif op["op"] == "shift_ft":
            fs = [f for f in T.get("ft_slots", []) if f["name"] == op["slot"]]
            if len(fs) != 1: R["conflicts"].append({"op": op, "why": "ft slot not found"}); continue
            f = fs[0]; d = op["d"]; box = op["box"]; regs = f.get("regs_um") or []
            idx = [i for i, p in enumerate(op["from_regs"]) if inside(p, box)]; slim = {k: v for k, v in op.items() if k != "from_regs"}
            if len(regs) != len(op["from_regs"]) or not idx: R["conflicts"].append({"op": slim, "why": "station count mismatch / no station in box"}); continue
            if all(eqv(regs[i][:2], [round(op["from_regs"][i][0] + d[0], 6), round(op["from_regs"][i][1] + d[1], 6)]) for i in idx): R["ops"].append({"op": slim, "state": "already"}); continue
            if not all(eqv(regs[i][:2], op["from_regs"][i][:2]) for i in idx): R["conflicts"].append({"op": slim, "why": "from_regs mismatch"}); continue
            cnt = {}
            for k in ("regs_um", "bit_sites_um"):
                if f.get(k) is not None: walk_list(f[k], box, d, cnt, k)
            R["ops"].append({"op": {k: v for k, v in op.items() if k != "from_regs"}, "state": "applied", "moved_points": cnt})
        elif op["op"] == "add_define":
            L = T.setdefault("verilog_defines", [])
            if op["define"] in L: R["ops"].append({"op": op, "state": "already"})
            else: L.append(op["define"]); R["ops"].append({"op": op, "state": "applied"})
        elif op["op"] == "set":
            o = T
            for k in op["path"][:-1]: o = o[k]
            k = op["path"][-1]; cur = o.get(k) if isinstance(o, dict) else o[k]
            if eqv(cur, op["to"]): R["ops"].append({"op": op, "state": "already"})
            elif eqv(cur, op["from"]): o[k] = op["to"]; R["ops"].append({"op": op, "state": "applied"})
            else: R["conflicts"].append({"op": op, "why": f"from mismatch: plan has {json.dumps(cur)[:200]}"})
        else: R["conflicts"].append({"op": op, "why": "unknown op"})
    # overlap check of every touched type: no two hard cores overlap, all inside the outline
    for t in sorted({op["type"] for op in F["ops"]} & set(pt)):
        T = pt[t]; W, H = T["outline_um"]; rs = []
        for h in T.get("hard_cores", []):
            w, hh = wh(h); x, y = h["origin_um"]; rs.append((h["inst"], x, y, x + w, y + hh))
            if x < -1e-6 or y < -1e-6 or x + w > W + 1e-6 or y + hh > H + 1e-6: R["conflicts"].append({"type": t, "why": f"{h['inst']} outside outline"})
        for i in range(len(rs)):
            for j in range(i + 1, len(rs)):
                a, b = rs[i], rs[j]
                if min(a[3], b[3]) - max(a[1], b[1]) > 1e-6 and min(a[4], b[4]) - max(a[2], b[2]) > 1e-6:
                    R["conflicts"].append({"type": t, "why": f"overlap {a[0]} {b[0]}"})
    out = json.dumps(P, indent=1) if raw.lstrip().startswith(b"{\n") else json.dumps(P)
    R["applied"] = sum(1 for o in R["ops"] if o["state"] == "applied"); R["already"] = sum(1 for o in R["ops"] if o["state"] == "already")
    if R["conflicts"]:
        json.dump(R, open(rep, "w"), indent=1); print("CONFLICT", len(R["conflicts"]), json.dumps(R["conflicts"][:5])[:1500]); sys.exit(3)
    if R["applied"] == 0: out_b = raw
    else: out_b = (out + ("\n" if raw.endswith(b"\n") else "")).encode()
    open(pout, "wb").write(out_b); R["plan_out_sha256"] = hashlib.sha256(out_b).hexdigest()
    json.dump(R, open(rep, "w"), indent=1); print("OK applied", R["applied"], "already", R["already"], "out", R["plan_out_sha256"][:12])
main()
