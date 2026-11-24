#!/usr/bin/env python3
"""S81-KVLEAF-T2-ARCH-R2 11-23: kv_leaf t2 part B, hand-drawn seating v1 for the slot 4527.36 x 1918.08.

Regions (um):  part A band keeps x < 1460, y < 1245 (S81-MISC-SERDES-J9).  Region B = x >= 1470 below y 1245; above
y 1260 the full width.  Data flow, bottom to top:
  row 1   clusters 0..3      a cluster kb = its 4 norm engines (2 x 2) | quant block kvq | CN writer; odd clusters are
  row 2   clusters 4..7      mirrored so the quant blocks of a pair (kb, kb ^ 1) ABUT (the pair link takes no stage)
  spine   4 taps (702 x 25.92, two levels of two) + the 4 half trees, the reduce and the IK reduce beside them
  row 3   clusters 8..11
  row 4   clusters 12..15    the IK clusters: CN writer over IK writer; clusters 14 / 15 carry the RoPE engines
  top     8 pool lanes; the 144 store SRAMs re-packed 12 x 12 above the leaf band
Output: seats (same record form as the Codex seating), link census per family, the XD nibbles the seating needs."""
import json, math, sys, collections
import os
W, H = float(os.environ.get('SEAT_W', '3214.08')), float(os.environ.get('SEAT_H', '2160.0'))   # piece 1 (B) frame = slot frame x - 1468.8
G = 4.32
snap = lambda v: round(v / G) * G
SZ = dict(kvec=(138.24, 138.24), kvpc=(211.68, 129.6), kvq=(259.2, 259.2), cnw=(181.44, 194.4), ikw=(181.44, 194.4),
          ikr=(198.72, 198.72), cpl=(172.8, 190.08), kvr=(140.4, 140.4), qnh=(114.48, 114.48), kvtc=(702.0, 25.92),
          kvi=(34.56, 34.56), sram=(31.992, 17.304))
MOD = dict(kvec="dsfd_su_t_kvec", kvpc="dsfd_su_t_kvpc", kvq="dsfd_su_t_kvq", cnw="dsfd_su_t_cnw", ikw="dsfd_su_t_ikw",
           ikr="dsfd_su_t_ikr", cpl="dsfd_sl_t_cpl", kvr="dsfd_su_t_kvr", qnh="dsfd_su_t_qnh", kvtc="dsfd_su_t_kvtc")
seats = []; rects = []
def put(master, slot, x, y, path):
    x, y = snap(x), snap(y); w, h = SZ[master]
    assert x >= 0 and y >= 0 and x + w <= W + 1e-6 and y + h <= H + 1e-6, (master, slot, x, y)
    for n, a, b, c, d in rects:
        assert not (x < c - 1e-6 and x + w > a + 1e-6 and y < d - 1e-6 and y + h > b + 1e-6), (master, slot, "overlaps", n)
    rects.append((f"{master}{slot}", x, y, x + w, y + h))
    seats.append(dict(master=master, slot=slot, origin_um=[round(x, 3), round(y, 3)], outline_um=list(SZ[master]), orient="R0",
                      elaborated_path=path, module=MOD.get(master, master)))
    return (x + w / 2, y + h / 2)
C = {}
kve_path = lambda ke: f"u_bank.g_kve[{ke}].g_rpc.u_kve" if ke >= 56 else f"u_bank.g_kve[{ke}].genblk2.g_npc.u_kve"
GAP = 12.96
def cluster(kb, x0, y0, mirror, ik):
    eng = "kvpc" if kb >= 14 else "kvec"; ew, eh = SZ[eng]
    wE = 2 * ew + GAP; wQ = SZ["kvq"][0]; wC = SZ["cnw"][0]
    width = wE + GAP + wC + GAP + wQ
    # order left to right: engines | CN (IK) writer | quant; mirrored: quant | writer | engines
    xe, xc, xq = (x0, x0 + wE + GAP, x0 + wE + GAP + wC + GAP) if not mirror else (x0 + wQ + GAP + wC + GAP, x0 + wQ + GAP, x0)
    for i in range(4):
        ke = 4 * kb + i
        C[("kve", ke)] = put(eng, ke, xe + (i % 2) * (ew + GAP), y0 + (i // 2) * (eh + GAP), kve_path(ke))
    C[("kvq", kb)] = put("kvq", kb, xq, y0, f"u_bank.g_kvq[{kb}].g_closed.u_kvq")
    C[("cnw", kb)] = put("cnw", kb, xc, y0, f"u_bank.g_kvq[{kb}].g_cn.g_cwc.u_cn_write")
    if ik:
        C[("ikw", kb)] = put("ikw", kb - 12, xc, y0 + SZ["cnw"][1] + GAP, f"u_bank.g_kvq[{kb}].g_cn.g_ik_write.g_iwc.u_ik_write")
    return width
def row(kbs, x0, y0, ik=False):
    x = x0
    for j, kb in enumerate(kbs):
        eng = "kvpc" if kb >= 14 else "kvec"
        w = 2 * SZ[eng][0] + GAP + GAP + SZ["cnw"][0] + GAP + SZ["kvq"][0]
        cluster(kb, x, y0, mirror=(j % 2 == 1), ik=ik)
        x += w + (0.0 if j % 2 == 0 else VCH)          # a pair abuts at its quant blocks; a vertical channel between pairs
    return x
EXR, EXS, EXV = (float(os.environ.get(k, d)) for k, d in (('SEAT_EXR', '0'), ('SEAT_EXS', '60.48'), ('SEAT_EXV', '0')))   # v5: one kvx lane beside every channel
VCH = float(os.environ.get('SEAT_VCH', '108.0')) + EXV
XB = 64.8                                                 # west lane 60.48: input relays and exit relays share it
Y1 = 21.6; Y2 = Y1 + 289.44 + 82.08 + EXR; YS = Y2 + 289.44 + 82.08 + EXS; SPH = 259.2; Y3 = YS + SPH + 82.08 + EXS; Y4 = Y3 + 289.44 + 82.08 + EXR; YT = 0
e1 = row([0, 1, 2, 3], XB, Y1); row([4, 5, 6, 7], XB, Y2); row([8, 9, 10, 11], XB, Y3)
# row 4 (IK clusters), B form.  Clusters 12 / 13 (norm engines): CN writer above the engines, IK writer above the
# quant.  Clusters 14 / 15 (RoPE engines, wider): CN | IK writer above the engines, a pool lane above the quant.
G4 = 25.92          # row 4 is 510 tall: the gap above its engines / quants is a feed-through station band
def cluster4(kb, x0, y0, mirror):
    eng = "kvpc" if kb >= 14 else "kvec"; ew, eh = SZ[eng]; wL = 2 * ew + GAP; hE = 2 * eh + GAP; wQ = SZ["kvq"][0]
    xl, xq = (x0, x0 + wL + GAP) if not mirror else (x0 + wQ + GAP, x0)
    for i in range(4):
        ke = 4 * kb + i
        C[("kve", ke)] = put(eng, ke, xl + (i % 2) * (ew + GAP), y0 + (i // 2) * (eh + GAP), kve_path(ke))
    C[("kvq", kb)] = put("kvq", kb, xq, y0, f"u_bank.g_kvq[{kb}].g_closed.u_kvq")
    C[("cnw", kb)] = put("cnw", kb, xl, y0 + hE + G4, f"u_bank.g_kvq[{kb}].g_cn.g_cwc.u_cn_write")
    ikp = f"u_bank.g_kvq[{kb}].g_cn.g_ik_write.g_iwc.u_ik_write"
    if kb < 14:
        C[("ikw", kb)] = put("ikw", kb - 12, xq + (0 if mirror else wQ - SZ["ikw"][0]), y0 + wQ + G4, ikp)
    else:
        C[("ikw", kb)] = put("ikw", kb - 12, xl + SZ["cnw"][0] + GAP, y0 + hE + G4, ikp)
        l = kb - 14; C[("cpl", l)] = put("cpl", l, xq + (0 if mirror else wQ - SZ["cpl"][0]), y0 + wQ + G4, f"g_cp.u_pool.g_lanec[{l}].u_l")
    return wL + GAP + wQ
x4 = XB
for j, kb in enumerate([12, 13, 14, 15]):
    x4 += cluster4(kb, x4, Y4, j % 2 == 1) + (0.0 if j % 2 == 0 else VCH)
e4 = x4 - VCH
# spine, left to right in the order SEAT_SPINE (default taps | store | half trees | reduce | IK reduce: the store by the
# mid channel so the exit chains are short); store SRAMs 18 x 8, half trees 2 x 2, taps two levels of two
sram = []; xs_ = XB
for blk in os.environ.get("SEAT_SPINE", "taps,store,qnh,kvr,ikr").split(","):
    if blk == "store":
        # 16 slot groups g_store[s] of 9 SRAMs (3 x 3 = 129.6 x 90.72), 8 x 2: the lower row holds the slots of the
        # cluster rows below the spine, the upper row the others, so every exit chain lands beside its own slot
        sram = [None] * 144
        for r_, order in enumerate(([0, 4, 1, 5, 2, 6, 3, 7], [8, 12, 9, 13, 10, 14, 11, 15])):
            for c_, sl in enumerate(order):
                gx, gy = xs_ + c_ * 129.6, YS + 30.24 + r_ * (90.72 + 17.28)
                for w_ in range(9):
                    x, y = snap(gx + (w_ % 3) * 43.2), snap(gy + (w_ // 3) * 30.24)
                    rects.append((f"sram{9 * sl + w_}", x, y, x + 31.992, y + 17.304)); sram[9 * sl + w_] = [x, y]
                C[("store", sl)] = (gx + 60.48, gy + 38.88)
        sx0 = xs_; xs_ += 8 * 129.6 + 12.96
    elif blk == "qnh":
        for hh in range(4):
            C[("qnh", hh)] = put("qnh", hh, xs_ + (hh % 2) * (114.48 + GAP), YS + 8.64 + (hh // 2) * (114.48 + GAP), f"u_bank.g_kvr.g_kvh[{hh}].g_closed.u_qnh")
        xs_ += 2 * (114.48 + GAP) + 25.92
    elif blk == "taps":
        xt = xs_; xm = xt + 702 + 8.64
        for u in range(4):
            C[("kvt", u)] = put("kvtc", u, xt + (u % 2) * (702 + 17.28), YS + 73.44 + (u // 2) * (25.92 + 60.48), f"u_bank.g_u[{u}].g_closed.u_kvt")
        xs_ += 2 * 702 + 17.28 + 25.92
    elif blk == "kvr":
        C[("kvr", 0)] = put("kvr", 0, xs_, YS + 60.48, "u_bank.g_kvr.g_closed.u_kvr"); xs_ += 140.4 + GAP
    elif blk == "ikr":
        C[("ikr", 0)] = put("ikr", 0, xs_, YS + 30.24, "u_bank.g_iks.g_closed.u_ik_reduce"); xs_ += 198.72 + GAP
for l in range(2, 8):      # six pool lanes in two columns of three, east of row 4
    C[("cpl", l)] = put("cpl", l, W - 4.32 - (2 - (l - 2) // 3) * SZ["cpl"][0] - (1 - (l - 2) // 3) * GAP, Y3 + 289.44 + 12.96 + ((l - 2) % 3) * (190.08 + GAP), f"g_cp.u_pool.g_lanec[{l}].u_l")
# ---- N-S feed-through corridors of piece 1 (B frame x): their station ranks get reserved bands (12.96 tall, no relay
# seat) at the bottom edge of every horizontal channel, inside the spine at its two edges, under row 3 and above row 4; inside row 4 the
# rank is the G4 gap above the engines / quants, in the pool-lane stack the two gaps between lanes
FTC = [(333.2, 1149.2), (2512.2, 3207.2)]
FTY = [Y1 + 289.44, Y2 + 289.44, YS + SPH - 21.6, Y3 - 12.96, Y3 + 289.44]       # + the rank inside row 4 (below)
ftst = []
for (fx0, fx1) in FTC:
    for fy in FTY:
        x0_, x1_ = fx0, fx1
        cut = [(a_, c_) for n_, a_, b_, c_, d_ in rects if a_ < x1_ and c_ > x0_ and b_ < fy + 12.96 and d_ > fy]     # blocks in the band (pool stack)
        segs = [(x0_, x1_)]
        for a_, c_ in sorted(cut):
            segs = [q for (p0, p1) in segs for q in ((p0, min(p1, a_)), (max(p0, c_), p1)) if q[1] - q[0] > 1.0]
        for p0, p1 in segs: ftst.append([round(p0, 2), round(fy, 2), round(p1, 2), round(fy + 12.96, 2)])
# rank inside row 4: per x segment of a corridor the lowest clear 12.96 band in the window above the engines / quants
# (the G4 gap); in the pool-lane stack the two gaps between lanes are the ranks, so that x range gets two bands
def clear_bands(fx0, fx1, y_lo, y_hi):
    xs = sorted({fx0, fx1} | {v for n_, a_, b_, c_, d_ in rects if b_ < y_hi and d_ > y_lo for v in (a_, c_) if fx0 < v < fx1})
    out = []
    for p0, p1 in zip(xs, xs[1:]):
        if p1 - p0 < 4.0: continue
        y = y_lo
        while y + 12.96 <= y_hi + 1e-6:
            if not any(a_ < p1 - 1e-6 and c_ > p0 + 1e-6 and b_ < y + 12.96 - 1e-6 and d_ > y + 1e-6 for n_, a_, b_, c_, d_ in rects):
                out.append([round(p0, 2), round(y, 2), round(p1, 2), round(y + 12.96, 2)]); break
            y += 4.32
    return out
r4 = []
for (fx0, fx1) in FTC:
    r4 += clear_bands(fx0, fx1, Y4 + 250.56, Y4 + 328.32)
    r4 += clear_bands(max(fx0, W - 4.32 - 2 * 172.8 - 12.96), fx1, Y3 + 289.44 + 12.96 + 190.08, Y3 + 289.44 + 12.96 + 190.08 + 12.96) if fx1 > W - 400 else []
    r4 += clear_bands(max(fx0, W - 4.32 - 2 * 172.8 - 12.96), fx1, Y3 + 289.44 + 12.96 + 2 * 190.08 + 12.96, Y3 + 289.44 + 12.96 + 2 * 190.08 + 25.92) if fx1 > W - 400 else []
ftst += r4
rects.append(("seam_landing", 0.0, Y2 + 289.44 + 12.96, 60.48, YS - 4.32))       # west face: the seam input landing stage (418 flops) + its clock tap
for i, (a_, b_, c_, d_) in enumerate(ftst): rects.append((f"ftst{i}", a_, b_, c_, d_))
man = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])
# an engine leaves the tap pair at its own slot along the 1421-um tap row (position KP = ke / 2 of 32), so the
# 64 relay chains do not all start at one point
tapc = lambda ke: (xm - 702 - 8.64 + ((ke // 2) + 0.5) / 32 * (2 * 702 + 17.28), (C[("kvt", 2 * (ke % 2))][1] + C[("kvt", 2 * (ke % 2) + 1)][1]) / 2)
fam = collections.defaultdict(list)
for ke in range(64):
    fam["XIN in"].append(man(tapc(ke), C[("kve", ke)]))
    if ke >= 56: fam["XCS rope"].append(man(tapc(ke), C[("kve", ke)]))
    fam["XP partial"].append(man(C[("kve", ke)], C[("qnh", ke // 16)]))
    if ke >= 48: fam["XP partial"].append(man(C[("kve", ke)], C[("ikr", 0)])); fam["XR return"].append(man(C[("ikr", 0)], C[("kve", ke)]))
    fam["XR return"].append(man(C[("kvr", 0)], C[("kve", ke)]))
    kb = ke // 4
    fam["XYQ y-kvq"].append(man(C[("kve", ke)], C[("kvq", kb)])); fam["XYC y-cnw"].append(man(C[("kve", ke)], C[("cnw", kb)]))
    if kb >= 12: fam["XYI y-ikw"].append(man(C[("kve", ke)], C[("ikw", kb)]))
for hh in range(4): fam["XH qnh-kvr"].append(man(C[("qnh", hh)], C[("kvr", 0)])); fam["XGO go"].append(man(C[("kvt", 0)], C[("qnh", hh)]))
fam["XGO go"] += [man(C[("kvt", 0)], C[("kvr", 0)]), man(C[("kvt", 0)], C[("ikr", 0)])]
for kb in range(16):
    fam["PAIR (must be 0)"].append(man(C[("kvq", kb)], C[("kvq", kb ^ 1)]) - 259.2)
    fam["XG election"].append(man(C[("kvq", kb)], C[("kvq", kb | 7)]))
    fam["XO exits"] += [man(C[(m, kb)], C[("store", kb)]) for m in ("kvq", "cnw")] + ([man(C[("ikw", kb)], C[("store", kb - 12)])] if kb >= 12 else [])
EXIST = {"XH qnh-kvr": 0, "PAIR (must be 0)": 0}
HOP = 400.0
xd = {}; census = {}
for k, v in fam.items():
    need = max(0, math.ceil(max(v) / HOP) - 1); x = max(0, need - EXIST.get(k, 3))
    census[k] = dict(links=len(v), worst_centre_um=round(max(v), 1), regs_needed=need, regs_existing=EXIST.get(k, 3), extra=x)
    xd[k.split()[0]] = x
    print(f"{k:18s} links {len(v):3d} worst {max(v):7.1f} um  regs needed {need}  existing {EXIST.get(k,3)}  extra {x}")
assert xd["PAIR"] == 0 and max(fam["PAIR (must be 0)"]) < 1e-6
order = ["XIN", "XCS", "XP", "XR", "XYQ", "XYC", "XYI", "XH", "XG", "XGO", "XO"]
assert all(xd[o] <= 15 for o in order)
val = sum(xd[o] << (4 * i) for i, o in enumerate(order)); print("XD = 48'h%012x" % val)
occ = lambda x, y, w, h: any(x < c - 1e-6 and x + w > a + 1e-6 and y < d - 1e-6 and y + h > b + 1e-6 for n, a, b, c, d in rects)
# ---- v5 exit relays (kvx masters), seated after the input relays.  A chain goes from its block (quant: kvq centre, IK:
# ikw centre) to the store; its seats come from a breadth-first search over ALL free seats (grid 21.6, 4.32 clear of
# every block), each hop (centre to centre, Manhattan) <= HOPX, fewest stages first.  XST[kb] = stages of block kb
# (its quant chain and, for the IK blocks, its IK chain carry the same count).
import numpy as np
KX = float(os.environ.get("SEAT_KVX", "51.84")); HOPX = float(os.environ.get("SEAT_HOPX", "380"))
def free_cands(K=None):
    K = K or KX
    P = [(snap(i * 21.6), snap(j * 21.6)) for i in range(int((W - K) / 21.6) + 1) for j in range(int((H - K) / 21.6) + 1)]
    return np.array([(x, y) for x, y in P if not occ(x - 4.32, y - 4.32, K + 8.64, K + 8.64)])
def route(src, dst, cand, nmin, K=None, first=None):
    """seats (origins) of a chain with >= nmin stages, or None"""
    K = K or KX; first = first or HOPX
    cc = cand + K / 2
    d_s = np.abs(cc - np.array(src)).sum(1); d_t = np.abs(cc - np.array(dst)).sum(1)
    layers = [d_s <= first]
    for n in range(1, 16):
        if n >= max(1, nmin) and (layers[-1] & (d_t <= HOP)).any(): break
        prev = cc[layers[-1]]
        if len(prev) == 0: return None
        # reach: within HOPX of any node of the previous layer (chunked)
        r = np.zeros(len(cc), bool)
        for k in range(0, len(prev), 400):
            r |= (np.abs(cc[:, None, :] - prev[None, k:k + 400, :]).sum(2) <= HOPX).any(1)
        layers.append(r)
    else: return None
    # backtrack: last seat nearest the store, then each predecessor the one nearest the straight line to the source
    path = []; used = np.zeros(len(cc), bool); nxt = None
    for k in range(len(layers) - 1, -1, -1):
        m = layers[k] & ~used
        if nxt is None: m &= d_t <= HOP; cost = d_t
        else: m &= np.abs(cc - cc[nxt]).sum(1) <= HOPX; cost = d_s + 0.25 * np.abs(cc - cc[nxt]).sum(1)
        if k == 0: m &= d_s <= first
        if not m.any(): return None
        i = np.where(m)[0][np.argmin(cost[m])]; path.append(i); used[i] = True; nxt = i
        # a seat blocks every candidate it overlaps (with clearance) for the rest of this chain
        used |= (np.abs(cand[:, 0] - cand[i, 0]) < K + 4.32) & (np.abs(cand[:, 1] - cand[i, 1]) < K + 4.32)
    return [tuple(cand[i]) for i in reversed(path)]
xrel = []; xhops = []; XST = [0] * 16; fail = []
dstof = lambda kind, kb: C[("store", kb if kind == "q" else kb - 12)]
chains = [("q", kb, C[("kvq", kb)]) for kb in range(16)] + [("i", kb, C[("ikw", kb)]) for kb in range(12, 16)]
def commit(kind, kb, src, seatsxy):
    prev = src; dst = dstof(kind, kb)
    for st, (x, y) in enumerate(seatsxy):
        assert not occ(x - 4.32, y - 4.32, KX + 8.64, KX + 8.64)
        rects.append((f"kvx{kind}{kb}_{st}", x, y, x + KX, y + KX)); c = (x + KX / 2, y + KX / 2)
        xhops.append((man(prev, c), kind, kb, st)); prev = c
        xrel.append(dict(master="kvx", chain=kind, block=kb, stage=st, origin_um=[round(float(x), 3), round(float(y), 3)], outline_um=[KX, KX], orient="R0", module="dsfd_su_t_kvx",
                         elaborated_path=(f"u_bank.g_kvq[{kb}].g_exit_relay[{st}].u_relay" if kind == "q" else f"u_bank.g_kvq[{kb}].g_cn.g_ikr.g_ik_relay[{st}].u_relay")))
    xhops.append((man(prev, dst), kind, kb, len(seatsxy)))
for kb in sorted(range(16), key=lambda k: man(C[("kvq", k)], C[("store", k)])):          # near blocks first: they have the least freedom
    mine = [c for c in chains if c[1] == kb]; n = 1
    for attempt in range(8):                     # the quant chain and the IK chain of a block carry the same count
        mark = (len(rects), len(xrel), len(xhops)); ok = True
        for kind, _, src in mine:
            r = route(src, dstof(kind, kb), free_cands(), n)
            if r is None: ok = None; break
            if len(r) != n: n = len(r); ok = False; break
            commit(kind, kb, src, r)
        if ok: break
        del rects[mark[0]:], xrel[mark[1]:], xhops[mark[2]:]
        if ok is None: break
    if not ok: fail.append(kb)
    XST[kb] = int(n)
print("XST = 64'h%016x" % sum(k << (4 * i) for i, k in enumerate(XST)), XST, "unrouted", fail)
for h in sorted(xhops, reverse=True)[:3]: print("  xhop", round(h[0], 1), h[1:])
print("exit relays", len(xrel), "kvx", KX, "hops over", HOP, ":", sum(h[0] > HOP for h in xhops), "of", len(xhops))
census["XO exit relays"] = dict(chains=len(chains), stages_by_block=XST, xst="64'h%016x" % sum(k << (4 * i) for i, k in enumerate(XST)), seats=len(xrel), kvx_um=KX,
                                worst_hop_centre_um=round(float(max(xhops)[0]), 1), hops_over=int(sum(h[0] > HOP for h in xhops)), unrouted=[str(f) for f in fail])
# ---- input relays (kvi masters), same search (after the exit relays, which are larger and fewer).  A chain goes from
# the engine's place on the tap row to the engine; the tap is bit-local, so ONE soft, bit-individual funnel stage
# (XINS) comes first: the first kvi may sit two hops from the tap.  KST[kb] = stages of the 4 engines of block kb.
FUN = 1; KI = 34.56
relays = []; hops = []; KST = [1] * 16; ifail = []; L = {ke: man(tapc(ke), C[("kve", ke)]) for ke in range(64)}
for kb in sorted(range(16), key=lambda k: -max(L[4 * k + i] for i in range(4))):
    n = 1
    for attempt in range(8):                     # all 4 engines of a block carry the same count: retry deeper until they do
        mark = (len(rects), len(relays), len(hops)); ok = True
        for i in range(4):
            ke = 4 * kb + i; r = route(tapc(ke), C[("kve", ke)], free_cands(KI), n, KI, 2 * HOPX)
            if r is None: ok = None; break
            if len(r) != n: n = len(r); ok = False; break
            prev = None
            for st, (x, y) in enumerate(r):
                rects.append((f"kvi{ke}_{st}", x, y, x + KI, y + KI)); c = (x + KI / 2, y + KI / 2)
                if prev is not None: hops.append(man(prev, c))
                prev = c
                relays.append(dict(master="kvi", engine=ke, stage=st, origin_um=[round(float(x), 3), round(float(y), 3)], outline_um=[KI, KI], orient="R0",
                                   elaborated_path=f"u_bank.g_kve[{ke}].g_input_relay[{st}].u_relay"))
            hops.append(man(prev, C[("kve", ke)]))
        if ok: break
        del rects[mark[0]:], relays[mark[1]:], hops[mark[2]:]
        if ok is None: break
    if not ok: ifail.append(kb)
    KST[kb] = int(n)
xd["XIN"] = 0; census["XIN in"] = dict(links=64, worst_centre_um=round(max(L.values()), 1), kvi_stages_by_cluster=KST, soft_funnel_stages=FUN, unrouted=[str(f) for f in ifail])
val = sum(xd[o] << (4 * i) for i, o in enumerate(order)) | (FUN << 44); kst = sum(k << (4 * i) for i, k in enumerate(KST))
print("XD = 48'h%012x (XINS %d)  KST = 64'h%016x %s unrouted %s" % (val, FUN, kst, KST, ifail))
worst_hop = max(hops); over = sum(h > HOP for h in hops)
print("relays", len(relays), "kvi stages by cluster", KST, "worst relay hop centre um", round(worst_hop, 1), "hops over", HOP, ":", over, "of", len(hops))
wh = None
fixed = sum((c - a) * (d - b) for n, a, b, c, d in rects)
print("blocks", len(seats), "fixed area incl. band reserve mm2", round(fixed / 1e6, 3), "of", round(W * H / 1e6, 3), "=", f"{fixed / (W * H):.1%}")
out = dict(schema="opentallas.s81.kvleaf_t2_partb_seats.v1", lane="S81-KVLEAF-T2-ARCH-R2", outline_um=[W, H], frame="piece 1 (B) of the kv_leaf t2 A|B cut: slot frame x - 1468.8; slot 4682.88 wide, cut at x 1468.8",
           hop_um=HOP, xd="48'h%012x" % val, kst="64'h%016x" % kst, xd_fields=xd, census=census, hard_seats=seats, relay_seats=relays, exit_relay_seats=xrel, ft_corridors_x_um=FTC, ft_station_bands_um=ftst,
           ft_station_rank_y_um=[round(y + 6.48, 2) for y in FTY] + sorted({round(b[1] + 6.48, 2) for b in r4}), seam_landing_um=[0.0, round(Y2 + 289.44 + 12.96, 2), 60.48, round(YS - 4.32, 2)],
           kv_store_sram=[dict(index=i, elaborated_path=f"g_store[{i // 9}].g_word[{i % 9}].u_m", origin_um=[round(x, 3), round(y, 3)], outline_um=[31.992, 17.304]) for i, (x, y) in enumerate(sram)],
           note="v1 hand-drawn; distances are centre to centre (Manhattan); pair link abutted; input relay hop measured on seats; "
                "no placement / GRT probe yet; the 7 larger band SRAMs and the 23 band cores are part A (not seated here)")
json.dump(out, open(sys.argv[1] if len(sys.argv) > 1 else "partb_seats_v1.json", "w"), indent=1)
