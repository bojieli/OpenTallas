#!/usr/bin/env python3
"""S81 stage B2 HOP-RESPACE-1112 (DIE-S81-87 ready12b re-sign batch, OWNER 11-12 04:37 re-plan signed types).

composer stage contract:  hop_respace_1112.py IN OUT REPORT --types T1,T2,...   (cwd = repo root)
  declared type_keys ["internal_stations", "ft_slots"], top_keys [].
For each listed type, every register chain with a hop > MAX (405 um, Manhattan) is SLID minimally along its own
existing route (the polyline through its current points, each leg taken x-then-y), keeping the end points and the
register COUNT (no cycle change):
  internal_stations[i]: chain from_um, regs_um..., to_um; from/to fixed, every reg moves.
  ft_slots[i]:          chain regs_um (as DIEREVIEW counts it); first and last reg fixed, the others move; each reg's
                        bit_sites_um cluster (matched to its reg by nearest centroid: < 80 um and the 2nd-nearest reg >= 3x as far) moves with it.
A chain with no legal slide (internal stations also try off-route grid points within 300 um) is LEFT UNCHANGED and
listed in needs_register_unchanged (a register = cycle change, REACH-FIX-1 class, not this stage).
Fail-closed (exit 1, nothing written): a type not in the plan; a moved reg or bit site outside the outline or inside a hard-core or physical-macro (contents) rectangle; ambiguous bit-site match;
any change outside the declared keys.  Idempotent: a chain with no hop > MAX is never touched.
"""
import argparse, copy, hashlib, json, sys
from pathlib import Path

EVENT = "HOP-RESPACE-1112"
MAX = 405.0
ROT = {"R90", "R270", "MXR90", "MYR90"}


def md(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


GAP = 403.0      # target hop after the move (2 um under MAX)


def on_leg(a, b, s, xfirst):
    """point at Manhattan distance s from a towards b; leg x-then-y (or y-then-x)."""
    i, j = (0, 1) if xfirst else (1, 0)
    d1 = abs(b[i] - a[i])
    p = list(a)
    if s <= d1:
        p[i] = a[i] + (s if b[i] >= a[i] else -s)
    else:
        p[i] = b[i]
        r = s - d1
        p[j] = a[j] + (r if b[j] >= a[j] else -r)
    return [round(p[0], 3), round(p[1], 3)]


def respace(pts, legal, step=4.0, win=450.0, grid=0.0):
    """end points fixed, register COUNT fixed.  Each inner point k may move to a LEGAL sample of the chain's own route
    (each leg x-then-y or y-then-x, arc step `step`, within +-`win` of its own arc position) or stay; dynamic program
    over the samples with every consecutive Manhattan hop <= GAP, minimising the summed displacement.
    Returns (new points or None if infeasible, mean hop)."""
    L = [md(a, b) for a, b in zip(pts, pts[1:])]
    cum = [0.0]
    for x in L:
        cum.append(cum[-1] + x)
    n = len(pts) - 1
    def sample(sv):
        seg = max(i for i in range(n) if cum[i] <= sv + 1e-9)
        return [on_leg(pts[seg], pts[seg + 1], sv - cum[seg], xf) for xf in (True, False)]
    C = [[list(pts[0])]]
    for k in range(1, n):
        cand = [list(pts[k])] if legal(k, pts[k]) is None else []
        sv = max(0.0, cum[k] - win)
        while sv <= min(cum[-1], cum[k] + win):
            for q in sample(sv):
                if q not in cand and legal(k, q) is None:
                    cand.append(q)
            sv += step
        if grid:      # off-route fallback: legal grid points within +-win of the reg (Manhattan)
            gx = pts[k][0] - win
            while gx <= pts[k][0] + win:
                gy = pts[k][1] - win
                while gy <= pts[k][1] + win:
                    q = [round(gx, 3), round(gy, 3)]
                    if md(q, pts[k]) <= win and q not in cand and legal(k, q) is None:
                        cand.append(q)
                    gy += grid
                gx += grid
        C.append(cand)
    C.append([list(pts[-1])])
    INF = float("inf")
    cost = [[0.0]]
    back = [[None]]
    for k in range(1, n + 1):
        ck, bk = [], []
        for q in C[k]:
            disp = md(q, pts[k])
            best, arg = INF, None
            for j, pq in enumerate(C[k - 1]):
                if cost[k - 1][j] < best and md(pq, q) <= GAP:
                    best, arg = cost[k - 1][j], j
            ck.append(best + disp); bk.append(arg)
        cost.append(ck); back.append(bk)
    if cost[n][0] == INF:
        return None, cum[-1] / n
    out, j = [], 0
    for k in range(n, -1, -1):
        out.append(C[k][j])
        j = back[k][j] if k else None
    return out[::-1], cum[-1] / n


def rects(t):
    out = []
    for c in (t.get("hard_cores") or []) + [m for m in (t.get("contents") or []) if m.get("outline_um") and m.get("origin_um")]:
        w, h = c["outline_um"]
        if c.get("orient", "R0") in ROT:
            w, h = h, w
        x, y = c["origin_um"]
        out.append((c["inst"], x, y, x + w, y + h))
    return out


def inside(p, R, W, H):
    if not (0 <= p[0] <= W and 0 <= p[1] <= H):
        return "outside outline"
    for n, x0, y0, x1, y1 in R:
        if x0 < p[0] < x1 and y0 < p[1] < y1:
            return f"under core {n}"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp"); ap.add_argument("out"); ap.add_argument("report")
    ap.add_argument("--types", required=True)
    a = ap.parse_args()
    raw = Path(a.inp).read_bytes()
    plan = json.loads(raw)
    dump = None
    for f in (lambda d: json.dumps(d) + "\n", lambda d: json.dumps(d, indent=1) + "\n"):
        if f(plan).encode() == raw:
            dump = f
    if dump is None:
        sys.exit("REFUSED: plan not in json.dumps form")
    T = plan["partition_types"]
    types = [t for t in a.types.split(",") if t]
    miss = [t for t in types if t not in T]
    if miss:
        sys.exit(f"REFUSED: types not in plan {miss}")
    problems, moves, need_reg = [], [], []
    for tn in types:
        t = T[tn]
        W, H = t["outline_um"]
        R = rects(t)
        for i, s in enumerate(t.get("internal_stations") or []):
            pts = [s["from_um"]] + s.get("regs_um", []) + [s["to_um"]]
            hops = [md(x, y) for x, y in zip(pts, pts[1:])]
            if max(hops) <= MAX:
                continue
            new, per = respace(pts, lambda k, q: inside(q, R, W, H))
            if new is None:
                new, per = respace(pts, lambda k, q: inside(q, R, W, H), win=300.0, grid=4.32)
            if new is None:
                need_reg.append(dict(type=tn, kind="internal_stations", index=i, conn=s["conn"], hops=[round(h, 1) for h in hops],
                                     why=f"no legal position for {len(pts)-2} regs (on-route or +-300 um grid): +1 register (cycle)"))
                continue
            for k, p in enumerate(new[1:-1]):
                why = inside(p, R, W, H)
                if why:
                    problems.append(f"{tn} IST{i} reg{k} {p}: {why}")
            moves.append(dict(type=tn, kind="internal_stations", index=i, conn=s["conn"], before=pts, after=new,
                              hops_before=[round(h, 1) for h in hops],
                              hops_after=[round(md(x, y), 1) for x, y in zip(new, new[1:])]))
            s["regs_um"] = new[1:-1]
        for i, s in enumerate(t.get("ft_slots") or []):
            rg = s.get("regs_um") or []
            if len(rg) < 3:
                continue
            hops = [md(x, y) for x, y in zip(rg, rg[1:])]
            if max(hops) <= MAX:
                continue
            bs = s.get("bit_sites_um")
            owner = {}
            if bs:
                for c, cl in enumerate(bs):
                    cx = sum(q[0] for q in cl) / len(cl); cy = sum(q[1] for q in cl) / len(cl)
                    d = sorted((md((cx, cy), r), k) for k, r in enumerate(rg))
                    if d[0][0] > 80 or (len(d) > 1 and d[1][0] < 3 * d[0][0]):
                        problems.append(f"{tn} FT{i} bit cluster {c}: no unique reg (d {d[:2]})")
                        continue
                    if d[0][1] in owner.values():
                        problems.append(f"{tn} FT{i} bit cluster {c}: reg {d[0][1]} has two clusters")
                    owner[c] = d[0][1]
            box = {}
            for c, k in owner.items():
                cl = bs[c]
                box[k] = (min(q[0] for q in cl) - rg[k][0], min(q[1] for q in cl) - rg[k][1],
                          max(q[0] for q in cl) - rg[k][0], max(q[1] for q in cl) - rg[k][1])

            def legal_ft(k, q):
                why = inside(q, R, W, H)
                if why or k not in box:
                    return why
                bx = box[k]
                x0, y0, x1, y1 = q[0] + bx[0], q[1] + bx[1], q[0] + bx[2], q[1] + bx[3]
                if x0 < 0 or y0 < 0 or x1 > W or y1 > H:
                    return "bit sites outside outline"
                for nme, a0, b0, a1, b1 in R:
                    if x0 < a1 and a0 < x1 and y0 < b1 and b0 < y1:
                        return f"bit sites under core {nme}"
                return None
            new, per = respace(rg, legal_ft)
            if new is None:
                need_reg.append(dict(type=tn, kind="ft_slots", index=i, name=s["name"], hops=[round(h, 1) for h in hops],
                                     why=f"no legal on-route slide for {len(rg)} regs: +1 register (cycle) = REACH-FIX-1 class"))
                continue
            for k in range(1, len(rg) - 1):
                why = inside(new[k], R, W, H)
                if why:
                    problems.append(f"{tn} FT{i} reg{k} {new[k]}: {why}")
            if bs:
                nb = []
                for c, cl in enumerate(bs):
                    k = owner.get(c)
                    if k is None:
                        nb.append(cl); continue
                    dx, dy = new[k][0] - rg[k][0], new[k][1] - rg[k][1]
                    moved = [[round(q[0] + dx, 3), round(q[1] + dy, 3)] for q in cl]
                    for q in (moved[0], moved[-1], min(moved), max(moved)):
                        why = inside(q, R, W, H)
                        if why:
                            problems.append(f"{tn} FT{i} bit cluster {c} site {q}: {why}")
                            break
                    nb.append(moved)
                s["bit_sites_um"] = nb
            moves.append(dict(type=tn, kind="ft_slots", index=i, name=s["name"], before=rg, after=new,
                              hops_before=[round(h, 1) for h in hops],
                              hops_after=[round(md(x, y), 1) for x, y in zip(new, new[1:])]))
            s["regs_um"] = new
    # declared keys only
    chk = json.loads(json.dumps(plan))
    base = json.loads(raw)
    for tn in types:
        for k in ("internal_stations", "ft_slots"):
            if k in base["partition_types"][tn]:
                chk["partition_types"][tn][k] = base["partition_types"][tn][k]
    if chk != base:
        problems.append("changed keys outside internal_stations/ft_slots")
    rep = dict(event=EVENT, max_hop_um=MAX, types=types, moves=moves, needs_register_unchanged=need_reg, problems=problems,
               plan_in_sha256=hashlib.sha256(raw).hexdigest())
    if problems:
        Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
        print(f"{EVENT}: FAIL-CLOSED {len(problems)} problems: {problems[:6]}")
        sys.exit(1)
    out = dump(plan).encode()
    rep["plan_out_sha256"] = hashlib.sha256(out).hexdigest()
    Path(a.out).write_bytes(out)
    Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    print(f"{EVENT}: {len(need_reg)} chains left unchanged (need a register); {len(moves)} chains slid in {len({m['type'] for m in moves})} types, no register added")


if __name__ == "__main__":
    main()
