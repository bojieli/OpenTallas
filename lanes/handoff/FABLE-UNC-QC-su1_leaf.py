#!/usr/bin/env python3
"""FABLE-UNC-QC SU1-LEAF-1 (rc104; closes the gap of VISQC-SU-1): slw_su_l1 x_su_c_i chain u_lane4+u_lane5.
The kit sites a per_bit core chain on each bit's own L route start_um -> leaf_um (kit_istations is_knee_site), n = len(regs_um)
stations, every hop L_b / (n + 1).  With leaf (497.8, 328.16) the route is 87-162 um for 6 stations: 696 x 6 flops in a 30 x 132 um
box beside the landing macro, on top of the 6-deep landing pad and the in-boundary bank = the GRT cluster (475-525, 200-300).
Row: leaf_um / to_um -> LEAF (the E-face strip between the lane4 and lane5 c_i pin groups), regs_um re-spaced on the L; same 6
stations, 0 cycles.  usage: su1_leaf.py PLAN_IN PLAN_OUT ROW.json EDITS.json"""
import sys, json, hashlib
pin, pout, prow, pedit = sys.argv[1:5]
LEAF = [450.0, 403.2]
TYPES = ["slw_su_l1__cla2a78701", "slw_su_l1__clcc9d0155"]
def knee(first, second, edges):
    if first < 1e-8: return second / edges, 0
    if second < 1e-8: return first / edges, edges
    return min((max(first / j, second / (edges - j)), j) for j in range(1, edges))
raw = json.load(open(pin)); base = hashlib.sha256(open(pin, "rb").read()).hexdigest()[:12]
edits = []; rep = {}
for tn in TYPES:
    ty = raw["partition_types"][tn]
    rows = [s for s in ty["internal_stations"] if s["conn"] == "bus:x_su_c_i" and s.get("core") == ["u_lane4", "u_lane5"]]
    assert len(rows) == 1, (tn, len(rows))
    s = rows[0]; n = len(s["regs_um"]); st = s["start_um"]; bits = sorted(set(s["core_bits"]) | {len(st) - 1})
    def geom(leaf):
        xs = [st[b][0] for b in bits]; ys = [st[b][1] for b in bits]
        normal = max(abs(min(xs) - leaf[0]), abs(max(xs) - leaf[0])); along = max(abs(min(ys) - leaf[1]), abs(max(ys) - leaf[1]))
        Ls = [abs(st[b][0] - leaf[0]) + abs(st[b][1] - leaf[1]) for b in bits]
        w, j = knee(normal, along, n + 1)
        box = (abs(max(xs) - leaf[0])) * (max(max(ys), leaf[1]) - min(min(ys), leaf[1]))
        return dict(leaf=leaf, normal=round(normal, 1), along=round(along, 1), L_min=round(min(Ls), 1), L_max=round(max(Ls), 1), kit_knee_hop=round(w, 1), split=j,
                    hop_min=round(min(Ls) / (n + 1), 1), hop_max=round(max(Ls) / (n + 1), 1), route_box_um2=round(box), chain_flops=len(bits) * n)
    old = dict(leaf_um=list(s["leaf_um"]), to_um=list(s["to_um"]), regs_um=[list(p) for p in s["regs_um"]])
    before = geom(s["leaf_um"]); after = geom(LEAF)
    fx, fy = s["from_um"]; L = abs(fx - LEAF[0]) + abs(LEAF[1] - fy); regs = []
    for k in range(1, n + 1):
        t = L * k / (n + 1)
        regs.append([round(fx - t, 3), round(fy, 3)] if t <= abs(fx - LEAF[0]) else [LEAF[0], round(fy + (t - abs(fx - LEAF[0])), 3)])
    s["leaf_um"] = list(LEAF); s["to_um"] = list(LEAF); s["regs_um"] = regs
    s["note"] = (s.get("note", "") + " | " if s.get("note") else "") + ("SU1-LEAF-1 11-23 (FABLE-UNC-QC rc104): leaf (497.8,328.16) -> (450.0,403.2), the strip between the lane4 and lane5 "
                 "c_i pin groups; per-bit route %s-%s um -> %s-%s um for the same %d stations, 0 cycles" % (before["L_min"], before["L_max"], after["L_min"], after["L_max"], n))
    # hard cores the per-bit L routes could enter (corner = (leaf x, pin y) for an E-face in bus, normal first)
    hits = []
    for h in ty["hard_cores"]:
        x0, y0 = h["origin_um"]; x1, y1 = x0 + h["outline_um"][0], y0 + h["outline_um"][1]
        for b in bits:
            px, py = st[b]
            for (ax, ay), (bx, by) in (((px, py), (LEAF[0], py)), ((LEAF[0], py), tuple(LEAF))):
                if min(ax, bx) < x1 - 0.5 and max(ax, bx) > x0 + 0.5 and min(ay, by) < y1 - 0.5 and max(ay, by) > y0 + 0.5: hits.append((h["inst"], b)); break
    pins_dist = {}
    rep[tn] = dict(before=before, after=after, macro_hits=len(hits), hit_cores=sorted({h for h, _ in hits}))
    edits.append(dict(type=tn, select=dict(conn="bus:x_su_c_i", core=["u_lane4", "u_lane5"]), set=dict(leaf_um=s["leaf_um"], to_um=s["to_um"], regs_um=regs), old=old))
out = json.dumps(raw, separators=(",", ":")) + "\n"; open(pout, "w").write(out)
sha = hashlib.sha256(out.encode()).hexdigest()[:12]
json.dump(dict(row="SU1-LEAF-1", lane="FABLE-UNC-QC", item="rc104", base_sha=base, out_sha=sha, includes="VISQC-SU-1 (base plan = VIS-QC su1_plan.json)",
               partition_types={tn: raw["partition_types"][tn] for tn in TYPES}), open(prow, "w"), separators=(",", ":"))
json.dump(dict(row="SU1-LEAF-1", lane="FABLE-UNC-QC", item="rc104", apply_after="VISQC-SU-1", edits=edits, report=rep), open(pedit, "w"), indent=1)
print("SU1-LEAF-1 base", base, "->", sha); print(json.dumps(rep, indent=1))
