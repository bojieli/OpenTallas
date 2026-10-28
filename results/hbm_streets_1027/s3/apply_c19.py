"""HBM-STREETS-3 C19 plan event on C18 (one source for both forms; COORD 19:12 HBM-STREETS-2 rulings).
usage: apply_c19.py REPO C18DIR C19DIR '{"t07_dx": -25.92, "pgp_d": [0, 0]}'
(1) schema: drop non-schema hard_cores key lib_ff (C18 G0 349 schema errors).
(2) ruling 2: vms_glue re-outline 869.832x1334.88 -> VW x VH (<=800 wide, area kept +-5 %), centred in x, grown into the
    259-um S gap; new pins table (faces kept, proportional re-spread on the new face spans, pitch 0.048; N/S pins above the
    5.5/um pin6 cap spill to the low-density W face end next to them); clock tap to the new core centre.
(3) ruling 4: spb0 PHY NOT moved (io rect = allocated bump field, moving it changes the bump map) -> shift the SM t07 cores
    (q_sm2 u_sm_t07_s/_n; NW_sm2 R0 + NE_sm2 MY share the type) by t07_dx with their taps.
(4) pgp q1 (q_hub_ne u_pgp_Q__q1) shift pgp_d with its tap.
(5) station relax: every die-lane ft_slot station inside a hard core (local frame) moves to the nearest point outside every
    core (+ halo), keeping each hop <= 400 um Manhattan; failures are reported, never forced.
"""
import json, sys, shutil, hashlib, math, os
from pathlib import Path
REPO, SRC, OUT = map(Path, sys.argv[1:4]); OPT = json.loads(sys.argv[4]) if len(sys.argv) > 4 else {}
raw = json.load(open(SRC / "die_plan.json")); T = raw["partition_types"]
rep = dict(source=str(SRC / "die_plan.json"), source_sha=hashlib.sha256((SRC / "die_plan.json").read_bytes()).hexdigest()[:12], opt=OPT)
G = 4.32
def r4(v): return round(v, 4)
# (1)
n = 0
for t in T.values():
    for c in t.get("hard_cores") or []:
        if c.pop("lib_ff", None) is not None: n += 1
rep["lib_ff_dropped"] = n
OUT.mkdir(parents=True, exist_ok=True)
cores_out = OUT / "cores"
if cores_out.is_symlink() or cores_out.is_file(): cores_out.unlink()
if not cores_out.exists(): shutil.copytree(os.path.realpath(SRC / "cores"), cores_out)
# (1b) C18 SM partition shifts (NW/NE_sm0/2 +-17.28, NW_sm3 -69.12) overlap the spb partitions and break 23 port
# geometries (schema; masked in C18 by its lib_ff schema errors) -> optional revert to the C17g origins.
REV = {"NW_sm0": [-17.28, 0], "NW_sm2": [-17.28, 0], "NE_sm0": [17.28, 0], "NE_sm2": [17.28, 0], "NW_sm3": [69.12, 0]}
if OPT.get("revert_sm_shift"):
    for p in raw["partitions"]:
        if p["name"] in REV:
            p["origin_um"] = [r4(p["origin_um"][0] + REV[p["name"]][0]), r4(p["origin_um"][1] + REV[p["name"]][1])]
    rep["reverted_sm_shift"] = REV
# (2) vms_glue
VW, VH = OPT.get("vw", 777.6), OPT.get("vh", 1529.28)
OLD = "cores/hfd_hgi_vms_glue_nw_t__869.832x1334.88__canon.json"
NEW = f"cores/hfd_hgi_vms_glue_nw_t__{VW:g}x{VH:g}__c19.json"
pins = json.load(open(SRC / OLD)); W0, H0 = 869.832, 1334.88
CAP, END, PITCH, OFF = 5.5, 8.64, 0.048, 0.024
def face(p, W, H):
    x, y = p["x"], p["y"]; return min([(x, "W"), (W - x, "E"), (y, "S"), (H - y, "N")])[1]
by = {f: [] for f in "NSEW"}
for p in pins: by[face(p, W0, H0)].append(p)
spill = []
for f in "NS":
    cap = int(CAP * (VW - 2 * END))
    by[f].sort(key=lambda p: p["x"])
    while len(by[f]) > cap: spill.append((f, by[f].pop(0)))   # lowest x = next to the W face
def spread(lst, key, L, fixed):
    out = []; used = set()
    n = len(lst)
    lo, hi = END, L - END
    srt = sorted(lst, key=key)
    for i, p in enumerate(srt):
        v = lo + (hi - lo) * (i + 0.5) / n
        k = round((v - OFF) / PITCH)
        while k in used: k += 1
        used.add(k); q = dict(p); q[fixed[0]] = r4(OFF + k * PITCH); q[fixed[1]] = fixed[2]; out.append(q)
    return out
newp = []
INS = 0.019
newp += spread(by["S"], lambda p: p["x"], VW, ("x", "y", INS))
newp += spread(by["N"], lambda p: p["x"], VW, ("x", "y", r4(VH - INS)))
newp += spread(by["E"], lambda p: p["y"], VH, ("y", "x", r4(VW - INS)))
wl = [(p["y"] / H0, p) for p in by["W"]] + [(-1.0 + p["x"] / W0 * 1e-3, p) for f, p in spill if f == "S"] + [(2.0 + p["x"] / W0 * 1e-3, p) for f, p in spill if f == "N"]
wl.sort(key=lambda t: t[0])
wpins = [dict(p, layer="M4") for _, p in wl]
for i, p in enumerate(wpins): p["_k"] = i
newp += [{k: v for k, v in q.items() if k != "_k"} for q in spread(wpins, lambda p: p["_k"], VH, ("y", "x", INS))]
assert len(newp) == len(pins) and len({p["name"] for p in newp}) == len(pins)
(OUT / NEW).write_text(json.dumps(newp))
dens = {f: round(sum(1 for p in newp if face(p, VW, VH) == f) / ((VW if f in "NS" else VH) - 2 * END), 2) for f in "NSEW"}
rep["vms_glue"] = dict(outline=[VW, VH], area_ratio=round(VW * VH / (W0 * H0), 3), pins=len(newp), spilled_to_W=len(spill), density=dens, pins_file=NEW)
def tapmove(t, inst, dx, dy, newxy=None):
    k = 0
    for tp in (t.get("clock") or {}).get("taps") or []:
        if str(tp.get("name", "")).split(".")[0] == inst and tp.get("xy"):
            tp["xy"] = list(newxy) if newxy else [r4(tp["xy"][0] + dx), r4(tp["xy"][1] + dy)]; k += 1
    return k
moved = {}
for tn in ("q_hub_nw", "q_hub_ne"):
    for c in T[tn]["hard_cores"]:
        if c["module"] == "hfd_hgi_vms_glue_nw_t":
            x, y = c["origin_um"]; w, h = c["outline_um"]
            nx = r4(round((x + (w - VW) / 2) / G) * G); ny = r4(y + h - VH)
            c["origin_um"] = [nx, ny]; c["outline_um"] = [VW, VH]; c["pins_file"] = NEW
            c["note"] = c.get("note", "") + " | HBM-STREETS-3 C19: re-outlined <=800 um wide (COORD 19:12 ruling 2), new kit"
            k = tapmove(T[tn], c["inst"], 0, 0, newxy=[r4(nx + VW / 2), r4(ny + VH / 2)])
            moved[f"{tn}/{c['inst']}"] = dict(rect=[nx, ny, r4(nx + VW), r4(ny + VH)], taps=k)
rep["vms_moved"] = moved
# (3) SM t07
dx = OPT.get("t07_dx", 0.0)
rep["t07"] = {}
for c in T["q_sm2"]["hard_cores"]:
    if c["inst"] in ("u_sm_t07_s", "u_sm_t07_n") and dx:
        c["origin_um"] = [r4(c["origin_um"][0] + dx), c["origin_um"][1]]
        rep["t07"][c["inst"]] = dict(origin=c["origin_um"], taps=tapmove(T["q_sm2"], c["inst"], dx, 0))
# (4) pgp q1
d = OPT.get("pgp_d", [0, 0])
for c in T["q_hub_ne"]["hard_cores"]:
    if c["inst"] == "u_pgp_Q__q1" and any(d):
        c["origin_um"] = [r4(c["origin_um"][0] + d[0]), r4(c["origin_um"][1] + d[1])]
        rep["pgp_q1"] = dict(origin=c["origin_um"], taps=tapmove(T["q_hub_ne"], c["inst"], d[0], d[1]))
# (5) station relax, die frame: a die-lane ft_slot station inside ANY hard core of ANY partition (own type or a
# neighbour's) moves to the nearest point outside every core (halo) for EVERY instance of its type; hops <= 400 um.
HALO = OPT.get("halo", 4.32); MAXHOP = 400.0
parts = raw["partitions"]
def tf(p, x, y):
    W = T[p["type"]]["outline_um"][0]; ox, oy = p["origin_um"]
    o = p.get("orient", "R0")
    if o == "R0": return (ox + x, oy + y)
    if o == "MY": return (ox + W - x, oy + y)
    raise ValueError(o)
def itf(p, X, Y):
    W = T[p["type"]]["outline_um"][0]; ox, oy = p["origin_um"]
    return (X - ox, Y - oy) if p.get("orient", "R0") == "R0" else (ox + W - X, Y - oy)
DR = []
for p in parts:
    for c in T[p["type"]].get("hard_cores") or []:
        x0, y0 = tf(p, *c["origin_um"]); x1, y1 = tf(p, c["origin_um"][0] + c["outline_um"][0], c["origin_um"][1] + c["outline_um"][1])
        DR.append((min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1), p["name"] + "/" + c["inst"]))
def inside(q, m=0.0): return [r for r in DR if r[0] - m < q[0] < r[2] + m and r[1] - m < q[1] < r[3] + m]
inst_of = {}
for p in parts: inst_of.setdefault(p["type"], []).append(p)
# (5a) slots with no regs_um whose interpolated stations (check.lane_geometry) fall in a core: materialise regs_um
sys.path.insert(0, str(REPO / "tools/die_plan"))
import check as CK, schema as SC
Pl = SC.Plan(raw, OUT / "die_plan.json")
mat = []
for lid in Pl.lanes:
    for part, slot, a_, b_ in Pl.lane_crossings(lid):
        s_ = Pl.slot(part, slot) or {}
        if s_.get("regs_um"): continue
        pa, pb = Pl.port_point(a_), Pl.port_point(b_)
        seg = CK.zroute(pa, pb, Pl.die_face(part, s_.get("in_face", "W")), Pl.die_face(part, s_.get("out_face", "E")))
        L = CK.plen(seg); k = int(s_.get("stations", 1))
        st = [CK.point_at(seg, L * j / k) for j in range(k)]
        if any(inside(q) for q in st):
            p = next(p for p in parts if p["name"] == part)
            s_["regs_um"] = [[r4(v) for v in itf(p, *q)] for q in st]; mat.append(f"{part}/{slot} via {lid}")
rep["slots_materialised"] = mat
relaxed, failed = [], []
for tn, ps in inst_of.items():
    t = T[tn]; W, H = t["outline_um"]
    for s in t.get("ft_slots") or []:
        regs = s.get("regs_um") or []
        for i, loc in enumerate(regs):
            hits = [h for p in ps for h in inside(tf(p, *loc))]
            if not hits: continue
            p0 = next(p for p in ps if inside(tf(p, *loc)))
            r = inside(tf(p0, *loc))[0]; P0 = tf(p0, *loc)
            cands = [(r[0] - HALO, P0[1]), (r[2] + HALO, P0[1]), (P0[0], r[1] - HALO), (P0[0], r[3] + HALO)]
            cands += [(e, f) for e in (r[0] - HALO, r[2] + HALO) for f in (r[1] - HALO, r[3] + HALO)]
            best = None
            for Q in cands:
                q = itf(p0, *Q); q = (r4(q[0]), r4(q[1]))
                if not (0 <= q[0] <= W and 0 <= q[1] <= H): continue
                if any(inside(tf(p, *q), HALO * 0.5) for p in ps): continue
                nb = [regs[j] for j in (i - 1, i + 1) if 0 <= j < len(regs)]
                if any(abs(q[0] - b[0]) + abs(q[1] - b[1]) > MAXHOP for b in nb): continue
                dd = abs(q[0] - loc[0]) + abs(q[1] - loc[1])
                if best is None or dd < best[0]: best = (dd, q)
            if best:
                relaxed.append(dict(type=tn, slot=s["name"], i=i, core=r[4], frm=list(loc), to=list(best[1]), moved_um=round(best[0], 2))); regs[i] = list(best[1])
            else:
                failed.append(dict(type=tn, slot=s["name"], i=i, core=r[4], at=list(loc)))
rep["stations_relaxed"] = relaxed; rep["stations_failed"] = failed
raw["die"]["label"] = "C19 = C18 + HBM-STREETS-3 rulings event (vms_glue <=800 wide, SM t07 shift, pgp q1, station relax) | " + raw["die"].get("label", "")
(OUT / "die_plan.json").write_text(json.dumps(raw, indent=1))
for f in SRC.iterdir():
    if f.is_file() and not (OUT / f.name).exists() and f.suffix in (".json",) and f.name not in ("die_plan.json",):
        shutil.copy2(f, OUT / f.name)
(OUT / "c19_event_report.json").write_text(json.dumps(rep, indent=1))
print(json.dumps({k: (v if not isinstance(v, list) else len(v)) for k, v in rep.items()}, indent=0)[:1500])
