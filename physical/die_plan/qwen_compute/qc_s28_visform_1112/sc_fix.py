#!/usr/bin/env python3
"""QC-S28-VISFORM SC-ECHAN-FT (11-12): sc family form, part 2 of SC-ECHAN.

SC-ECHAN moved u_core W (x 345.6 -> 302.4) to open a 66-um E channel and pushed the ft stations on the core's W
flank W with it.  W->E slots whose LAST station sits on that flank (x in [core.x0 - FLANK, core.x0), block rows
overlapping the core's y band) then cross the whole core plus the E channel in one leg to the E window pin
(G0 hops 407-439 um on x_stm_fe / x_fw_fe / x_fw_fe_p2 after stations_hf1c).

Form: on every sc type (^(sle|slw)_sc_), each W->E slot with a flank-hugging last station gets that station
(regs_um[k-1] + its bit block bit_sites_um[k-2]) re-sited rigidly (dx on the 2.16-um column lattice, dy on the
0.27-um row lattice) to the legal spot that minimises max(prev->last, last->E window centre):
  candidates: dx = 0 .. E edge, dy in {0, toward prev station y, toward out-window centre y};
  legal: block (+1.404 x 0.27 cells) clear of every hard core by HALO and inside the outline;
  taken only if the new max leg is <= LIMIT and below the current max leg; else the slot is left as is.
Bits that land on another slot's bit cell are legalised to the nearest free lattice site (visform.Occ).

  sc_fix.py derive PLAN DELTA [--report R]    (apply with visform.py apply PLAN DELTA OUT)
"""
import argparse, json, hashlib, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import visform as V

FLANK = 8.0          # um W of core.x0 that counts as "on the flank"
LIMIT = 380.0        # trigger: slots whose current max leg exceeds this (lane reach 405 minus the next S0 leg margin)
TARGET = 360.0       # re-site goal: smallest move whose max leg is <= TARGET (else the minimax spot, if <= LIMIT)
CW, CH = 1.404, 0.27


def snap(v, g):
    return round(round(v / g) * g, 6)


def legs(prev, r, W, outc):
    return abs(r[0] - prev[0]) + abs(r[1] - prev[1]), (W - r[0]) + abs(r[1] - outc)


def bbox(b):
    xs = [p[0] for p in b]; ys = [p[1] for p in b]
    return min(xs), min(ys), max(xs) + CW, max(ys) + CH


def overl(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def fix_type(tn, t, ops, rows, plan):
    W, H = t["outline_um"]
    cores = [V.rect_of(h) for h in t.get("hard_cores") or []]
    if not cores:
        return
    core = max(cores, key=lambda r: (r[2] - r[0]) * (r[3] - r[1]))
    halo = [(r[0] - V.HALO, r[1] - V.HALO, r[2] + V.HALO, r[3] + V.HALO) for r in cores]
    slots = t.get("ft_slots") or []
    blocks = [(j, m, bbox(b2)) for j, s2 in enumerate(slots) for m, b2 in enumerate(s2.get("bit_sites_um") or []) if b2]
    for i, s in enumerate(slots):
        if s.get("in_face") != "W" or s.get("out_face") != "E":
            continue
        regs, bits = s.get("regs_um") or [], s.get("bit_sites_um") or []
        k = len(regs)
        if k < 2 or len(bits) != k - 1:
            continue
        last, prev, blk = regs[-1], regs[-2], bits[-1]
        bb = bbox(blk)
        if not (core[0] - FLANK <= last[0] < core[0] and bb[1] < core[3] and bb[3] > core[1]):
            continue
        ow = s["out_window_um"]; outc = (ow[0] + ow[1]) / 2
        cur = max(legs(prev, last, W, outc))
        if cur <= LIMIT:
            continue
        others = [r for j, m, r in blocks if not (j == i and m == len(bits) - 1)]
        best = None
        dys = {0.0, snap(prev[1] - last[1], 0.27), snap(outc - last[1], 0.27)}
        nmax = int((W - bb[2]) // 2.16)
        for n in range(0, nmax + 1):
            dx = round(n * 2.16, 6)
            for dy in dys:
                nb = (bb[0] + dx, bb[1] + dy, bb[2] + dx, bb[3] + dy)
                if nb[0] < 0 or nb[2] > W or nb[1] < 0 or nb[3] > H or any(overl(nb, h) for h in halo):
                    continue
                r = [round(last[0] + dx, 6), round(last[1] + dy, 6)]
                a, b = legs(prev, r, W, outc)
                # clear of other blocks first, then: within TARGET -> smallest move; else minimax
                clash = any(overl(nb, o) for o in others)
                mx = round(max(a, b), 3)
                key = (clash, 0 if mx <= TARGET else 1, (dx + abs(dy)) if mx <= TARGET else mx, mx)
                if best is None or key < best[0]:
                    best = (key, dx, dy, r, a, b)
        row = dict(type=tn, slot=s["name"], stations=k, last=last, cur_max=round(cur, 1))
        if best is None or best[0][3] > LIMIT or best[0][3] >= cur - 1.0:
            row.update(action="keep", best=None if best is None else round(best[0][3], 1))
            rows.append(row)
            continue
        _, dx, dy, r, a, b = best
        occ = V.Occ()
        for j, s2 in enumerate(slots):
            for m, b2 in enumerate(s2.get("bit_sites_um") or []):
                if j == i and m == len(bits) - 1:
                    continue
                for p in b2:
                    occ.add(p)
        moved, nleg = [], 0

        def ok(q):
            return not any(V.inside(q, c, 0.0) for c in halo) and 0 <= q[0] <= W - CW and 0 <= q[1] <= H - CH
        for p in blk:
            q = [round(p[0] + dx, 6), round(p[1] + dy, 6)]
            if occ.hit(q) or not ok(q):
                q = occ.nearest(q, ok); nleg += 1
            occ.add(q); moved.append(q)
        nregs = [list(x) for x in regs[:-1]] + [r]
        nbits = [list(x) for x in bits[:-1]] + [moved]
        base = ["partition_types", tn, "ft_slots", i]
        V.op(ops, "SC-ECHAN-FT", plan, base + ["regs_um"], nregs)
        V.op(ops, "SC-ECHAN-FT", plan, base + ["bit_sites_um"], nbits)
        row.update(action="move", dx=dx, dy=dy, new=r, prev_leg=round(a, 1), last_leg=round(b, 1),
                   new_max=round(max(a, b), 1), bits=len(blk), bits_relegalised=nleg, block_clash=best[0][0])
        rows.append(row)


def derive(a):
    plan = json.loads(Path(a.plan).read_text())
    ops, rows = [], []
    for tn in sorted(plan["partition_types"]):
        if V.SC_RE.match(tn):
            fix_type(tn, plan["partition_types"][tn], ops, rows, plan)
    psha = hashlib.sha256(Path(a.plan).read_bytes()).hexdigest()
    d = dict(schema="qc_s28_visform.delta.v1", base_plan_sha256=psha, form="SC-ECHAN-FT", ops=ops)
    Path(a.delta).write_text(json.dumps(d, indent=1) + "\n")
    if a.report:
        Path(a.report).write_text(json.dumps(dict(plan=psha, rows=rows), indent=1) + "\n")
    for r in rows:
        print(r["type"], r["slot"], r["action"], r["cur_max"], "->", r.get("new_max", r.get("best")),
              r.get("dx", ""), r.get("dy", ""), r.get("bits_relegalised", ""))
    print("OPS", len(ops), "moved", sum(r["action"] == "move" for r in rows), "kept", sum(r["action"] == "keep" for r in rows))


def main(argv=None):
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    d = sp.add_parser("derive"); d.add_argument("plan"); d.add_argument("delta"); d.add_argument("--report")
    a = ap.parse_args(argv)
    derive(a)


if __name__ == "__main__":
    main()
