#!/usr/bin/env python3
"""DIE-LAYOUT-HBM 11-11 (DIE-HBM-100 ask, folded into the CPL-HBM-B1 d6 positions event): planned positions for the
soft hb_idx_s_SE_scorer groups of the HBM bank types, as extra internal_stations rows (positions only, 0 cycles,
EQ by construction: no RTL, no register count, no bus depth change).

kit_bus_bitgroups (TOOLS-2) sites bit b of a bus station chain at the planned route of the core that owns b.  Bits read
(in bus) / launched (out bus) by the scorer soft cells had no planned owner (plan rows attribute them to the pair cores).
For each TYPE:BUS this tool traces the bound RTL (trace_readers.py) and, for each scorer group with >= MINBITS bits:
  * site   = centroid of the hard cores the group's first-hop flops reach at minimal depth (in bus: forward, e.g.
             q_b001 gc_0 leaf -> r1c0 hcol cores), or, when no hard core is reached (q_b000: the scorer is a bus-to-bus
             stage L160m_i -> L14_o), the midpoint of the source bus face and this bus's face; the site is moved to the
             nearest free point (outside every hard-core box + halo) inside the outline;
  * row    = conn bus:<BUS>, launch/capture like the type's other rows of that bus with the scorer group named
             '<group>.d' (in) / '<group>.q' (out), from_um = the rows' face point, to_um = site, bits = group bits,
             regs_um = the bus depth (max regs of the bus rows, unchanged) on a Manhattan face->site path (HV or VH,
             whichever keeps every station out of hard-core boxes), every hop <= HOP.
The bus depth is unchanged (row regs == current max), so kit_istations' chain and all latency tables are unchanged.
usage: scorer_rows.py PLAN RTLDIR OUT_DELTA.json TYPE:BUS[:RTLTYPE] ...   (RTLTYPE: bound module to trace, default TYPE)
OUT_DELTA = {"types": {TYPE: {"internal_stations_add": [rows]}}, "report": [...]}; apply = append the rows."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import trace_readers as TR  # noqa: E402

HOP = 360.0
MINBITS = 16
TAG = "DIE-LAYOUT-HBM SCORER 11-11"


def group_of(sig):
    best = None
    for m in re.finditer(r"hb_idx_s_[A-Z]{2}_scorer(?:_ge_\d+_gc_\d+_leaf)?", sig):
        if best is None or len(m.group(0)) > len(best):
            best = m.group(0)
    return best


def boxes(t):
    return [(h["origin_um"][0] - h.get("halo_um", 0.0), h["origin_um"][1] - h.get("halo_um", 0.0),
             h["origin_um"][0] + h["outline_um"][0] + h.get("halo_um", 0.0),
             h["origin_um"][1] + h["outline_um"][1] + h.get("halo_um", 0.0)) for h in t["hard_cores"]]


def inside(p, bx):
    return any(a < p[0] < c and b < p[1] < d for a, b, c, d in bx)


def free_site(p, t, bx, step=4.32):
    W, H = t["outline_um"]
    if not inside(p, bx):
        return p
    best = None
    for r in range(1, 400):
        for dx, dy in ((r, 0), (-r, 0), (0, r), (0, -r)):
            q = (round(min(max(p[0] + dx * step, 1.0), W - 1.0), 3), round(min(max(p[1] + dy * step, 1.0), H - 1.0), 3))
            if not inside(q, bx):
                best = q
                break
        if best:
            return best
    raise SystemExit(f"no free site near {p}")


def face_point(t, bus):
    b = next(x for x in t["buses"] if x["name"] == bus)
    W, H = t["outline_um"]
    lo, hi = b.get("window_um") or b.get("offset_um")
    m = (lo + hi) / 2
    return {"W": (0.0, m), "E": (W, m), "S": (m, 0.0), "N": (m, H)}[b["face"]]


def chain(a, z, n, bx):
    """n stations on a Manhattan a->z path out of the boxes: HV / VH, each station slid along the path if needed"""
    best = None
    for mid in ((z[0], a[1]), (a[0], z[1])):
        path = [a, mid, z]
        L = sum(TR_dist(p, q) for p, q in zip(path, path[1:]))
        pts, ok = [], True
        for j in range(n):
            s0 = L * (j + 1) / (n + 1)
            hit = None
            for k in range(0, 200):
                for s in ((s0 + k * 2.16), (s0 - k * 2.16)):
                    if 0 < s < L:
                        q = at(path, s)
                        if not inside(q, bx):
                            hit = (s, q)
                            break
                if hit:
                    break
            if not hit:
                ok = False
                break
            pts.append(hit)
        if not ok:
            continue
        pts.sort()
        full = [a] + [q for _, q in pts] + [z]
        worst = max(TR_dist(p, q) for p, q in zip(full, full[1:]))
        cand = (worst, [list(q) for _, q in pts])
        if best is None or cand[0] < best[0]:
            best = cand
    return best


def TR_dist(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def at(path, s):
    for p, q in zip(path, path[1:]):
        d = TR_dist(p, q)
        if s <= d or q is path[-1]:
            f = s / d if d else 0.0
            return (round(p[0] + f * (q[0] - p[0]), 3), round(p[1] + f * (q[1] - p[1]), 3))
        s -= d
    return path[-1]


def bus_sources(txt, sigs, g):
    """input-bus stage signals reached backward from sigs (for a soft bus-to-bus scorer)"""
    hits = {}
    for s in sigs:
        seen, todo = {s}, [s]
        for _ in range(12):
            nxt = []
            for x in todo:
                for n in g.bwd.get(x, ()):
                    if isinstance(n, tuple):
                        continue
                    m = re.match(r"^(L\w+?_i)(?:_p\d+|_is\d+)?_q$", n)
                    if m:
                        hits[m.group(1)] = hits.get(m.group(1), 0) + 1
                    elif n not in seen:
                        seen.add(n)
                        nxt.append(n)
            todo = nxt
    return hits


def main(argv):
    plan, rtldir, outp = argv[:3]
    P = json.load(open(plan))
    T = P["partition_types"]
    delta, report = {}, []
    for spec in argv[3:]:
        tn, bus, *rt = spec.split(":")
        rtn = rt[0] if rt else tn
        t = T[tn]
        txt = open(f"{rtldir}/hbm_arch_{rtn}.sv").read()
        b = next(x for x in t["buses"] if x["name"] == bus)
        in_bus = b["dir"] == "in"
        res, hard = TR.trace(t, txt, bus, 14)
        rows = [r for r in t.get("internal_stations", []) if r.get("conn") == f"bus:{bus}"]
        n = max(len(r["regs_um"]) for r in rows)
        face = tuple(rows[0]["from_um"]) if str(rows[0].get("launch", "")).startswith("face bus") else tuple(rows[0]["to_um"])
        bx = boxes(t)
        groups = {}
        for o in res:
            gname = group_of(o["sig"])
            if not gname or not o["nbits"]:
                continue
            gr = groups.setdefault(gname, dict(bits=set(), pts=[], sigs=[], cores=set()))
            gr["cores"].update(o["cores"])
            for lo, hi in o["runs"]:
                gr["bits"].update(range(lo, hi + 1))
            gr["sigs"].append(o["sig"])
            if o["centroid"]:
                gr["pts"].append((o["nbits"], o["centroid"]))
        g = None
        for gname, gr in sorted(groups.items()):
            nb = len(gr["bits"])
            if nb < MINBITS:
                report.append(dict(type=tn, bus=bus, group=gname, bits=nb, skipped=f"< {MINBITS} bits"))
                continue
            if gr["pts"]:
                pieces = [h for h in t["hard_cores"]
                          if any(TR.norm(re.sub(r"__r[ab]$", "", h["inst"])) == TR.norm(c[2:]) for c in gr["cores"])]
                m = 2 * max(h.get("halo_um", 0.0) for h in pieces)
                x0 = min(h["origin_um"][0] for h in pieces) - m
                y0 = min(h["origin_um"][1] for h in pieces) - m
                x1 = max(h["origin_um"][0] + h["outline_um"][0] for h in pieces) + m
                y1 = max(h["origin_um"][1] + h["outline_um"][1] for h in pieces) + m
                c = (min(max(face[0], x0), x1), min(max(face[1], y0), y1))
                how = (f"face-nearest point of the box of the {len(gr['cores'])} reached hard cores "
                       f"[{x0:.1f},{y0:.1f},{x1:.1f},{y1:.1f}] (+2 halo)")
            else:
                g = g or TR.G(txt)
                src = bus_sources(txt, gr["sigs"], g)
                if not src:
                    raise SystemExit(f"{tn} {bus} {gname}: no hard core and no source bus reached")
                sb = max(src, key=lambda k: (next((x["width"] for x in t["buses"] if x["name"] == k), 0), src[k]))
                fp = face_point(t, sb)
                c = ((fp[0] + face[0]) / 2, (fp[1] + face[1]) / 2)
                how = f"midpoint of source bus {sb} face and {bus} face (no hard core reached)"
            site = free_site((round(c[0], 3), round(c[1], 3)), t, bx)
            ch = chain(face, site, n, bx)
            if ch is None or ch[0] > HOP:
                raise SystemExit(f"{tn} {bus} {gname}: no chain with hops <= {HOP} ({ch and ch[0]})")
            ref = rows[0]
            face_first = str(ref.get("launch", "")).startswith("face bus")
            row = dict(conn=f"bus:{bus}", from_um=list(face) if face_first else list(site),
                       to_um=list(site) if face_first else list(face),
                       regs_um=ch[1] if face_first else ch[1][::-1], bits=nb,
                       launch=f"face bus {bus}" if face_first else f"{gname}.q",
                       capture=(f"{gname}.d" if in_bus else f"{gname}.q") if face_first else f"face bus {bus}",
                       note=f"{TAG}: soft scorer group {gname} ({nb} b of {bus}, bound RTL trace); site = {how}; "
                            f"{n} station(s) = bus depth (unchanged), max hop {ch[0]:.0f} um; positions only")
            delta.setdefault(tn, dict(internal_stations_add=[]))["internal_stations_add"].append(row)
            report.append(dict(type=tn, bus=bus, group=gname, bits=nb, runs=TR.runs_of(gr["bits"])[:6], site=list(site),
                               centroid=[round(c[0], 2), round(c[1], 2)], how=how, depth=n, max_hop_um=round(ch[0], 1)))
            print(json.dumps(report[-1]))
    json.dump(dict(event=TAG, base_plan=plan, types=delta, report=report), open(outp, "w"), indent=1)


if __name__ == "__main__":
    main(sys.argv[1:])
