#!/usr/bin/env python3
"""DIE-HBM-38 plan events on d35b (q_b010 + q_b010__physical_v1, identical edits; NE_b010 MY / NW_b010 R0 share the
type-local geometry).
  r : RE-STATION of the 4 over-reach slot classes found by the G2 actual-station check (COORD 12:4x priority):
      L28x2  4 -> 5 stations (E->N worst bit 1678 um Manhattan cannot close in 4 hops of 405 um; station0 sits beside
             its input pin) -> lane L28/L28m 28 -> 29 cycles; packed bit-site clusters re-solved (min max hop).
      L36x2  stage-1/2 clusters re-solved (same 3 stations).
      L168mx1 station0 cloud moved toward the input window; L204mx1 station3 cloud re-balanced.
  a : r + one intra-strip core move u_hb_idx__s_Q2_r0c2_k0h1 (587.52 -> 483.84, same y) opening the core-free N-S
      channel x 702.43-829.44 (y 2903 -> N face) for L28x2; L28x2 clusters solved inside the channel region; L36x2
      (its stage-1 cluster sat where the moved core lands) 3 -> 4 stations (lane L36/L36m 14 -> 15 cycles).
usage: mk_d38.py MODE SRC_PLAN_DIR DST_PLAN_DIR PROBE_IO_TCL"""
import json, sys, os, shutil, hashlib, re
import numpy as np
mode, src, dst, iotcl = sys.argv[1:5]
P = json.load(open(src + "/die_plan.json"))
TYPES = ["q_b010", "q_b010__physical_v1"]
t0 = P["partition_types"]["q_b010"]
W, H = t0["outline_um"]
CELL = (1.08, 0.27)
pins = {m[1]: (float(m[2]), float(m[3])) for m in re.finditer(
    r"place_pin -pin_name \{(\S+)\} -layer \S+ -location \{([\d.]+) ([\d.]+)\}", open(iotcl).read())}
rep = {"event": "d38" + mode, "base": src, "slots": {}, "cores": []}
if mode == "a":
    for tn in TYPES:
        h = next(h for h in P["partition_types"][tn]["hard_cores"] if h["inst"] == "u_hb_idx__s_Q2_r0c2_k0h1")
        assert h["origin_um"] == [587.52, 3291.84]
        h["origin_um"] = [483.84, 3291.84]
    rep["cores"].append({"inst": "u_hb_idx__s_Q2_r0c2_k0h1", "from": [587.52, 3291.84], "to": [483.84, 3291.84]})
cores = [(c["origin_um"][0], c["origin_um"][1], c["origin_um"][0] + c["outline_um"][0], c["origin_um"][1] + c["outline_um"][1])
         for c in t0["hard_cores"]]
# placement blockages of content leaves with outlines that are not split into cores (as g2.probe_blockages)
for c in t0["contents"]:
    if "origin_um" in c and "outline_um" in c and not any(h["inst"] == c["inst"] or h["inst"].startswith((c["inst"] + "_", c["inst"] + ".")) for h in t0["hard_cores"]):
        cores.append((c["origin_um"][0], c["origin_um"][1], c["origin_um"][0] + c["outline_um"][0], c["origin_um"][1] + c["outline_um"][1]))
slots = {s["name"]: s for s in t0["ft_slots"]}
SOLVE = ["L28x2", "L36x2"]
def firm_boxes(skip):
    out = []
    for s in t0["ft_slots"]:
        if s["name"] in skip: continue
        for st in s.get("bit_sites_um", []):
            a = np.array(st); out.append((a[:, 0].min(), a[:, 1].min(), a[:, 0].max() + CELL[0], a[:, 1].max() + CELL[1]))
    return out
OBS = cores + firm_boxes(SOLVE)
def free(box, m=1.0):
    x0, y0, x1, y1 = box
    if x0 < 4.32 + m or y0 < 4.32 + m or x1 > W - 4.32 - m or y1 > H - 4.32 - m: return False
    return not any(x0 < b[2] + m and b[0] - m < x1 and y0 < b[3] + m and b[1] - m < y1 for b in OBS)
def bitpins(name, n):
    pi = np.array([pins[f"{name}_i[{b}]"] for b in range(n)]); po = np.array([pins[f"{name}_o[{b}]"] for b in range(n)])
    return pi, po
def inset(p, f):
    d = {"E": (-1, 0), "W": (1, 0), "N": (0, -1), "S": (0, 1)}[f]; return p + np.array(d, float)
def solve(name, k, init, region=None, iters=60):
    """k stations (station0 beside the in pin + k-1 packed clusters).  Cluster shape = slot's existing stage-1
    sites (relative offsets kept, bit order kept).  Minimise the max per-bit Manhattan hop."""
    s = slots[name]; n = s["width"] + 1
    shape = np.array(s["bit_sites_um"][0]); shape = shape - shape.mean(0)
    cc = shape + np.array([CELL[0] / 2, CELL[1] / 2])        # cell centres relative to cluster centre
    lo, hi = shape.min(0), shape.max(0) + np.array(CELL)
    pi, po = bitpins(name, n)
    s0 = inset(pi, s["in_face"]) + np.array([CELL[0] / 2, CELL[1] / 2]) * 0
    def cost(C):
        pts = [pi, s0] + [c + cc for c in C] + [po]
        v = max(np.abs(a - b).sum(1).max() for a, b in zip(pts, pts[1:]))
        # G0C reach rule (reach.py): station-centre hops <= 0.9 x 405 = 364.5 um -> keep <= 360 (scaled into the same objective)
        cen = [np.array(s["regs_um"][0], float)] + list(C)
        vc = max(np.abs(a - b).sum() for a, b in zip(cen, cen[1:]))
        return max(v, vc * 405.0 / 360.0)
    def ok(c):
        if region and not (region[0] <= c[0] + lo[0] and c[0] + hi[0] <= region[2] and region[1] <= c[1] + lo[1] and c[1] + hi[1] <= region[3]):
            return False
        return free((c[0] + lo[0], c[1] + lo[1], c[0] + hi[0], c[1] + hi[1]))
    C = [np.array(c, float) for c in init]
    assert all(ok(c) for c in C), [(c, ok(c)) for c in C]
    best = cost(C)
    for step in (40, 20, 10, 5, 2.16, 1.08, 0.54, 0.27):
        for _ in range(iters):
            imp = False
            for j in range(len(C)):
                for d in ((step, 0), (-step, 0), (0, step), (0, -step), (step, step), (-step, -step), (step, -step), (-step, step)):
                    c2 = C[j] + d
                    if not ok(c2): continue
                    C2 = C[:j] + [c2] + C[j + 1:]
                    v = cost(C2)
                    if v < best - 1e-6: C, best, imp = C2, v, True
            if not imp: break
    return C, best, cc, shape
def apply(name, k, C, shape):
    for tn in TYPES:
        s = next(x for x in P["partition_types"][tn]["ft_slots"] if x["name"] == name)
        st0 = s["regs_um"][0]
        s["stations"] = k
        s["regs_um"] = [st0] + [[round(float(c[0]), 3), round(float(c[1]), 3)] for c in C]
        # translate the slot's legal stage-1 packing by a site/row-grid multiple (0.054 x 0.27 um)
        a0 = np.array(slots[name]["bit_sites_um"][0]); m0 = a0.mean(0)
        sites = []
        for c in C:
            dx = round((c[0] - m0[0]) / 0.054) * 0.054; dy = round((c[1] - m0[1]) / 0.27) * 0.27
            sites.append([[round(float(x + dx), 3), round(float(y + dy), 3)] for x, y in a0])
        s["bit_sites_um"] = sites
        s["regs_um"] = [st0] + [[round(float(np.array(q)[:, 0].mean() + CELL[0] / 2), 3), round(float(np.array(q)[:, 1].mean() + CELL[1] / 2), 3)] for q in sites]
def lane_cycles(lane, d):
    L = P["latency"]["lanes"]
    for nm in (lane, lane + "m"):
        e = L[nm]; e["cycles"] += d; e["stations"] += d; e["natural"] += d
    rep.setdefault("lane_cycles", {})[lane] = {nm: L[nm]["cycles"] for nm in (lane, lane + "m")}
# --- L28x2
if mode == "r":
    init = [(790, 3200), (735, 3558), (700, 3908), (640, 4248)]; region = None
else:
    init = [(780, 3200), (766, 3500), (766, 3800), (766, 4100)]; region = (702.432, 2903.0, 829.44, H)
C, best, cc, shape = solve("L28x2", 5, init, region)
apply("L28x2", 5, C, shape); lane_cycles("L28", +1)
rep["slots"]["L28x2"] = {"stations": 5, "centres": [list(map(float, c)) for c in C], "max_hop_um": round(best, 3)}
OBS += firm_boxes(set(SOLVE) - {"L28x2"}) and []
s = slots["L28x2"]   # updated sites of L28x2 now obstruct L36x2
for st in next(x for x in P["partition_types"]["q_b010"]["ft_slots"] if x["name"] == "L28x2")["bit_sites_um"]:
    a = np.array(st); OBS.append((a[:, 0].min(), a[:, 1].min(), a[:, 0].max() + CELL[0], a[:, 1].max() + CELL[1]))
# --- L36x2
if mode == "r":
    C, best, cc, shape = solve("L36x2", 3, [np.array(st).mean(0) for st in slots["L36x2"]["bit_sites_um"]])
    apply("L36x2", 3, C, shape)
    rep["slots"]["L36x2"] = {"stations": 3, "centres": [list(map(float, c)) for c in C], "max_hop_um": round(best, 3)}
else:
    C, best, cc, shape = solve("L36x2", 4, [(760, 3330), (440, 3316), (261.4, 3327.7)])
    apply("L36x2", 4, C, shape); lane_cycles("L36", +1)
    rep["slots"]["L36x2"] = {"stations": 4, "centres": [list(map(float, c)) for c in C], "max_hop_um": round(best, 3)}
# --- regs-only clouds (movable; aim <= 380 um planned to leave DPL displacement margin)
for tn in TYPES:
    for x in P["partition_types"][tn]["ft_slots"]:
        if x["name"] == "L168mx1":
            assert x["regs_um"][0] == [712.8, 1982.88]; x["regs_um"][0] = [740.16, 1952.64]
        if x["name"] == "L204mx1":
            assert x["regs_um"][3] == [17.28, 1520.64]; x["regs_um"][3] = [17.28, 1485.0]
rep["slots"]["L168mx1"] = {"station0": [[712.8, 1982.88], [740.16, 1952.64]]}
rep["slots"]["L204mx1"] = {"station3": [[17.28, 1520.64], [17.28, 1485.0]]}
for tn in TYPES:
    P["partition_types"][tn]["note"] += f" | DIE-HBM-38 d38{mode}: re-station L28x2(5)/L36x2/L168mx1/L204mx1 to the 405-um reach" + (" + core r0c2_k0h1 -> x 483.84 (N-S channel x 702.4-829.4)" if mode == "a" else "")
os.makedirs(dst, exist_ok=True)
for f in os.listdir(src):
    if f == "die_plan.json": continue
    s_, d_ = os.path.join(src, f), os.path.join(dst, f)
    if os.path.exists(d_): continue
    if os.path.isdir(s_): shutil.copytree(s_, d_, copy_function=os.link)
    else: os.link(s_, d_)
open(dst + "/die_plan.json", "w").write(json.dumps(P, indent=1) + "\n")
rep["die_plan_sha256"] = hashlib.sha256(open(dst + "/die_plan.json", "rb").read()).hexdigest()
json.dump(rep, open(dst + f"/d38{mode}_event_report.json", "w"), indent=1)
print(json.dumps(rep, indent=1))
