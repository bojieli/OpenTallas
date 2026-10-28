"""DIE-HBM-10 C23q = C22b + the PHY_N split re-balanced to whole channels (COORD ASK 11:43 DIE-HBM-10, default):
  PHY_NW = PC 0-9 (ot_hbm3e_phy_rc_e8p5_pc0_9), PHY_NC = PC 10-21 (_pc10_21), PHY_NE = PC 22-31 (_pc22_31).
usage: apply_c23q.py C22B_DIR OUT_DIR HUB_EST_JSON VIEWS_DIR TOOLS_DIR
Every PC's in and out bits take ONE path, so no bus crosses a slice cut (PHY window traffic rule, c23_phy_map.json):
  W/E mcb path (hub type N face -> spu0 -> spt0..2 -> mcb -> PHY_NW/NE): data in L8 (10 x 307 = 3070), ctl in L63w
     (10 x 21 = 210, NEW lane), rdata L21 (10 x 256 = 2560), rvalid L114w (10, NEW lane);  NW PCs 0-9, NE PCs 22-31
  centre column (hub type E face -> root -> vsN4..6 -> PHY_NC): data L9 (6 x 307 = 1842), ctl L63 (126),
     rdata L22 (1536, MOVED from the W/E path to the column), rvalid L114 (6, via b112 as today);  NW 10-15, NE 16-21
Geometry:
  * partitions on the 8.64 lattice, macros contiguous from the old PHY origin (old io rect 9797.76..18299.52):
    PHY_NW [9797.76, 12458.88] (2661.12), PHY_NC [12458.88, 15647.04] (3188.16), PHY_NE [15647.04, 18601.92] (2954.88,
    macro at offset 0, 293.76 um spare at the E end as the old PHY_N); PHY_NC's S face covers vsN6 (13357.44..15042.24).
  * each slice: own clk / rst_n taps at its macro clk pin x (LEF, snapped to 8.64) on the S face (as PHY_N), 1 tap.
  * W/E path ft windows repacked inside the old PHY-family block of every face (same start, same order L8, L21, then
    L63w, L114w; old per-bit window density) -> abutting faces stay die-aligned (asserted); foreign windows untouched.
  * column port windows packed from 13358.44: NW L114, L22, L63, L9 | NE L9m, L63m, L22m, L114m (die x); hub E face:
    L9, L63, L22 from the old L9 start, the next port (L156) shifted past the block when hit (asserted no overlap).
  * new ft slots: L63wx1..5 / L114wx1..5 (W path, stations = L8x / L21x sibling), L22x1..3 (vsN6..4, stations = L9 x),
    L22x4 / L22mx4 (root, stations = L9x1 / L9mx1).  Bit sites by ft_corridor.py (run after this script).
  * hub internal stations: every (ctl leaf, pin group) station whose bus changes is re-routed with the SAME router
    (hub_repack.route_station, reach 360 um, the c23q_hub_est.py result); core_conns gain the two new buses.
  * latency table recomputed from the stations (cycles = sum stations + 2 boundary), new params LAT_L63W/L114W(M).
No new checks, no section 12 change; the C22b plan of record is untouched (new dir)."""
import json, sys, shutil, os, hashlib, copy, re, math
from pathlib import Path
SRC, OUT, EST, VIEWS, TOOLS = map(Path, sys.argv[1:6])
sys.path.insert(0, str(TOOLS / "die_plan")); sys.path.insert(0, str(TOOLS))
import hub_repack as HR
P = json.load(open(SRC / "die_plan.json")); T = P["partition_types"]
rep = dict(event="C23q (DIE-HBM-10)", source=str(SRC / "die_plan.json"),
           source_sha=hashlib.sha256((SRC / "die_plan.json").read_bytes()).hexdigest()[:12])
OUT.mkdir(parents=True, exist_ok=True)
if not (OUT / "cores").exists(): shutil.copytree(os.path.realpath(SRC / "cores"), OUT / "cores")
def r4(v): return round(v, 4)
G = 8.64
def snap8(v): return r4(round(v / G) * G)
PART = {p["name"]: p for p in P["partitions"]}
PORT = {p["id"]: p for p in P["ports"]}
LANE = {l["id"]: l for l in P["lanes"]}
DIN, CIN, DOUT, COUT = 307, 21, 256, 1
NW_W, NW_C = 10, 6             # PCs on the W path / column per hub (NE: 10 E path, 6 column)
WID = {"L8": NW_W * DIN, "L63w": NW_W * CIN, "L21": NW_W * DOUT, "L114w": NW_W * COUT,
       "L9": NW_C * DIN, "L63": NW_C * CIN, "L22": NW_C * DOUT, "L114": NW_C * COUT}
OLDW = {"L8": 2456, "L21": 2048, "L22": 2048, "L9": 2456, "L63": 336, "L114": 16}
UMB = 439.248 / 2457           # old window um per pin (2456 + epoch) at the plan's achieved PHY density
def wlen(bits): return max(8.64, round((bits + 1) * UMB, 3))

# ------------------------------------------------------------ 1. PHY partitions + types + io
old = PART["PHY_N"]; ot = T["PHY_N"]; ox, oy = old["origin_um"]; H = ot["outline_um"][1]
LEFS = {}
for d in sorted(VIEWS.iterdir()):
    lef = (d / f"{d.name}.lef").read_text()
    def pin_x(p):
        blk = lef.split(f"  PIN {p}\n")[1]
        return float(blk.split(" RECT ")[1].split()[0])
    LEFS[d.name] = dict(clk_x=pin_x("clk"), w=float(lef.split("SIZE ")[1].split()[0]))
SL = [("PHY_NW", "ot_hbm3e_phy_rc_e8p5_pc0_9", 0.0, 2661.12, (0, 9)),
      ("PHY_NC", "ot_hbm3e_phy_rc_e8p5_pc10_21", 2661.12, 3188.16, (10, 21)),
      ("PHY_NE", "ot_hbm3e_phy_rc_e8p5_pc22_31", 5849.28, 2954.88, (22, 31))]
assert abs(sum(s[3] for s in SL) - ot["outline_um"][0]) < 1e-6
BUSES = {"PHY_NW": [("L8_i", "in", WID["L8"], "data"), ("L63w_i", "in", WID["L63w"], "ctl"),
                    ("L21_o", "out", WID["L21"], "data"), ("L114w_o", "out", WID["L114w"], "ctl")],
         "PHY_NE": [("L8m_i", "in", WID["L8"], "data"), ("L63wm_i", "in", WID["L63w"], "ctl"),
                    ("L21m_o", "out", WID["L21"], "data"), ("L114wm_o", "out", WID["L114w"], "ctl")],
         "PHY_NC": [(f"{b}{m}_{d}", dd, WID[b], k) for m in ("", "m") for b, d, dd, k in
                    (("L9", "i", "in", "data"), ("L63", "i", "in", "ctl"), ("L22", "o", "out", "data"), ("L114", "o", "out", "ctl"))]}
ios = [i for i in P["die"]["io"] if i.get("part") == "PHY_N"]; assert len(ios) == 1
io0 = ios[0]; P["die"]["io"].remove(io0)
newparts = []; rep["phy"] = {}
for name, mac, x0, w, (lo, hi) in SL:
    lf = LEFS[mac]; assert abs(lf["w"] - (w if name != "PHY_NE" else 2661.12)) < 1e-6, (name, lf["w"])
    t = copy.deepcopy(ot)
    t["module"] = "hbm_arch_" + name; t["outline_um"] = [w, H]
    t["buses"] = [dict(name=n, dir=d, width=wd, kind=k) for n, d, wd, k in BUSES[name]]
    tx = snap8(lf["clk_x"])
    t["clock"] = dict(ot["clock"], tap_um=[tx, 4.32], tap_pitch_um=w, taps=[])
    # reset IN: PHY_NC on its S face beside the clock tap (parent vsN6, as PHY_N today); PHY_NW / PHY_NE on the face
    # abutting their only soft neighbour NW_mcb / NE_mcb, facing its reset face site 13 (die y 16640.61, 172.77 above
    # the PHY row): the S-face pin had no rst_o within the 380-um die hop (G0C reset wavefront)
    rt = {"PHY_NW": [0.0, 172.8], "PHY_NE": [w, 172.8]}.get(name, [r4(tx + 8.64), 4.32])
    t["reset"] = dict(ot["reset"], tap_um=rt)
    t["contents"] = [dict(inst="u_phy_Q", module=mac, status="new", cells=0,
                          note=f"C23q slice of the as-built phy_NW (rc_slice --pcs {lo}-{hi}, PHY-only abstract, ASSUMED per-channel-group clock)")]
    t["note"] = f"C23q (DIE-HBM-10): PHY_N slice PCs {lo}-{hi}; macro at partition x 0; clk pin x {lf['clk_x']}"
    T[name] = t
    p = dict(copy.deepcopy(old), name=name, type=name, origin_um=[r4(ox + x0), oy]); newparts.append(p)
    n = hi - lo + 1
    io = copy.deepcopy(io0); io["name"] = f"io_{name}_u_phy_Q"; io["part"] = name
    io["rect_um"] = [r4(ox + x0), io0["rect_um"][1], r4(ox + x0 + lf["w"]), io0["rect_um"][3]]
    io["sites"] = round(io0["sites"] * n / 32); io["signals"] = round(io0["signals"] * n / 32)
    io["note"] = io0["note"] + f" | C23q slice PCs {lo}-{hi} ({n}/32 of sites and signals)"
    P["die"]["io"].append(io)
    rep["phy"][name] = dict(macro=mac, x_um=[r4(ox + x0), r4(ox + x0 + w)], clk_tap_um=[tx, 4.32], pcs=[lo, hi], io_rect=io["rect_um"])
del T["PHY_N"]
P["partitions"] = [q for q in P["partitions"] if q["name"] != "PHY_N"] + newparts
PART = {p["name"]: p for p in P["partitions"]}
assert all(not (i.get("part") == "PHY_N") for i in P["die"]["io"])

# ------------------------------------------------------------ 2. W/E path ft slots: widths, new slots, windows
WTYPES = ["q_spu0", "q_spt0", "q_spt1", "q_spt2", "q_mcb"]
XN = {"q_spu0": (1, 5), "q_spt0": (2, 4), "q_spt1": (3, 3), "q_spt2": (4, 2), "q_mcb": (5, 1)}   # L8 x-index, L21 x-index
rep["wpath"] = {}
for tn in WTYPES:
    t = T[tn]; S_ = {s["name"]: s for s in t["ft_slots"]}
    i8, i21 = XN[tn]
    s8, s21, s22 = S_[f"L8x{i8}"], S_[f"L21x{i21}"], S_[f"L22x{i21}"]
    # blocks per face (type frame) = span of the old L8/L21/L22 windows on that face
    faces = {}
    for s, io_ in ((s8, "in"), (s8, "out"), (s21, "in"), (s21, "out"), (s22, "in"), (s22, "out")):
        f = s[io_ + "_face"]; a, b = s[io_ + "_window_um"]; faces.setdefault(f, []).append((a, b, s["name"], io_))
    others = [(s[io_ + "_face"], s[io_ + "_window_um"], s["name"]) for s in t["ft_slots"]
              if s["name"] not in (s8["name"], s21["name"], s22["name"]) for io_ in ("in", "out") if (io_ + "_window_um") in s]
    s63 = copy.deepcopy(s8); s63["name"] = f"L63wx{i8}"; s63["width"] = WID["L63w"]
    s114 = copy.deepcopy(s21); s114["name"] = f"L114wx{i21}"; s114["width"] = WID["L114w"]
    for s in (s63, s114):
        for k in ("bit_sites_um", "regs_um", "bit_site_cell_um"): s.pop(k, None)
        s["note"] = f"C23q NEW lane slot ({'ctl in' if s is s63 else 'rvalid out'} of the W/E-path PCs), stations = sibling"
    s8["width"] = WID["L8"]; s21["width"] = WID["L21"]
    for s in (s8, s21):
        for k in ("bit_sites_um", "regs_um", "bit_site_cell_um"): s.pop(k, None)
    t["ft_slots"] = [s for s in t["ft_slots"] if s["name"] != s22["name"]] + [s63, s114]
    for f, ws in faces.items():
        lo = min(a for a, b, _, _ in ws); hi = max(b for a, b, _, _ in ws)
        assert not any(ff == f and (w_[0] < hi - 1e-6 and w_[1] > lo + 1e-6) for ff, w_, _ in others), (tn, f, "foreign window in block")
        order = [n for a, b, n, _ in sorted(ws)]                        # old order of L8 / L21 / L22 on this face
        # each new small slot right after its sibling (L63w after L8, L114w after L21): same corner geometry, so the
        # sibling's station count fits its path (G0C reach: L114wx1 behind L8 on the mcb E face had a 379-um hop)
        part = {s8["name"]: s63["name"], s21["name"]: s114["name"]}
        seq = [x for n in order if not n.startswith("L22") for x in (n, part[n])]
        bymap = {s8["name"]: s8, s21["name"]: s21, s63["name"]: s63, s114["name"]: s114}
        x = lo
        for n in seq:
            s = bymap[n]; io_ = "in" if s["in_face"] == f else "out"
            assert s[io_ + "_face"] == f
            L = wlen(s["width"]); s[io_ + "_window_um"] = [r4(x), r4(x + L)]; x = r4(x + L + 0.48)
        assert x - 0.48 <= hi + 1e-6, (tn, f, x, hi)
        rep["wpath"].setdefault(tn, {})[f] = dict(block=[lo, hi], used_to=r4(x - 0.48), seq=seq)
# die alignment of abutting faces (NW instances; NE are the MY mirrors of the same types)
def die_win(part, slot, io_):
    p = PART[part]; t = T[p["type"]]; s = next(s for s in t["ft_slots"] if s["name"] == slot)
    a, b = s[io_ + "_window_um"]; f = s[io_ + "_face"]; base = p["origin_um"][0] if f in "NS" else p["origin_um"][1]
    return f, (r4(base + a), r4(base + b))
CH = [("NW_spu0", 1, 5), ("NW_spt0", 2, 4), ("NW_spt1", 3, 3), ("NW_spt2", 4, 2), ("NW_mcb", 5, 1)]
for (pa, a8, a21), (pb, b8, b21) in zip(CH, CH[1:]):
    for sa, sb, ioa, iob in ((f"L8x{a8}", f"L8x{b8}", "out", "in"), (f"L21x{a21}", f"L21x{b21}", "in", "out"),
                             (f"L63wx{a8}", f"L63wx{b8}", "out", "in"), (f"L114wx{a21}", f"L114wx{b21}", "in", "out")):
        assert die_win(pa, sa, ioa)[1] == die_win(pb, sb, iob)[1], (pa, sa, pb, sb, die_win(pa, sa, ioa), die_win(pb, sb, iob))

# ------------------------------------------------------------ 3. ports + lanes on the W/E path
def setw(pid, w): PORT[pid]["width"] = w
for m, hub, side, phy in (("", "NW_hub", "NW", "PHY_NW"), ("m", "NE_hub", "NE", "PHY_NE")):
    for k in range(6):
        setw(f"L8{m}_{k}", WID["L8"]); setw(f"L21{m}_{k}", WID["L21"])
    PORT[f"L8{m}_5"]["dst"] = dict(part=phy, bus=f"L8{m}_i"); PORT[f"L21{m}_0"]["src"] = dict(part=phy, bus=f"L21{m}_o")
    for k in range(6):                                                   # drop the W/E-path L22
        P["ports"].remove(PORT.pop(f"L22{m}_{k}"))
    chain = [hub, f"{side}_spu0", f"{side}_spt0", f"{side}_spt1", f"{side}_spt2", f"{side}_mcb", phy]
    ids = []
    for k in range(6):                                                   # L63w: hub -> PHY (as L8)
        src = dict(part=chain[k], bus="L63w_o" if k == 0 else f"L63wx{k}_o")
        dst = dict(part=chain[k + 1], bus=f"L63w{m}_i" if k == 5 else f"L63wx{k + 1}_i")
        pid = f"L63w{m}_{k}"; P["ports"].append(dict(id=pid, src=src, dst=dst, width=WID["L63w"], kind="ctl")); PORT[pid] = P["ports"][-1]; ids.append(pid)
    P["lanes"].append(dict(id=f"L63w{m}", ports=ids, note=f"{hub}->{phy} ctl of the W/E-path PCs (C23q)"))
    ids = []
    for k in range(6):                                                   # L114w: PHY -> hub (as L21)
        src = dict(part=chain[6 - k], bus=f"L114w{m}_o" if k == 0 else f"L114wx{k}_o")
        dst = dict(part=chain[5 - k], bus="L114w_i" if k == 5 else f"L114wx{k + 1}_i")
        pid = f"L114w{m}_{k}"; P["ports"].append(dict(id=pid, src=src, dst=dst, width=WID["L114w"], kind="ctl")); PORT[pid] = P["ports"][-1]; ids.append(pid)
    P["lanes"].append(dict(id=f"L114w{m}", ports=ids, note=f"{phy}->{hub} rvalid of the W/E-path PCs (C23q)"))

# ------------------------------------------------------------ 4. column: widths, L22 via the column, windows
COLT = {"vsN6": 4, "vsN5": 3, "vsN4": 2}    # L9 x-index in that type
for m in ("", "m"):
    for k in range(5):
        setw(f"L9{m}_{k}", WID["L9"]); setw(f"L63{m}_{k}", WID["L63"])
    for k in range(6): setw(f"L114{m}_{k}", WID["L114"])
    PORT[f"L9{m}_4"]["dst"] = dict(part="PHY_NC", bus=f"L9{m}_i"); PORT[f"L63{m}_4"]["dst"] = dict(part="PHY_NC", bus=f"L63{m}_i")
    PORT[f"L114{m}_0"]["src"] = dict(part="PHY_NC", bus=f"L114{m}_o")
    for tn, i9 in COLT.items():
        t = T[tn]; S_ = {s["name"]: s for s in t["ft_slots"]}
        S_[f"L9{m}x{i9}"]["width"] = WID["L9"]; S_[f"L63{m}x{i9}"]["width"] = WID["L63"]
        S_[f"L114{m}x{5 - i9}"]["width"] = WID["L114"]
        n = copy.deepcopy(S_[f"L9{m}x{i9}"]); n["name"] = f"L22{m}x{5 - i9}"; n["in_face"], n["out_face"] = "N", "S"
        n["width"] = WID["L22"]; n["note"] = "C23q: rdata of the column PCs, stations = the L9 slot of this type"
        t["ft_slots"].append(n)
    t = T["root"]; S_ = {s["name"]: s for s in t["ft_slots"]}
    S_[f"L9{m}x1"]["width"] = WID["L9"]; S_[f"L63{m}x1"]["width"] = WID["L63"]; S_[f"L114{m}x4"]["width"] = WID["L114"]
    n = copy.deepcopy(S_[f"L9{m}x1"]); n["name"] = f"L22{m}x4"; n["in_face"], n["out_face"] = "N", S_[f"L9{m}x1"]["in_face"]
    n["width"] = WID["L22"]; n["note"] = "C23q: rdata of the column PCs root -> hub (reverse of L9x1), stations = L9x1"
    t["ft_slots"].append(n)
    # L9 / L63 / L114 keep their C22b stations: every kept bit keeps its pin (windows below are anchored on the old
    # lsb end at the old per-bit density), so each stage keeps sites of bits 0..N-1 and old bit N's site becomes the
    # epoch site (the new epoch pin is pin N); regs_um unchanged.  Only the new L22 slots are sited (no sites yet).
    for tn in list(COLT) + ["root"]:
        for s in T[tn]["ft_slots"]:
            if re.match(rf"^L(9|63|114){m}x\d$", s["name"]):
                N = s["width"]; assert all(len(st) > N for st in s["bit_sites_um"]), (tn, s["name"])
                s["bit_sites_um"] = [st[:N + 1] for st in s["bit_sites_um"]]
                s["note"] = s.get("note", "") + f" | C23q: {N} bits, C22b stations kept (bits 0..{N - 1} + old bit {N} site = epoch)"
            elif re.match(rf"^L22{m}x\d$", s["name"]):
                for k in ("bit_sites_um", "regs_um", "bit_site_cell_um"): s.pop(k, None)
    hub ="NW_hub" if not m else "NE_hub"
    l9 = PORT[f"L9{m}_1"]
    chain = ["PHY_NC", "vsN6", "vsN5", "vsN4", "root", hub]
    ids = []
    for k in range(5):
        src = dict(part=chain[k], bus=f"L22{m}_o" if k == 0 else f"L22{m}x{k}_o")
        dst = dict(part=chain[k + 1], bus="L22_i" if k == 4 else f"L22{m}x{k + 1}_i")
        pid = f"L22{m}_{k}"
        pr = dict(id=pid, src=src, dst=dst, width=WID["L22"], kind="data")
        if k < 4: pr.update(face="S", layers=list(l9["layers"]))
        else: pr.update(face=OPPF if False else ("W" if not m else "E"), layers=list(PORT[f"L9{m}_0"]["layers"]))
        if "order" in l9 and k < 4: pr["order"] = l9["order"]
        P["ports"].append(pr); PORT[pid] = pr; ids.append(pid)
    LANE[f"L22{m}"]["ports"] = ids; LANE[f"L22{m}"]["note"] = f"PHY_NC->{hub} rdata of the column PCs via the centre column (C23q)"
# column + hub-face windows: every kept bus keeps its C22b pins.  A narrowed port keeps its old lsb end and its old
# per-pin density (pins spread uniformly, schema.spread), so bits 0..N-1 keep their pins and C22b stations; the new L22
# windows go in the free face span (column: W of L63 for NW, E of L114m for NE; hub face: after L63).
def trim(pid, oldw):
    q = PORT[pid]; a, b = q["window_um"]; L = max(8.64, round((b - a) * (q["width"] + 1) / (oldw + 1), 3))
    q["window_um"] = [r4(b - L), r4(b)] if q.get("order") == "lsb_high" else [r4(a), r4(a + L)]
rep["column"] = {}
for m in ("", "m"):
    for k in range(1, 5): trim(f"L9{m}_{k}", OLDW["L9"]); trim(f"L63{m}_{k}", OLDW["L63"])
    for k in range(4): trim(f"L114{m}_{k}", OLDW["L114"])
L = wlen(WID["L22"])
x0 = r4(PORT["L114_0"]["window_um"][1] + 0.48); x1 = r4(PORT["L114m_0"]["window_um"][1] + 0.48)
for k in range(4):
    PORT[f"L22_{k}"]["window_um"] = [x0, r4(x0 + L)]; PORT[f"L22m_{k}"]["window_um"] = [x1, r4(x1 + L)]
col = sorted({tuple(PORT[f"{b_}{m}_{k}"]["window_um"]) for m in ("", "m") for b_, ks in (("L9", range(1, 5)), ("L63", range(1, 5)),
              ("L114", range(4)), ("L22", range(4))) for k in ks})
assert all(u[1] <= v[0] + 1e-6 for u, v in zip(col, col[1:])), col
assert col[0][0] >= 13358.44 - 1e-6 and col[-1][1] <= 15042.24 - 1.0, col
rep["column"] = dict(windows=[list(w_) for w_ in col], fill=round(sum(w_[1] - w_[0] for w_ in col) / 1684.8, 3))
for m in ("", "m"):
    trim(f"L9{m}_0", OLDW["L9"]); trim(f"L63{m}_0", OLDW["L63"])
    blk = [f"L9{m}_0", f"L63{m}_0", f"L22{m}_4"]; hub = "NW_hub" if not m else "NE_hub"
    y = r4(PORT[f"L63{m}_0"]["window_um"][1] + 0.48)        # L63 keeps its lo end (lsb_low on the hub face)
    assert PORT[f"L63{m}_0"].get("order") != "lsb_high" and PORT[f"L9{m}_0"].get("order") != "lsb_high"
    PORT[f"L22{m}_4"]["window_um"] = [y, r4(y + L)]; y = r4(y + L + 0.48)
    line = [q for q in P["ports"] if q["id"] not in blk and "window_um" in q and q.get("face") in ("E", "W")
            and {q["src"]["part"], q["dst"]["part"]} == {hub, "root"}]
    lo0, hi0 = PORT[f"L22{m}_4"]["window_um"][0], y - 0.48; moved = []
    for q in sorted(line, key=lambda q: q["window_um"][0]):
        a, b = q["window_um"]
        if a < hi0 and b > lo0:
            Lq = b - a; q["window_um"] = [r4(y), r4(y + Lq)]; moved.append(q["id"]); y = r4(y + Lq + 0.48); hi0 = y - 0.48
    ws = sorted([PORT[p]["window_um"] for p in blk] + [q["window_um"] for q in line])
    assert all(a[1] <= b[0] + 1e-6 for a, b in zip(ws, ws[1:])), (m, ws)
    hubt = T[PART[hub]["type"]]; assert ws[-1][1] <= PART[hub]["origin_um"][1] + hubt["outline_um"][1] + 1e-6
    rep.setdefault("hub_face", {})[hub] = dict(block={p: PORT[p]["window_um"] for p in blk}, shifted=moved)

# b112 relay of the column rvalid (L114x5, shared NW/NE type via MY): 16 -> 6 bits.  Windows are already the 8.64-um
# minimum; each stage keeps its first 6 payload sites + the epoch site (same positions, regs and stations unchanged).
s = next(s for s in T["q_b112"]["ft_slots"] if s["name"] == "L114x5"); assert s["width"] == OLDW["L114"]
s["bit_sites_um"] = [st[:WID["L114"]] + [st[-1]] for st in s["bit_sites_um"]]; s["width"] = WID["L114"]
s["note"] = s.get("note", "") + " | C23q: 6 column-PC rvalid bits (sites 0-5 + epoch kept)"

# ------------------------------------------------------------ 5. hub buses + internal stations + core_conns
EST_ = json.load(open(EST))
for hub, tn in (("NW_hub", "q_hub_nw"), ("NE_hub", "q_hub_ne")):
    t = T[tn]; bus = {b["name"]: b for b in t["buses"]}
    for b, w in (("L8_o", WID["L8"]), ("L21_i", WID["L21"]), ("L9_o", WID["L9"]), ("L22_i", WID["L22"]),
                 ("L63_o", WID["L63"]), ("L114_i", WID["L114"])):
        bus[b]["width"] = w
    t["buses"] += [dict(name="L63w_o", dir="out", width=WID["L63w"], kind="ctl"), dict(name="L114w_i", dir="in", width=WID["L114w"], kind="ctl")]
    e = EST_[tn]; det = e["stations_detail"]
    W_, H_ = t["outline_um"]
    R = HR.Raster(W_, H_, [HR._core_rect(h) for h in t["hard_cores"]])
    BUS6 = ("L8_o", "L9_o", "L21_i", "L22_i", "L63_o", "L114_i")
    k = 0; changed = 0
    sts = [(i, s) for i, s in enumerate(t["internal_stations"])
           if any(s.get("launch") == "face bus " + b or s.get("capture") == "face bus " + b for b in BUS6)]
    # face windows in the hub frame from the REAL new windows: N face = spu0 S-face slot windows + 760.32 (NW R0; NE MY gives
    # the same offset), E face = root-line port windows - 6065.28 (die y).  Each station's face point sits at its census-bit
    # position inside its new window (scaled to the window); r10 abutment intervals copied from a template station per face.
    sp = {s["name"]: s for s in T["q_spu0"]["ft_slots"]}; dx = r4(PART["NW_spu0"]["origin_um"][0] - PART["NW_hub"]["origin_um"][0])
    oy_ = PART[hub]["origin_um"][1]; m_ = "" if hub == "NW_hub" else "m"
    win = {"L8_o": ("N",) + tuple(x + dx for x in sp["L8x1"]["in_window_um"]), "L21_i": ("N",) + tuple(x + dx for x in sp["L21x5"]["out_window_um"]),
           "L63w_o": ("N",) + tuple(x + dx for x in sp["L63wx1"]["in_window_um"]), "L114w_i": ("N",) + tuple(x + dx for x in sp["L114wx5"]["out_window_um"]),
           "L9_o": ("E",) + tuple(y - oy_ for y in PORT[f"L9{m_}_0"]["window_um"]), "L63_o": ("E",) + tuple(y - oy_ for y in PORT[f"L63{m_}_0"]["window_um"]),
           "L22_i": ("E",) + tuple(y - oy_ for y in PORT[f"L22{m_}_4"]["window_um"])}
    assert abs(dx - 760.32) < 1e-6
    tmpl = {}
    for _, s in sts:
        if "r10" in s: tmpl.setdefault(s["r10"]["face"], s["r10"])
    sts = [(i, s) for i, s in enumerate(t["internal_stations"])
           if any(s.get("launch") == "face bus " + b or s.get("capture") == "face bus " + b for b in BUS6)]
    assert len(sts) == len(det)
    from collections import Counter
    fill = Counter(); rng = {}
    for (i, s), d in sorted(zip(sts, det), key=lambda z: (z[1]["new"], int(z[1]["inst"].rsplit("_p", 1)[1]), z[1]["grp"])):
        rng[i] = (fill[d["new"]], fill[d["new"]] + d["bits"]); fill[d["new"]] += d["bits"]
    for (i, s), d in zip(sts, det):
        assert s["bits"] == d["bits"] and d["inst"] in (s["capture"] + s["launch"])
        if d["new"] == d["bus"]:
            pass
        face_first = s["launch"].startswith("face bus")
        if d["new"] == "L114_i":
            fp = s["from_um"] if face_first else s["to_um"]
        else:
            f, a0, a1 = win[d["new"]]; lo, hi = rng[i]; mm = a0 + (lo + hi) / 2 * (a1 - a0) / fill[d["new"]]
            fp = [r4(mm), H_] if f == "N" else [W_, r4(mm)]
        cp = s["to_um"] if face_first else s["from_um"]
        a, b = (fp, cp) if face_first else (cp, fp)
        if d["new"] == d["bus"] and list(fp) == list(s["from_um"] if face_first else s["to_um"]):
            continue
        res = HR.route_station(R, tuple(a), tuple(b), len(s["regs_um"]), 360.0)
        assert res is not None, (tn, d)
        s["from_um"], s["to_um"] = list(a), list(b)
        s["regs_um"] = [list(r) for r in res["regs"]]
        nb = d["new"]; s["conn"] = "bus:" + nb
        if face_first: s["launch"] = "face bus " + nb
        else: s["capture"] = "face bus " + nb
        if "r10" in s:
            fc = "N" if nb == "L114_i" else win[nb][0]
            s["r10"] = dict(copy.deepcopy(tmpl[fc]) if s["r10"]["face"] != fc else s["r10"], bus=nb, fend=s["r10"]["fend"])
        s["note"] = s.get("note", "").split(" | C23q")[0] + f" | C23q regroup {d['bus']}->{nb} ({res['kind']}, {res['length_um']} um, {len(res['regs'])} st)"
        changed += 1
    rep.setdefault("hub_stations", {})[tn] = dict(stations=len(sts), rerouted=changed, max_regs=max(len(s["regs_um"]) for _, s in sts))
CC = json.load(open(SRC / "core_conns.json"))
for tn in ("q_hub_nw", "q_hub_ne"):
    for inst, pins in CC.get(tn, {}).items():
        for pn, lst in pins.items():
            if isinstance(lst, list) and "bus:L8_o" in lst:
                for nb in ("bus:L63w_o", "bus:L114w_i"):
                    if nb not in lst: lst.append(nb)

# ------------------------------------------------------------ 6. latency table
lat = P["latency"]["lanes"]
def stations_of(pid):
    pr = PORT[pid]; n = 0
    for end in ("src",):
        prt = pr[end]["part"]; bn = pr[end]["bus"]
        if prt in PART:
            for s in T[PART[prt]["type"]].get("ft_slots", []):
                if bn == s["name"] + "_o": n += s["stations"]
    return n
for lid in ("L8", "L8m", "L21", "L21m", "L22", "L22m", "L9", "L9m", "L63", "L63m", "L114", "L114m", "L63w", "L63wm", "L114w", "L114wm"):
    ids = LANE[lid]["ports"] if lid in LANE else next(l for l in P["lanes"] if l["id"] == lid)["ports"]
    st = sum(stations_of(p) for p in ids)
    e = lat.get(lid, dict(fixed=0, pad=0, param="LAT_" + lid.upper()))
    old_c = e.get("cycles")
    e.update(stations=st, boundary=2, faces=len(ids), natural=st + 2, cycles=st + 2 + e.get("pad", 0))
    lat[lid] = e
    rep.setdefault("latency", {})[lid] = [old_c, e["cycles"]]
P["note"] = (P.get("note") or "") + " | C23q (DIE-HBM-10 10-28): PHY_N -> PHY_NW/NC/NE (PC 0-9 / 10-21 / 22-31), per-PC bus regroup"
txt = json.dumps(P, indent=1); (OUT / "die_plan.json").write_text(txt)
(OUT / "die_plan.sha256").write_text(hashlib.sha256(txt.encode()).hexdigest() + "  die_plan.json\n")
json.dump(CC, open(OUT / "core_conns.json", "w"), indent=1)
for f in os.listdir(SRC):
    if f.endswith(".json") and not (OUT / f).exists() and f not in ("die_plan.json",):
        shutil.copy(SRC / f, OUT / f)
# as-built PC map (side file; the repo map is not touched)
pcmap = {}
for pc in range(32):
    part = "PHY_NW" if pc <= 9 else "PHY_NC" if pc <= 21 else "PHY_NE"
    lo = {"PHY_NW": 0, "PHY_NC": 10, "PHY_NE": 22}[part]
    hub = ("NW", pc) if pc < 16 else ("NE", pc - 16)
    path = "W" if pc <= 9 else "E" if pc >= 22 else "column"
    pcmap[pc] = dict(partition=part, macro_local_pc=pc - lo, hub_ctl=f"ctl_{hub[0]}_p{hub[1]:02d}", path=path)
side = dict(pc_map=pcmap, regions={"PHY_NW": "T060W", "PHY_NC": "T060C", "PHY_NE": "T060E"},
            region_parent={"T060W": "T059", "T060C": "T057", "T060E": "T061"})
json.dump(side, open(OUT / "c23q_side.json", "w"), indent=1)
json.dump(rep, open(OUT / "c23q_event_report.json", "w"), indent=1)
print(json.dumps(rep, indent=1)[:4000])
