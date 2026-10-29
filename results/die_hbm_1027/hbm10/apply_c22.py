"""DIE-HBM-10 C22 = C21 + the two C21-caused G0C error groups fixed structurally (COORD 09:30 C21 collect).
usage: apply_c22.py C21_DIR OUT_DIR
C21 G0C = 80 ERRORs against 16 on the C20j baseline (same tools). All 64 new ones are C21's own:
 (a) 41 street_die_leg + 19 geometry: the 66 idx 2nd-quarter pieces (u_hb_idx__s_Q2_*) were homed in q_b010/q_b001 free
     space that ignored the ft lane stations (bit sites + station regs).  Fix: re-home every piece on a CORRIDOR-FREE
     slot (blocked = other hard cores/contents + every actual ft bit cell + every station reg point, 8.64-um halo to cores),
     filling outward from the hub W face for locality: q_b000 -> q_b010 -> q_b001 -> q_b011 -> q_b002.  Same canon views,
     same inst names, 0 new types (NW/NE share the types via MY).  Stations, windows, pins, outlines: unchanged.
 (b) 4 complete/internal_station: the planned VM crossing link u_vmb_Q1 <-> u_vmb_Q5 (3.98 mm) had 3 registers, so its
     hops exceed reach 405 um.  Fix: registers by a greedy walk along the link, each at the farthest point <= 400 um on that is
     not inside a hub hard core (hop re-checked <= 405).  Lx = N + 1 cycles.
Nothing else changes (PHY_N split NOT applied: the HBM PHY is one hard macro with one clock pin, see README (2))."""
import json, sys, shutil, os, hashlib, copy, math
from pathlib import Path
import numpy as np
SRC, OUT = map(Path, sys.argv[1:3])
P = json.load(open(SRC / "die_plan.json")); T = P["partition_types"]
SIDE = json.load(open(SRC / "c21_side.json"))
rep = dict(event="C22 (DIE-HBM-10)", source=str(SRC / "die_plan.json"),
           source_sha=hashlib.sha256((SRC / "die_plan.json").read_bytes()).hexdigest()[:12])
OUT.mkdir(parents=True, exist_ok=True)
if not (OUT / "cores").exists(): shutil.copytree(os.path.realpath(SRC / "cores"), OUT / "cores")
G, HALO, R = 8.64, 8.64, 2.16
def r4(v): return round(v, 4)
def snapg(v, g=2.16): return r4(round(v / g) * g)

# ---------------- (a) corridor-free idx 2nd-quarter homes
ORDER = ["q_b000", "q_b010", "q_b001", "q_b011", "q_b002"]
pieces = []
for tn in ("q_b010", "q_b001"):
    keep = []
    for h in T[tn]["hard_cores"]:
        (pieces if h["inst"].startswith("u_hb_idx__s_Q2_") else keep).append(h)
    T[tn]["hard_cores"] = keep
assert len(pieces) == 66, len(pieces)
def blocked(t):
    Wt, Ht = t["outline_um"]
    occ = [(h["origin_um"][0], h["origin_um"][1], h["origin_um"][0] + h["outline_um"][0], h["origin_um"][1] + h["outline_um"][1])
           for h in t.get("hard_cores", [])]
    occ += [(c["origin_um"][0], c["origin_um"][1], c["origin_um"][0] + c["outline_um"][0], c["origin_um"][1] + c["outline_um"][1])
            for c in t.get("contents", []) if c.get("origin_um") and c.get("outline_um") and not c["inst"].startswith("u_hb_idx__s_Q2")]
    M = np.zeros((int(Wt / R) + 3, int(Ht / R) + 3), bool)
    for s in t.get("ft_slots", []):
        cw, ch = s.get("bit_site_cell_um", (1.404, .27))
        for sites in s.get("bit_sites_um") or []:
            for x, y in sites: M[int(x / R):int((x + cw) / R) + 2, int(y / R):int((y + ch) / R) + 2] = True
        for r in s.get("regs_um") or []:
            M[max(0, int((r[0] - 4) / R)):int((r[0] + 4) / R) + 2, max(0, int((r[1] - 4) / R)):int((r[1] + 4) / R) + 2] = True
    C = np.zeros((M.shape[0] + 1, M.shape[1] + 1), int); C[1:, 1:] = M.cumsum(0).cumsum(1)
    return occ, C
def mhit(C, r):
    a, b, c, d = int(r[0] / R), int(r[1] / R), int(r[2] / R) + 2, int(r[3] / R) + 2
    return (C[c, d] - C[a, d] - C[c, b] + C[a, b]) > 0
def ohit(occ, r, hl): return any(r[0] < o[2] + hl and o[0] < r[2] + hl and r[1] < o[3] + hl and o[1] < r[3] + hl for o in occ)
k = 0; rep["idx_homes"] = {}
for tn in ORDER:
    if k == len(pieces): break
    t = T[tn]; Wt, Ht = t["outline_um"]; occ, C = blocked(t); added = []
    y = 17.28
    while y + 187.488 <= Ht - 17.28 and k < len(pieces):
        x = 17.28
        while x + 218.592 <= Wt - 17.28 and k < len(pieces):
            h = pieces[k]; W, H = h["outline_um"]
            r = (x, y, x + W, y + H)
            if not ohit(occ, r, HALO) and not mhit(C, r):
                h = copy.deepcopy(h); h["origin_um"] = [r4(x), r4(y)]
                h["note"] = h.get("note", "").split(" | C22")[0] + f" | C22 (a): corridor-free home in {tn} (C21 site hit ft lane stations)"
                t["hard_cores"].append(h); occ.append(r); added.append(h["inst"]); k += 1
                x = math.ceil((x + W + HALO) / G - 1e-9) * G; continue   # stay on the 8.64-um origin lattice
            x += G
        y += G
    if added:
        ha = sum(h["outline_um"][0] * h["outline_um"][1] for h in t["hard_cores"])
        rep["idx_homes"][tn] = dict(pieces=len(added), hard_fill=round(ha / (Wt * Ht), 3))
assert k == 66, k
# glue entry: keep in q_b010, move to a corridor-free spot clear of the pieces
t = T["q_b010"]; occ, C = blocked(t)
g = next(c for c in t["contents"] if c["inst"] == "u_hb_idx__s_Q2"); gw, gh = g["outline_um"]; done = False
for y in np.arange(17.28, t["outline_um"][1] - gh - 17.28, G):
    for x in np.arange(17.28, t["outline_um"][0] - gw - 17.28, G):
        r = (x, y, x + gw, y + gh)
        if not ohit(occ, r, HALO) and not mhit(C, r):
            g["origin_um"] = [r4(x), r4(y)]; done = True; break  # x, y from 17.28 + k*8.64: on lattice
    if done: break
assert done
rep["idx_homes"]["glue_origin_um"] = g["origin_um"]
rep["idx_homes"]["note"] = ("fill outward from the hub W face (locality); lanes L6q2/L7q2/L91q2/L137q2 still owed as die ports "
                            "(C21 lanes_owed), now with via b000..b002")

# ---------------- (b) VM crossing link registers within reach
rep["vm_link"] = {}
for tn in ("q_hub_nw", "q_hub_ne"):
    t = T[tn]; cores = [(h["origin_um"][0], h["origin_um"][1], h["origin_um"][0] + h["outline_um"][0], h["origin_um"][1] + h["outline_um"][1])
                        for h in t["hard_cores"]]
    inside = lambda p: any(c[0] < p[0] < c[2] and c[1] < p[1] < c[3] for c in cores)
    for st in t["internal_stations"]:
        if not st.get("note", "").startswith("C21 (b) PLANNED VM crossing link"): continue
        (x0, y0), (x1, y1) = st["from_um"], st["to_um"]
        # The straight row line crosses hub hard cores (u_hb_vms_Q__q0 is 778 um wide > reach), so the link takes the
        # nearest free channel row y*: launch face -> vertical to y* -> horizontal -> vertical to the capture face.
        # Registers by a greedy walk along that path, each at the farthest point <= 400 um on that is not inside a core.
        assert y0 == y1
        Ht = t["outline_um"][1]
        def walk(path):
            seg = list(zip(path, path[1:])); Ls = [abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in seg]; tot = sum(Ls)
            def at(s_):
                for (p, q), l in zip(seg, Ls):
                    if s_ <= l + 1e-9:
                        f = s_ / l if l else 0.0; return (p[0] + (q[0] - p[0]) * f, p[1] + (q[1] - p[1]) * f)
                    s_ -= l
                return path[-1]
            regs, cur = [], 0.0
            while tot - cur > 400.0:
                for d in np.arange(400.0, 20.0, -2.16):
                    q = at(cur + d); qs = (snapg(q[0]), snapg(q[1]))
                    if not inside(q) and not inside(qs): break
                else: return None, tot
                regs.append([qs[0], qs[1]]); cur += d
            return regs, tot
        best = None
        for dy in sorted(np.arange(-1500.0, 1500.1, 8.64), key=abs):
            ys = y0 + dy
            if not (20 < ys < Ht - 20): continue
            path = [(x0, y0), (x0 + 1e-6 * (x1 - x0), ys), (x1 - 1e-6 * (x1 - x0), ys), (x1, y1)] if dy else [(x0, y0), (x1, y1)]
            regs, tot = walk(path)
            if regs is not None: best = (dy, regs, tot); break
        if best is None: raise SystemExit(f"{tn}: no channel row for the VM link")
        dy, regs, span = best; n = len(regs)
        pts = [st["from_um"]] + regs + [st["to_um"]]
        hops = [abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(pts, pts[1:])]
        assert max(hops) <= 405.0, (tn, max(hops))
        st["regs_um"] = regs
        st["note"] = st["note"].replace("Lx 4 cycles", f"Lx {n + 1} cycles") + f" | C22 (b): {n} regs, max hop {max(hops):.1f} um (reach 405)"
        rep["vm_link"].setdefault(tn, []).append(dict(conn=st["conn"], path_um=r4(span), channel_dy_um=r4(dy), regs=n, lx_cycles=n + 1,
                                                      max_hop_um=round(max(hops), 1), regs_in_core=sum(inside(p) for p in regs)))
    for l in SIDE.get("planned_links", {}).get(tn, []):
        l["latency_cycles"] = rep["vm_link"][tn][0]["lx_cycles"]
        l["regs_um"] = next(s["regs_um"] for s in t["internal_stations"] if s.get("conn") == l["launch"] + "|" + l["capture"])
P["note"] = (P.get("note") or "") + " | C22 (DIE-HBM-10 10-28): corridor-free idx Q2 homes, VM link regs within reach"
txt = json.dumps(P, indent=1); (OUT / "die_plan.json").write_text(txt)
(OUT / "die_plan.sha256").write_text(hashlib.sha256(txt.encode()).hexdigest() + "  die_plan.json\n")
for f in os.listdir(SRC):
    if f.endswith(".json") and not (OUT / f).exists() and f not in ("die_plan.json", "c21_side.json"):
        shutil.copy(SRC / f, OUT / f)
json.dump(SIDE, open(OUT / "c22_side.json", "w"), indent=1); json.dump(rep, open(OUT / "c22_event_report.json", "w"), indent=1)
print(json.dumps(rep, indent=1)[:3000])
