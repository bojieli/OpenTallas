"""KV-PLAN-DELTA-6 FT move (COORD 17:41 ruling: ~3,280 FT bits out of hub_Wi (ft5/ft6) and hgi_WN_7 v8 (ft4)).

Type-sharing rule: every ft slot of a shared type must be used on every instance (no idle stations = no tied ports),
so the hroot control buses move as a W/E mirror pair:
  L1449/L1450 (kvs_ctl.o_hroot_WN/WS)  hub_C -S-> pv_S_7 -W-> hgi_WS_7 -W-> hg_WS_7 -N-> hub_Wo(ft2/ft3, in S) -> hroot_W*
  L1447/L1448 (kvs_ctl.o_hroot_EN/ES)  hub_C -S-> pv_S_7 -E-> hgi_ES_7 -E-> hg_ES_7 -N-> hub_Eo(ft30/ft31, in S) -> hroot_E*
  hgi_v2 (WS_7 + ES_7) gets 2 slots used on both; kv3_hg_v3 splits: S instances (hg_WS_7, hg_ES_7) -> new type
  kv3_hg_v3s (= hg_v3 + 2 slots), N instances keep kv3_hg_v3 unchanged.  hub_Wi loses ft5/ft6, hub_Ei ft63/ft64.
  L663 (host.fdi 1044 b)  hub_Wi -E-> hub_C -N-> pv_N_7 -W(top)-> hgi_WN_7 ft4 (now local E->S corner at the die-top
  edge) -> hgi_WN_6 ft4 (unchanged).  All four touched types (hub_Wi, hub_C, pv_v12, hgi_v8) are unique.
Windows: <= 8 b/um (S.window_for per_um=8, track_max 0.6), core-free within 20 um of the face (face-register strip; M6/M7 over the M5-ceiling head cores) on both sides, no overlap
with existing pins (1.08-um gap); E windows = exact die mirror of the W windows (die is x-symmetric).
Stations: ceil(path / 380 um); siting = ft_corridor (reach 405, margin 1) with every existing FT flop blocked.
usage: d6_ft.py RUNTIME_ROOT IN.json OUT.json LEDGER.json"""
import copy, json, math, sys
from pathlib import Path
import numpy as np

R = Path(sys.argv[1]); inp, outp, ledp = sys.argv[2:5]
sys.path.insert(0, str(R / "tools/die_plan")); sys.path.insert(0, str(R))
import schema as S, ft_corridor as F

raw = json.load(open(inp)); P = S.Plan(raw, Path(inp))
DIE_W = P.W
CX2 = float(DIE_W)
PER_UM, GAP, CLEAR = 8.0, 1.08, 20.0   # 20 um: face-register strip; head cores are M5-ceiling, M6/M7 run over them (12.7 roads)
LED = dict(windows=[], slots=[], lanes={}, types={})
ports = {p["id"]: p for p in raw["ports"]}
parts = {p["name"]: p for p in raw["partitions"]}
T = raw["partition_types"]


def shared(a, b):
    """(die face of a toward b, axis lo, axis hi, face line coordinate)"""
    ax0, ay0, ax1, ay1 = P.rect(a); bx0, by0, bx1, by1 = P.rect(b)
    if abs(ax1 - bx0) < 1e-3: return "E", max(ay0, by0), min(ay1, by1), ax1
    if abs(ax0 - bx1) < 1e-3: return "W", max(ay0, by0), min(ay1, by1), ax0
    if abs(ay1 - by0) < 1e-3: return "N", max(ax0, bx0), min(ax1, bx1), ay1
    if abs(ay0 - by1) < 1e-3: return "S", max(ax0, bx0), min(ax1, bx1), ay0
    raise ValueError(f"{a} {b} not abutting")


def occupied(a, b, skip=()):
    iv = []
    for pid, pr in P.ports.items():
        if pid in skip: continue
        if {pr["src"]["part"], pr["dst"]["part"]} == {a, b}:
            cs = [c for _, _, c in P.port_pins(pid)]
            iv.append((min(cs) - GAP, max(cs) + GAP))
    return iv


def die_boxes(part):
    out = []
    for bx in S.placed_macro_boxes(P.ptype(part)).values():
        p1 = P.to_die(part, (bx[0], bx[1])); p2 = P.to_die(part, (bx[2], bx[3]))
        out.append((min(p1[0], p2[0]), min(p1[1], p2[1]), max(p1[0], p2[0]), max(p1[1], p2[1])))
    return out


def core_hit(face, line, lo, hi, parts_):
    for part in parts_:
        for x0, y0, x1, y1 in die_boxes(part):
            if face in "EW":
                if x1 > line - CLEAR and x0 < line + CLEAR and y0 < hi and y1 > lo: return True
            else:
                if y1 > line - CLEAR and y0 < line + CLEAR and x0 < hi and x1 > lo: return True
    return False


def layers_for(face):
    return ["M4", "M6"] if face in "EW" else ["M5", "M7"]


def find_window(a, b, width, pref, taken, skip=()):
    face, lo, hi, line = shared(a, b)
    lays = layers_for(face)
    L = S.window_for(0.0, width + 1, lays, per_um=PER_UM, track_max=0.6)
    occ = occupied(a, b, skip) + taken
    best = None
    s = lo + 4.32
    while s + L <= hi - 4.32:
        w0, w1 = s, s + L
        if not any(o0 < w1 + GAP and o1 > w0 - GAP for o0, o1 in occ) and not core_hit(face, line, w0, w1, (a, b)):
            d = abs((w0 + w1) / 2 - pref)
            if best is None or d < best[0]: best = (d, round(w0, 4), round(w1, 4))
        s += 2.16
    if best is None: raise ValueError(f"no window {a}->{b} {width} b")
    return face, [best[1], best[2]], lays


def mirror_win(w):
    return [round(CX2 - w[1], 4), round(CX2 - w[0], 4)]


def next_slot(tn, used):
    names = {s["name"] for s in T[tn].get("ft_slots", [])} | used
    k = 0
    while f"ft{k}" in names: k += 1
    used.add(f"ft{k}"); return f"ft{k}"


# --- 1. split kv3_hg_v3 -> kv3_hg_v3s for the S instances
T["kv3_hg_v3s"] = copy.deepcopy(T["kv3_hg_v3"])
T["kv3_hg_v3s"]["module"] = T["kv3_hg_v3"]["module"].replace("kv3_hg_v3", "kv3_hg_v3s")
T["kv3_hg_v3s"]["note"] = T["kv3_hg_v3"].get("note", "") + " | KV-PLAN-DELTA-6: S-row variant (hg_WS_7, hg_ES_7) + 2 hroot ctl ft slots"
for n in ("hg_WS_7", "hg_ES_7"): parts[n]["type"] = "kv3_hg_v3s"
for k in [k for k, v in raw["census"][0].items() if False]: pass
P = S.Plan(raw, Path(inp))

# --- 2. remove the old hub crossings
def drop_slot(tn, name):
    T[tn]["ft_slots"] = [s for s in T[tn]["ft_slots"] if s["name"] != name]
for tn, nm in (("kv3_hub_Wi", "ft5"), ("kv3_hub_Wi", "ft6"), ("kv3_hub_Ei", "ft63"), ("kv3_hub_Ei", "ft64")):
    drop_slot(tn, nm)

# --- 3. route W lanes, mirror to E
# chain W: (src part, dst part) per new port; slot faces in die frame
W_CHAIN = ["hub_C", "pv_S_7", "hgi_WS_7", "hg_WS_7", "hub_Wo"]
E_CHAIN = ["hub_C", "pv_S_7", "hgi_ES_7", "hg_ES_7", "hub_Eo"]
top_s = P.rect("pv_S_7")[3]
PREF = {("hub_C", "pv_S_7"): P.rect("hub_C")[0] + 160, ("pv_S_7", "hgi_WS_7"): top_s - 160,
        ("hgi_WS_7", "hg_WS_7"): top_s - 160, ("hg_WS_7", "hub_Wo"): P.rect("hg_WS_7")[2] - 160}
pairs = {"L1449": ("L1447", "ft2", "ft30"), "L1450": ("L1448", "ft3", "ft31")}
taken = {}
used = {tn: set() for tn in T}
newports = {}
slotname = {}
for lw, (le, wo_slot, eo_slot) in pairs.items():
    width = ports[lw + "_0"]["width"]
    wp, ep = [], []
    for i, (a, b) in enumerate(zip(W_CHAIN, W_CHAIN[1:])):
        tk = taken.setdefault((a, b), [])
        face, win, lays = find_window(a, b, width, PREF[(a, b)], tk, skip=(lw + "_0", lw + "_1", le + "_0", le + "_1"))
        tk.append((win[0] - GAP, win[1] + GAP))
        ea, eb = E_CHAIN[i], E_CHAIN[i + 1]
        eface = {"E": "W", "W": "E"}.get(face, face)
        ewin = mirror_win(win) if face in "NS" else list(win)
        # also reserve the mirrored window on the E pair
        taken.setdefault((ea, eb), []).append((ewin[0] - GAP, ewin[1] + GAP))
        if a == "hub_C":
            ws, es = dict(part="hub_C", bus=f"o_kvs_ctl_o_hroot_{lw == 'L1449' and 'WN' or 'WS'}"), \
                     dict(part="hub_C", bus=f"o_kvs_ctl_o_hroot_{lw == 'L1449' and 'EN' or 'ES'}")
        else:
            ws, es = dict(part=a, bus=slotname[(lw, a)] + "_o"), dict(part=ea, bus=slotname[(le, ea)] + "_o")
        if b in ("hub_Wo",):
            wd, ed = dict(part="hub_Wo", bus=wo_slot + "_i"), dict(part="hub_Eo", bus=eo_slot + "_i")
        else:
            tnw = P.parts[b]["type"]
            if b == "pv_S_7":
                nw, ne = next_slot(tnw, used[tnw]), next_slot(tnw, used[tnw])
            else:   # shared type (hgi_v2 / hg_v3s): one slot used by the W and the E instance
                nw = ne = next_slot(tnw, used[tnw])
            slotname[(lw, b)] = nw; slotname[(le, eb)] = ne
            wd, ed = dict(part=b, bus=nw + "_i"), dict(part=eb, bus=ne + "_i")
        wp.append(dict(id=f"{lw}_d6_{i}", src=ws, dst=wd, width=width, kind="data", face=face, layers=lays,
                       window_um=win, order="lsb_low"))
        ep.append(dict(id=f"{le}_d6_{i}", src=es, dst=ed, width=width, kind="data", face=eface, layers=lays,
                       window_um=ewin, order="lsb_high" if face in "NS" else "lsb_low"))
        LED["windows"].append(dict(lane=lw, a=a, b=b, face=face, window_um=win, b_per_um=round((width + 1) / (win[1] - win[0]), 3),
                                   mirror=dict(lane=le, a=ea, b=eb, face=eface, window_um=ewin)))
    newports[lw] = wp; newports[le] = ep

# slot records (die faces -> type faces)
def add_slot(part, name, fin_die, fout_die, width, length):
    tn = P.parts[part]["type"]
    if any(s["name"] == name for s in T[tn]["ft_slots"]): return
    T[tn]["ft_slots"].append(dict(name=name, in_face=P.type_face(part, fin_die), out_face=P.type_face(part, fout_die),
                                  width=width, stations=max(1, math.ceil(length / 380.0))))
    LED["slots"].append(dict(type=tn, slot=name, part=part, in_die=fin_die, out_die=fout_die, width=width,
                             path_est_um=round(length, 1)))


def wcen(pr):
    return (pr["window_um"][0] + pr["window_um"][1]) / 2


def face_pt(part, face, c):
    x0, y0, x1, y1 = P.rect(part)
    return {"E": (x1, c), "W": (x0, c), "N": (c, y1), "S": (c, y0)}[face]


for lid, plist in newports.items():
    for pin, pout in zip(plist, plist[1:]):
        part = pin["dst"]["part"]
        if part in ("hub_Wo", "hub_Eo"): continue
        fin = S.OPP[pin["face"]]; fout = pout["face"]
        a = face_pt(part, fin, wcen(pin)); b = face_pt(part, fout, wcen(pout))
        add_slot(part, pin["dst"]["bus"][:-2], fin, fout, pin["width"], abs(a[0] - b[0]) + abs(a[1] - b[1]))

# hub_Wo / hub_Eo: existing slots now enter from the S face
for part, lid, nm in (("hub_Wo", "L1449", "ft2"), ("hub_Wo", "L1450", "ft3"), ("hub_Eo", "L1447", "ft30"), ("hub_Eo", "L1448", "ft31")):
    s = P.slot(part, nm); pin = newports[lid][-1]; pout = ports[[q for q in P.lanes[lid]["ports"]][-1]]
    s["in_face"] = P.type_face(part, "S")
    a = face_pt(part, "S", wcen(pin)); b = face_pt(part, pout["face"], wcen(pout))
    s["stations"] = max(1, math.ceil((abs(a[0] - b[0]) + abs(a[1] - b[1])) / 380.0))
    for k in ("regs_um", "bit_sites_um"): s.pop(k, None)
    LED["slots"].append(dict(type=P.parts[part]["type"], slot=nm, part=part, in_die="S", out_die="W" if part == "hub_Wo" else "E",
                             width=s["width"], path_est_um=round(abs(a[0] - b[0]) + abs(a[1] - b[1]), 1), kind="re-faced"))

# --- 4. L663 host.fdi out of v8
w663 = ports["L663_0"]["width"]
c663 = []
f, win, lays = find_window("hub_Wi", "hub_C", w663, P.rect("hub_Wi")[3] - 120, taken.setdefault(("hub_Wi", "hub_C"), []), skip=("L663_0",))
taken[("hub_Wi", "hub_C")].append((win[0] - GAP, win[1] + GAP))
nC = next_slot("kv3_hub_C", used["kv3_hub_C"]); nN = next_slot("kv3_pv_v12", used["kv3_pv_v12"])
c663.append(dict(id="L663_d6_0", src=dict(part="hub_Wi", bus="o_host_fdi"), dst=dict(part="hub_C", bus=nC + "_i"), width=w663,
                 kind="data", face=f, layers=lays, window_um=win, order="lsb_low"))
f, win, lays = find_window("hub_C", "pv_N_7", w663, P.rect("hub_C")[0] + 120, taken.setdefault(("hub_C", "pv_N_7"), []))
c663.append(dict(id="L663_d6_1", src=dict(part="hub_C", bus=nC + "_o"), dst=dict(part="pv_N_7", bus=nN + "_i"), width=w663,
                 kind="data", face=f, layers=lays, window_um=win, order="lsb_low"))
f, win, lays = find_window("pv_N_7", "hgi_WN_7", w663, P.rect("pv_N_7")[3] - 120, taken.setdefault(("pv_N_7", "hgi_WN_7"), []))
c663.append(dict(id="L663_d6_2", src=dict(part="pv_N_7", bus=nN + "_o"), dst=dict(part="hgi_WN_7", bus="ft4_i"), width=w663,
                 kind="data", face=f, layers=lays, window_um=win, order="lsb_low"))
for c in c663:
    LED["windows"].append(dict(lane="L663", a=c["src"]["part"], b=c["dst"]["part"], face=c["face"], window_um=c["window_um"],
                               b_per_um=round((w663 + 1) / (c["window_um"][1] - c["window_um"][0]), 3)))
nxt = ports["L663_1"]
for part, pin, pout in (("hub_C", c663[0], c663[1]), ("pv_N_7", c663[1], c663[2])):
    fin = S.OPP[pin["face"]]; a = face_pt(part, fin, wcen(pin)); b = face_pt(part, pout["face"], wcen(pout))
    add_slot(part, pin["dst"]["bus"][:-2], fin, pout["face"], w663, abs(a[0] - b[0]) + abs(a[1] - b[1]))
s4 = P.slot("hgi_WN_7", "ft4"); fin = S.OPP[c663[2]["face"]]
a = face_pt("hgi_WN_7", fin, wcen(c663[2])); b = P.port_point("L663_1")
s4["in_face"] = P.type_face("hgi_WN_7", fin)
s4["stations"] = max(1, math.ceil((abs(a[0] - b[0]) + abs(a[1] - b[1])) / 380.0))
for k in ("regs_um", "bit_sites_um"): s4.pop(k, None)
LED["slots"].append(dict(type="kv3_hgi_v8", slot="ft4", part="hgi_WN_7", in_die=fin, out_die=nxt["face"], width=w663,
                         path_est_um=round(abs(a[0] - b[0]) + abs(a[1] - b[1]), 1), kind="re-faced (was full-height S->N)"))
newports["L663"] = c663

# --- 5. rewrite lanes / ports
lanes = {l["id"]: l for l in raw["lanes"]}
drop = set()
for lid, plist in newports.items():
    old = lanes[lid]["ports"]
    if lid == "L663":
        keep = old[1:]; drop |= {old[0]}
    else:
        keep = [old[-1]]; drop |= set(old[:-1])
    lanes[lid]["ports"] = [p["id"] for p in plist] + keep
    lanes[lid]["note"] = lanes[lid].get("note", "") + " | KV-PLAN-DELTA-6 FT move (hub_Wi/v8 capacity)"
raw["ports"] = [p for p in raw["ports"] if p["id"] not in drop] + [p for pl in newports.values() for p in pl]
# hub_Wo/hub_Eo last-hop ports keep src bus ft2/ft3/ft30/ft31 _o (unchanged)
P = S.Plan(raw, Path(inp))

# --- 6. site the new / re-faced slots, every existing flop blocked
touched = {}
for s in LED["slots"]: touched.setdefault(s["type"], set()).add(s["slot"])
for tn, names in touched.items():
    ty = P.types[tn]
    allslots = ty["ft_slots"]
    fixed = []
    for s in allslots:
        if s["name"] in names: continue
        w, h = s["bit_site_cell_um"]
        for st in s.get("bit_sites_um", []):
            for x, y in st: fixed.append((x, y, x + w, y + h))
    alloc = F.RowAllocator
    F.RowAllocator = lambda *a, _al=alloc, **kw: _al(*a, **dict(kw, blocked=list(kw.get("blocked", [])) + fixed))
    ty["ft_slots"] = [s for s in allslots if s["name"] in names]
    try:
        led = F._place_type(P, tn, 405., 1., {}, {})
    finally:
        F.RowAllocator = alloc
        placed = {s["name"]: s for s in ty["ft_slots"]}
        ty["ft_slots"] = [placed.get(s["name"], s) for s in allslots]
    LED["types"][tn] = led

# --- 7. latency of the moved lanes
for lid in newports:
    old = raw["latency"]["lanes"][lid]
    nat = P.lane_natural(lid)
    new = dict(old, cycles=nat["cycles"] + old.get("pad", 0), stations=nat["stations"], boundary=nat["boundary"],
               faces=nat["faces"], fixed=nat["fixed"], natural=nat["cycles"])
    LED["lanes"][lid] = dict(old=old, new=new)
    raw["latency"]["lanes"][lid] = new

Path(outp).write_text(json.dumps(raw, indent=1) + "\n")
Path(ledp).write_text(json.dumps(LED, indent=1, default=float) + "\n")
for w in LED["windows"]: print("WIN", w["lane"], w["a"], "->", w["b"], w["face"], w["window_um"], w["b_per_um"], "b/um")
for lid, v in LED["lanes"].items(): print("LAT", lid, v["old"]["cycles"], "->", v["new"]["cycles"])
print("D6_FT_DONE")
