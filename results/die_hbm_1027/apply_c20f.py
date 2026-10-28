"""DIE-HBM-3 C20f = C20e (ef1edb01445c) + COORD 22:18 rulings (b) L12 split and (c) vms_glue height growth.
usage: apply_c20f.py REPO C20E_DIR VMSGROW_DIR C20F_DIR

(c) vms_glue (hfd_hgi_vms_glue_nw_t, 4 instances q_hub_nw/ne u_hb_vms_Q__q0/q1) 777.6x1529.28 -> 777.6x1635.552
    (+106.272 um, the REPACK grow-alt; E face 8897 pins -> 5.498/um <= 5.5, no ring-bus split).  Delta from
    vms_grow.py (repack.py restricted to the vms table, pins in centre form): grown cores + 34 neighbour moves of
    108 um, taps follow (REPACK rule).  Core-frame islands unchanged (all inside the taller outline).
(b) L12 split (DIE-HBM-2 ASK (b) default, COORD ACCEPTED): one as-built bus split over two lanes of equal latency.
    L12 / L12m keep bits [1979:0] (1980 b) on root W/E -> b101 E-in N-out -> hub S, b101 slot L12x1 4 -> 5 stations
    (the C20a hop 390 > 364 is cut) and the NW/NE_b101 cut 2996/3303 = 0.91 -> 1980/3303 = 0.599 <= 0.6.
    New lanes L12s / L12ms carry bits [2995:1980] (1016 b) direct root W face -> NW_hub E face (L12s) and root E
    face -> NE_hub W face (L12ms), like L74.  latency_groups kind "bus" {L12, L12s}, {L12m, L12ms}; LAT 13 kept
    (fixed_cycles), no RTL cycle change.  The W shared face (root/NW_hub) has no free 182-um stretch near the source
    (free: 60 um at 6275, 65 um at 7918, 800 um above 9585): L12s goes right after L74_0 and every W-face window above
    it moves up (order kept, 0.48-um gaps) into the free top stretch; their face endpoints in root ft slots and
    root/hub internal stations follow.  E face (root/NE_hub): free 6250-6824, no ripple.
    core_conns: root tx -> {L12, L12s}, tx_v / ctl.cq / ctl.vm_rq / argmax.cq -> L12s only (bit map
    root_ep_report: all at bits >= 2180); hub: every port that lists L12_i also lists L12s_i (port-level superset).
    Internal stations: root L12s_o/L12ms_o and hub L12s_i twins routed with hub_repack.route_station (hops <= 360,
    registers off cores); per consumer the twin register count is padded to its L12 path count + one common excess,
    and the excess comes off the L12s lane fixed_cycles so every bit of the word lands in the same cycle.
"""
import json, sys, shutil, hashlib, os, copy
from pathlib import Path
REPO, SRC, VG, OUT = map(Path, sys.argv[1:5])
sys.path.insert(0, str(REPO / "tools/die_plan"))
import hub_repack as HR
OUT.mkdir(parents=True, exist_ok=True)
for f in SRC.iterdir():
    if f.is_file() and f.suffix in (".json", ".sha256"):
        shutil.copy2(f, OUT / f.name)
if (OUT / "cores").exists(): shutil.rmtree(OUT / "cores")
shutil.copytree(os.path.realpath(SRC / "cores"), OUT / "cores")
raw = json.load(open(SRC / "die_plan.json")); T = raw["partition_types"]
cc = json.load(open(SRC / "core_conns.json"))
rep = dict(source=str(SRC), source_sha=hashlib.sha256((SRC / "die_plan.json").read_bytes()).hexdigest()[:12])
def r4(v): return round(v, 4)
def g48(v): return r4(round(v / 0.048) * 0.048)
parts = {p["name"]: p for p in raw["partitions"]}
P_ = {p["id"]: p for p in raw["ports"]}
REACH = 360.0

# ------------------------------------------------------------------ (c) vms_glue growth
dl = json.load(open(VG / "c20_repack_delta.json"))
vdone = []
for e in dl["entries"]:
    t = T[e["type"]]; c = next(c for c in t["hard_cores"] if c["inst"] == e["inst"])
    assert c["origin_um"] == e["old_origin"] or abs(c["origin_um"][0] - e["old_origin"][0]) + abs(c["origin_um"][1] - e["old_origin"][1]) < 1e-3, e["inst"]
    c["origin_um"] = [r4(v) for v in e["new_origin"]]
    if e["grown"]:
        c["outline_um"] = list(e["new_outline"])
        shutil.copy2(VG / e["new_pins_file"], OUT / e["new_pins_file"]); c["pins_file"] = e["new_pins_file"]
        c["note"] = c.get("note", "") + " | DIE-HBM-3 C20f: +106.272 um height (COORD 22:18 (c), E face 5.498/um)"
    for tm in e["taps_moved"]:
        tp = next(tp for tp in t["clock"]["taps"] if tp["name"] == tm["name"]); tp["xy"] = list(tm["new_xy"])
    vdone.append((e["type"], e["inst"], e["grown"], e["move_um"]))
rep["vms_glue"] = dict(entries=len(vdone), grown=[v for v in vdone if v[2]], moved=len([v for v in vdone if not v[2]]),
                       max_move=max(v[3] for v in vdone))

# ------------------------------------------------------------------ (b) L12 split
NB = 1980; NS = 2996 - NB
def shrink(w, frac):
    c = (w[0] + w[1]) / 2; ww = g48((w[1] - w[0]) * frac); lo = g48(c - ww / 2); return [lo, r4(lo + ww)]
for pid in ("L12_0", "L12_1", "L12m_0", "L12m_1"):
    P_[pid]["width"] = NB; P_[pid]["window_um"] = shrink(P_[pid]["window_um"], NB / 2996)
for tn, bn in (("root", "L12_o"), ("root", "L12m_o"), ("q_hub_nw", "L12_i"), ("q_hub_ne", "L12_i")):
    next(b for b in T[tn]["buses"] if b["name"] == bn)["width"] = NB
# b101 slot: width + 5 stations on a legal route (E in -> N out)
b101 = {}
for bpart, btype, lid in (("NW_b101", "q_b101_nw", "L12"), ("NE_b101", "q_b101", "L12m")):
    bt = T[btype]; W, H = bt["outline_um"]; pb = parts[bpart]
    s = next(s for s in bt["ft_slots"] if s["name"] == "L12x1"); s["width"] = NB
    wi = P_[lid + "_0"]["window_um"]; wo = P_[lid + "_1"]["window_um"]
    yi = (wi[0] + wi[1]) / 2 - pb["origin_um"][1]
    xo = (wo[0] + wo[1]) / 2 - pb["origin_um"][0]
    if pb.get("orient", "R0") == "MY": xo = W - xo
    xin = W if s["in_face"] == "E" else 0.0
    R = HR.Raster(W, H, [HR._core_rect(h) for h in bt.get("hard_cores", [])])
    res = HR.route_station(R, (xin, yi), (xo, H), 5, REACH)
    old = s["regs_um"]
    if res and len(res["regs"]) == 5:
        # keep registers one lattice step inside the outline (the slot convention: E strip x = W - 4.32, N row y = H - 4.32)
        s["regs_um"] = [[r4(min(max(x, 4.32), W - 4.32)), r4(min(max(y, 4.32), H - 4.32))] for x, y in res["regs"]]; s["stations"] = 5
    s["note"] = (f"DIE-HBM-3 C20f: L12 split (COORD 22:18 (b)) bits [1979:0] only, {s['stations']} stations "
                 f"(route {res and res['kind']}, {res and res['length_um']} um) | " + s.get("note", ""))
    for k in ("bit_sites_um", "bit_site_cell_um"): s.pop(k, None)
    b101[btype] = dict(old=old, new=s["regs_um"], route=res and {k: v for k, v in res.items() if k != "regs"})
rep["b101"] = b101

# new lanes / ports / buses
W_HUB = T["q_hub_nw"]["outline_um"][0]
ROOT = parts["root"]; RX0, RY0 = ROOT["origin_um"]; RW = T["root"]["outline_um"][0]
HUBY0 = parts["NW_hub"]["origin_um"][1]
def win_w(bits): return g48(bits * 0.178813)      # the shared-face M6/M4 density of L4/L13 (5.59 pins/um)
WS = win_w(NS)
l74 = P_["L74_0"]["window_um"]
lo_w = r4(l74[1] + 0.48); win_W = [lo_w, r4(lo_w + WS)]
lo_e = r4(P_["L89m_0"]["window_um"][1] + 0.48); win_E = [lo_e, r4(lo_e + WS)]
assert win_E[1] < P_["L4m_0"]["window_um"][0] - 0.48
newports = [dict(id="L12s_0", src={"part": "root", "bus": "L12s_o"}, dst={"part": "NW_hub", "bus": "L12s_i"}, width=NS,
                 kind="data", face="W", layers=["M6", "M4"], window_um=win_W,
                 note="DIE-HBM-3 C20f L12 split: bits [2995:1980] of the as-built L12 word, direct root W -> NW_hub E (like L74)"),
            dict(id="L12ms_0", src={"part": "root", "bus": "L12ms_o"}, dst={"part": "NE_hub", "bus": "L12s_i"}, width=NS,
                 kind="data", face="E", layers=["M6", "M4"], window_um=win_E,
                 note="DIE-HBM-3 C20f L12m split: bits [2995:1980] of the as-built L12m word (204 used, 812 open), direct root E -> NE_hub W")]
# W-face ripple: every root-W/NW_hub-E window at or above L12s moves up (order kept, gap 0.48)
face_ports = sorted([p for p in raw["ports"] if p.get("window_um") and {p["src"]["part"], p["dst"]["part"]} == {"root", "NW_hub"}],
                    key=lambda p: p["window_um"][0])
shift = {}
hi = win_W[1]
for p in face_ports:
    w = p["window_um"]
    if w[1] <= win_W[0] + 1e-6: continue
    lo = max(w[0], r4(hi + 0.48)); d = r4(lo - w[0])
    if d > 0:
        shift[p["id"]] = dict(old=list(w), d=d); p["window_um"] = [r4(w[0] + d), r4(w[1] + d)]
    hi = p["window_um"][1]
TOP = HUBY0 + T["q_hub_nw"]["outline_um"][1]
assert hi <= TOP - 0.48, (hi, TOP)
rep["w_face_ripple"] = dict(l12s_window=win_W, moved={k: v["d"] for k, v in shift.items()}, top_after=hi, face_top=TOP)
raw["ports"].extend(newports)
raw["lanes"].append(dict(id="L12s", ports=["L12s_0"], fixed_cycles=0,
                         note="DIE-HBM-3 C20f: L12 split bits [2995:1980], root W -> NW_hub E direct; latency group L12_word"))
raw["lanes"].append(dict(id="L12ms", ports=["L12ms_0"], fixed_cycles=0,
                         note="DIE-HBM-3 C20f: L12m split bits [2995:1980], root E -> NE_hub W direct; latency group L12m_word"))
raw.setdefault("latency_groups", []).extend([
    dict(name="L12_word", kind="bus", lanes=["L12", "L12s"], source="root.L12_o",
         note="DIE-HBM-3 C20f: one as-built bus (2996 b) over two lanes, same cycle"),
    dict(name="L12m_word", kind="bus", lanes=["L12m", "L12ms"], source="root.L12m_o",
         note="DIE-HBM-3 C20f: one as-built bus (2996 b) over two lanes, same cycle")])
T["root"]["buses"] += [dict(name="L12s_o", dir="out", width=NS, kind="data"), dict(name="L12ms_o", dir="out", width=NS, kind="data")]
for tn in ("q_hub_nw", "q_hub_ne"):
    T[tn]["buses"].append(dict(name="L12s_i", dir="in", width=NS, kind="data"))

# face endpoints that follow the ripple (root W face x=0, NW hub E face x=W_HUB)
def wshift(ylocal_die):
    for k, v in shift.items():
        if v["old"][0] - 1.0 <= ylocal_die <= v["old"][1] + 1.0: return v["d"]
    return 0.0
moved_pts = []
for s in T["root"].get("ft_slots", []):
    for r in s.get("regs_um") or []:
        if abs(r[0]) < 1e-6:
            d = wshift(r[1] + RY0)
            if d: moved_pts.append(("root.slot", s["name"], r[1], d)); r[1] = r4(r[1] + d)

# ------------------------------------------------------------------ core_conns
def addbus(lst, new, drop=None):
    out = [x for x in lst if x != drop] if drop else list(lst)
    if new not in out: out.append(new)
    return out
CCN = {}
r = cc["root"]
for inst, pt, mode, lid in (("u_hb_idx__link", "tx", "both", ""), ("u_hb_idx__link", "tx_v", "move", ""),
                            ("u_hb_idx__ctl", "cq", "move", ""), ("u_hb_idx__ctl", "vm_rq", "move", ""),
                            ("u_hb_argmax", "cq", "move", "")):
    for ob, nb in (("bus:L12_o", "bus:L12s_o"), ("bus:L12m_o", "bus:L12ms_o")):
        if ob in r[inst][pt]:
            r[inst][pt] = addbus(r[inst][pt], nb, drop=ob if mode == "move" else None)
            CCN.setdefault("root", []).append(f"{inst}.{pt}: {ob} -> {'+' if mode == 'both' else ''}{nb}")
for tn in ("q_hub_nw", "q_hub_ne"):
    n = 0
    for inst, m in cc[tn].items():
        for pt, tg in m.items():
            if isinstance(tg, list) and "bus:L12_i" in tg:
                m[pt] = addbus(tg, "bus:L12s_i"); n += 1
    CCN[tn] = f"{n} ports +bus:L12s_i (superset)"
rep["core_conns"] = CCN

# ------------------------------------------------------------------ internal stations
def raster(tn):
    t = T[tn]; return HR.Raster(*t["outline_um"], [HR._core_rect(h) for h in t.get("hard_cores", [])])
RR = raster("root")
ycW = r4((win_W[0] + win_W[1]) / 2 - RY0); ycE = r4((win_E[0] + win_E[1]) / 2 - RY0)
ist = T["root"]["internal_stations"]
plans = []
for e in ist:
    c = e.get("conn")
    if c in ("bus:L12_o", "bus:L12m_o"):
        cap = e.get("launch") or e.get("capture") or ""
        inst, _, pt = cap.partition(".")
        newc = "bus:L12s_o" if c == "bus:L12_o" else "bus:L12ms_o"
        to = (0.0, ycW) if c == "bus:L12_o" else (RW, ycE)
        plans.append((e, newc, to, pt in ("tx",)))
excess_r = 0; root_new = []
for e, newc, to, keep in plans:
    n_old = len(e["regs_um"])
    res = HR.route_station(RR, tuple(e["from_um"]), to, 0, REACH)
    nmin = len(res["regs"]) if res else None
    root_new.append((e, newc, to, keep, n_old, res))
    if res: excess_r = max(excess_r, nmin - n_old)
add, conv, fail = [], [], []
for e, newc, to, keep, n_old, _ in root_new:
    res = HR.route_station(RR, tuple(e["from_um"]), to, n_old + excess_r, REACH)
    if not res: fail.append(e.get("launch")); continue
    ne = copy.deepcopy(e) if keep else e
    ne["conn"] = newc; ne["to_um"] = [r4(to[0]), r4(to[1])]; ne["regs_um"] = [list(x) for x in res["regs"]]
    ne["bits"] = min(int(e.get("bits", NS)), NS)
    ne["note"] = (f"DIE-HBM-3 C20f L12 split: {cap if False else ne.get('launch')} -> {newc[4:]} face window "
                  f"({res['kind']}, {res['length_um']} um, {len(res['regs'])} station(s) = L12 path {n_old} + {excess_r}, hops <= 360)")
    (add if keep else conv).append(ne)
ist.extend(add)
rep["root_internal"] = dict(added=len(add), converted=len(conv), failed=fail, excess=excess_r,
                            regs=[(x.get("launch"), x["conn"], len(x["regs_um"])) for x in add + conv])
# root internal endpoints on moved W windows
for e in ist:
    for k in ("from_um", "to_um"):
        p = e[k]
        if abs(p[0]) < 1e-6:
            d = wshift(p[1] + RY0)
            if d:
                p[1] = r4(p[1] + d); moved_pts.append(("root.ist", e.get("conn"), k, d))
                res = HR.route_station(RR, tuple(e["from_um"]), tuple(e["to_um"]), len(e["regs_um"]), REACH)
                if res: e["regs_um"] = [list(x) for x in res["regs"]]
                else: fail.append(("root ripple", e.get("conn")))
# hub twins
excess_h = 0; hub_rep = {}
for tn, ycl in (("q_hub_nw", (win_W[0] + win_W[1]) / 2 - HUBY0), ("q_hub_ne", (win_E[0] + win_E[1]) / 2 - parts["NE_hub"]["origin_um"][1])):
    RH = raster(tn); src = (W_HUB, r4(ycl))
    tw = []
    for e in T[tn]["internal_stations"]:
        if e.get("conn") == "bus:L12_i":
            res = HR.route_station(RH, src, tuple(e["to_um"]), 0, REACH)
            tw.append((e, res))
            if res: excess_h = max(excess_h, len(res["regs"]) - len(e["regs_um"]))
    hub_rep[tn] = dict(src=src, tw=tw, RH=RH)
for tn, h in hub_rep.items():
    new, fl = [], []
    for e, _ in h["tw"]:
        res = HR.route_station(h["RH"], h["src"], tuple(e["to_um"]), len(e["regs_um"]) + excess_h, REACH)
        if not res: fl.append(e.get("capture")); continue
        ne = copy.deepcopy(e); ne["conn"] = "bus:L12s_i"; ne["from_um"] = [r4(h["src"][0]), r4(h["src"][1])]
        ne["regs_um"] = [list(x) for x in res["regs"]]; ne["bits"] = min(int(e.get("bits", NS)), NS)
        ne["note"] = (f"DIE-HBM-3 C20f L12 split twin: L12s_i E/W face window -> {e.get('capture')} ({res['kind']}, "
                      f"{res['length_um']} um, {len(res['regs'])} station(s) = L12_i path {len(e['regs_um'])} + {excess_h}, hops <= 360)")
        new.append(ne)
    T[tn]["internal_stations"].extend(new)
    h.update(added=len(new), failed=fl)
    if tn == "q_hub_nw":
        for e in T[tn]["internal_stations"]:
            for k in ("from_um", "to_um"):
                p = e[k]
                if abs(p[0] - W_HUB) < 1e-6 and e.get("conn") != "bus:L12s_i":
                    d = wshift(p[1] + HUBY0)
                    if d:
                        p[1] = r4(p[1] + d); moved_pts.append(("hub.ist", e.get("conn"), k, d))
                        res = HR.route_station(h["RH"], tuple(e["from_um"]), tuple(e["to_um"]), len(e["regs_um"]), REACH)
                        if res: e["regs_um"] = [list(x) for x in res["regs"]]
                        else: fail.append(("hub ripple", e.get("conn"), e.get("capture")))
rep["hub_twins"] = {tn: dict(added=h["added"], failed=h["failed"], excess=excess_h) for tn, h in hub_rep.items()}
rep["ripple_endpoints"] = len(moved_pts); rep["ripple_fail"] = fail

# ------------------------------------------------------------------ latency (LAT_L12 = 13 kept on all 4 lanes)
import schema as SC
L = {l["id"]: l for l in raw["lanes"]}
for lid in ("L12", "L12m", "L12s", "L12ms"): L[lid]["fixed_cycles"] = 0
Pl = SC.Plan(raw, OUT / "die_plan.json")
TGT = 13
for lid, extra in (("L12", 0), ("L12m", 0), ("L12s", excess_r + excess_h), ("L12ms", excess_r + excess_h)):
    nat = Pl.lane_natural(lid)["cycles"]
    L[lid]["fixed_cycles"] = max(0, TGT - nat - extra)
Pl = SC.Plan(raw, OUT / "die_plan.json")
lat = {}
for lid in Pl.lanes:
    new = Pl.lane_latency(lid); old = raw["latency"]["lanes"].get(lid)
    if old is None or any(old.get(k) != new.get(k) for k in ("cycles", "stations", "boundary", "faces", "fixed", "pad")):
        lat[lid] = dict(old=(old or {}).get("cycles"), new=new["cycles"], fixed=new.get("fixed"), stations=new.get("stations"))
    raw["latency"]["lanes"][lid] = dict(new, param=(old or {}).get("param", "LAT_L12" if lid.startswith("L12") else f"LAT_{lid}"))
rep["latency"] = lat
raw["die"]["label"] = "C20f = C20e + L12 split (1980 b via b101 + 1016 b direct root->hub) + vms_glue +106.272 um | " + raw["die"]["label"].split(" | ", 1)[-1]
(OUT / "die_plan.json").write_text(json.dumps(raw, indent=1))
(OUT / "core_conns.json").write_text(json.dumps(cc, indent=1))
(OUT / "die_plan.sha256").write_text(hashlib.sha256((OUT / "die_plan.json").read_bytes()).hexdigest() + "\n")
(OUT / "c20f_event_report.json").write_text(json.dumps(rep, indent=1, default=str))
print(json.dumps({k: v for k, v in rep.items() if k not in ("b101",)}, default=str)[:4000])
print("b101", json.dumps(b101, default=str)[:1200])
