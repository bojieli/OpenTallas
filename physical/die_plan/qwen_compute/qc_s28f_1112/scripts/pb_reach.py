#!/usr/bin/env python3
"""QC-S28-F: per-bit TRUE reach of every per_bit internal-station chain, mirroring the kit TCL (kit_istations is_bits +
is_knee_site: chain bbox over the chain's starts, one shared integer split, stage k on bit b's own L), PLUS the
unregistered lane leg leaf_um <-> lane pin.  In buses: exact lane pin of each bit from the bound RTL
(.c_i({<bus>_q[b], ...}) concatenation, MSB first).  Out buses: the lane c_o pin envelope on the leaf side (nearest /
farthest c_o pin of that core), reported as a range.  Read-only.
usage (cwd SRC): pb_reach.py SRC PLAN BIND_RTL_DIR OUT_TSV TYPE [TYPE...]"""
import json
import re
import sys
from pathlib import Path

SRC, PLAN, RTL, OUT = sys.argv[1:5]
TYPES = sys.argv[5:]
sys.path.insert(0, SRC + "/tools/die_plan")
import schema  # noqa: E402
import gen_phys  # noqa: E402

raw = json.load(open(PLAN))
P = schema.Plan(raw, path=PLAN)
L1 = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])  # noqa: E731


def knee_sites(px, py, lx, ly, face, edges, d_in, geom, along):
    xmin, ymin, xmax, ymax = geom
    if face in "EW":
        normal = max(abs(xmin - lx), abs(xmax - lx)); alng = max(abs(ymin - ly), abs(ymax - ly)); cx, cy = lx, py
    else:
        normal = max(abs(ymin - ly), abs(ymax - ly)); alng = max(abs(xmin - lx), abs(xmax - lx)); cx, cy = px, ly
    n1, a1 = normal, alng
    if along:
        cx, cy = (px, ly) if face in "EW" else (lx, py)
        n1, a1 = alng, normal
    if d_in:
        first, second, ax, ay, bx, by = n1, a1, px, py, lx, ly
    else:
        first, second, ax, ay, bx, by = a1, n1, lx, ly, px, py
    if first < 1e-8:
        split, worst = 0, second / edges
    elif second < 1e-8:
        split, worst = edges, first / edges
    else:
        worst, split = min((max(first / j, second / (edges - j)), j) for j in range(1, edges))
    pts = []
    for e in range(1, edges):
        if e <= split:
            f = e / split
            pts.append((ax + f * (cx - ax), ay + f * (cy - ay)))
        else:
            f = (e - split) / (edges - split)
            pts.append((cx + f * (bx - cx), cy + f * (by - cy)))
    return worst, split, pts, (ax, ay), (bx, by)


def lane_map(tn):
    """{(inst, bus, bit): lane pin name} for in buses from the bound RTL"""
    f = Path(RTL) / f"{tn}.sv"
    out = {}
    if not f.exists():
        return out
    s = f.read_text()
    for m in re.finditer(r"\n\s*(\w+) (u_\w+) \((.*?)\);\n", s, re.S):
        inst = m.group(2)
        for pm in re.finditer(r"\.(\w+)\((\{.*?\}|[^()]*)\)", m.group(3)):
            els = [e.strip() for e in pm.group(2).strip("{}").split(",")]
            N = len(els)
            for i, e in enumerate(els):
                mm = re.fullmatch(r"(\w+)_q\[(\d+)\]", e)
                if mm:
                    out[(inst, mm.group(1), int(mm.group(2)))] = f"{pm.group(1)}[{N - 1 - i}]"
    return out


rows = []
for tn in TYPES:
    t = raw["partition_types"][tn]
    buses = {b["name"]: b for b in t["buses"]}
    hc = {h["inst"]: h for h in t.get("hard_cores", [])}
    cpins = {}
    for inst, h in hc.items():
        pf = Path(SRC) / "physical/die_plan/qwen_compute/plan_of_record" / h["pins_file"] if h.get("pins_file") else None
        if pf and pf.exists():
            ox, oy = h["origin_um"]
            cpins[inst] = {p["name"]: (ox + float(p["x"]), oy + float(p["y"])) for p in json.loads(pf.read_text())["pins"]}
    pins = {}
    for name, bit, _ln, x, y, face in gen_phys.type_pins(P, tn):
        pins.setdefault(name, {})[bit] = (x, y, face)
    lm = lane_map(tn)
    for idx, e in enumerate(t.get("internal_stations", [])):
        if e.get("bit_route") != "per_bit" or not e.get("conn", "").startswith("bus:"):
            continue
        bus = e["conn"][4:]
        b = buses[bus]
        d_in = b["dir"] == "in"
        face = b["face"]
        bat = pins.get(bus, {})
        W = max(bat) if bat else int(b["width"]) - 1
        if e.get("start_core"):
            starts = {bit: (float(p[0]), float(p[1])) for bit, p in enumerate(e["start_um"])}
        else:
            keep = sorted({int(x) for x in e.get("core_bits", bat)} | {W})
            starts = {x: bat[x][:2] for x in keep if x in bat}
        keep = {int(x) for x in e.get("core_bits", list(starts))}
        xs = [p[0] for p in starts.values()]; ys = [p[1] for p in starts.values()]
        geom = (min(xs), min(ys), max(xs), max(ys))
        lx, ly = e["leaf_um"]
        n = len(e["regs_um"])
        along = e.get("leg_order") == "along_first"
        if e.get("leg_order") == "channel":
            rows.append(dict(type=tn, idx=idx, bus=bus, core=e.get("core"), n=n, note="channel chain (not mirrored)"))
            continue
        cores = e["core"] if isinstance(e.get("core"), list) else [e.get("core") or str(b.get("leaf", "")).split(".")[0]]
        kw, tw, lane_lo, lane_hi = 0.0, 0.0, 1e9, 0.0
        for bit, (px, py) in starts.items():
            if bit not in keep:
                continue
            worst, split, st, A, B = knee_sites(px, py, lx, ly, face, n + 1, d_in, geom, along)
            kw = max(kw, worst)
            chain = [A] + st + [B]
            hops = [L1(a, c) for a, c in zip(chain, chain[1:])]
            # lane leg
            lp = None
            for c in cores:
                pn = lm.get((c, bus, bit))
                if pn and c in cpins and pn in cpins[c]:
                    lp = cpins[c][pn]
            if d_in and lp is not None:
                leg = L1((lx, ly), lp)
                lane_lo, lane_hi = min(lane_lo, leg), max(lane_hi, leg)
                hops[-1] += leg
            elif not d_in:
                c = cores[0]
                cand = [v for k, v in cpins.get(c, {}).items() if k.startswith("c_o[")]
                if cand:
                    ds = sorted(L1((lx, ly), v) for v in cand)
                    lane_lo, lane_hi = min(lane_lo, ds[0]), max(lane_hi, ds[0])
                    hops[0] += ds[0]
            tw = max(tw, max(hops))
        hc0 = hc.get(cores[0])
        rows.append(dict(type=tn, idx=idx, bus=bus, dir=b["dir"], core="+".join(cores), bits=e.get("bits"), n=n,
                         order=e.get("leg_order", "normal"), start=e.get("start_core", "-"),
                         kit_knee=round(kw, 1), true_hop=round(tw, 1),
                         lane_leg=f"{lane_lo:.1f}-{lane_hi:.1f}" if lane_hi else "-",
                         leaf=e["leaf_um"]))
cols = ["type", "idx", "bus", "dir", "core", "bits", "n", "order", "start", "kit_knee", "true_hop", "lane_leg", "leaf", "note"]
with open(OUT, "w") as f:
    f.write("\t".join(cols) + "\n")
    for r in rows:
        f.write("\t".join(str(r.get(c, "")) for c in cols) + "\n")
bad = [r for r in rows if (r.get("true_hop") or 0) > 405 or (r.get("kit_knee") or 0) > 403]
print(f"chains {len(rows)} kit_knee>403 {sum(1 for r in rows if (r.get('kit_knee') or 0) > 403)} "
      f"true_hop>405 {sum(1 for r in rows if (r.get('true_hop') or 0) > 405)} "
      f"max kit {max((r.get('kit_knee') or 0) for r in rows):.1f} max true {max((r.get('true_hop') or 0) for r in rows):.1f}")
for r in bad:
    print("  BAD", r)
