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
W, H = float(os.environ.get('SEAT_W', '4700.16')), 1918.08
G = 4.32
snap = lambda v: round(v / G) * G
SZ = dict(kvec=(138.24, 138.24), kvpc=(211.68, 129.6), kvq=(259.2, 259.2), cnw=(181.44, 194.4), ikw=(181.44, 194.4),
          ikr=(198.72, 198.72), cpl=(172.8, 190.08), kvr=(140.4, 140.4), qnh=(114.48, 114.48), kvtc=(702.0, 25.92),
          kvi=(34.56, 34.56), sram=(31.992, 17.304))
MOD = dict(kvec="dsfd_su_t_kvec", kvpc="dsfd_su_t_kvpc", kvq="dsfd_su_t_kvq", cnw="dsfd_su_t_cnw", ikw="dsfd_su_t_ikw",
           ikr="dsfd_su_t_ikr", cpl="dsfd_sl_t_cpl", kvr="dsfd_su_t_kvr", qnh="dsfd_su_t_qnh", kvtc="dsfd_su_t_kvtc")
seats = []; rects = [("partA", 0, 0, 1460, 1245)]
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
kve_path = lambda ke: f"u_bank.g_kve[{ke}].g_rpc.u_kve" if ke >= 56 else f"u_bank.g_kve[{ke}].genblk1.g_npc.u_kve"
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
VCH = float(os.environ.get('SEAT_VCH', '95.04'))
XB = 1512.0
Y1 = 21.6; Y2 = Y1 + 289.44 + 82.08; YS = Y2 + 289.44 + 82.08; Y3 = YS + 216.0 + 82.08; Y4 = Y3 + 289.44 + 82.08; YT = 0
e1 = row([0, 1, 2, 3], XB, Y1); row([4, 5, 6, 7], XB, Y2); row([8, 9, 10, 11], XB, Y3)
e4 = row([12, 13, 14, 15], 1200.96, Y4, ik=True)
xm = (XB + e1) / 2
for u in range(4):
    C[("kvt", u)] = put("kvtc", u, xm - 702 - 8.64 + (u % 2) * (702 + 17.28), YS + 60.48 + (u // 2) * (25.92 + 43.2), f"u_bank.g_u[{u}].g_closed.u_kvt")
xl = xm - 702 - 8.64 - 60.48
for hh in range(4):
    C[("qnh", hh)] = put("qnh", hh, xl - (hh + 1) * (114.48 + GAP), YS + 51.84, f"u_bank.g_kvr.g_kvh[{hh}].g_closed.u_qnh")
xr = xm + 702 + 8.64 + 60.48
C[("kvr", 0)] = put("kvr", 0, xr, YS + 38.88, "u_bank.g_kvr.g_closed.u_kvr")
C[("ikr", 0)] = put("ikr", 0, xr + 140.4 + 4 * GAP, YS + 8.64, "u_bank.g_iks.g_closed.u_ik_reduce")
for l in range(8):
    C[("cpl", l)] = put("cpl", l, 388.8 + (l % 3) * (172.8 + GAP), 1270.08 + (l // 3) * (190.08 + GAP), f"g_cp.u_pool.g_lanec[{l}].u_l")
sram = []
for i in range(144):
    x, y = snap(21.6 + (i % 8) * (31.992 + 11.208)), snap(1270.08 + (i // 8) * (17.304 + 10.8))
    rects.append((f"sram{i}", x, y, x + 31.992, y + 17.304)); sram.append([x, y])
C[("store", 0)] = (21.6 + 4 * 43.2, 1270.08 + 9 * 28.1)
# ---- input relays: 3 + XIN stages an engine, on the straight line tap pair -> engine, nearest free 38.88 cell
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
    fam["XO exits"] += [man(C[(m, kb)], C[("store", 0)]) for m in ("kvq", "cnw")] + ([man(C[("ikw", kb)], C[("store", 0)])] if kb >= 12 else [])
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
# ---- input relays (kvi masters) on channel paths: tap row centre -> a vertical channel -> the horizontal channel on
# the spine side of the engine's row -> the engine.  The tap is bit-local (an engine's 256 bits leave over the whole
# 702-um tap), so ONE soft, bit-individual funnel stage (XINS) comes before the first compact relay.
CH = {0: Y1 + 289.44 + 41.04, 1: Y2 + 289.44 + 41.04, 2: Y3 - 41.04, 3: Y4 - 41.04}       # channel centre y by cluster row
xmid = XB + 2 * 755.9 + VCH / 2
VX = [XB - 23.76, xmid, e1 + 23.76]
def path(ke):
    kb = ke // 4; r = kb // 4; b = C[("kve", ke)]
    a = (xm, YS - 41.04 if r < 2 else YS + 216.0 + 41.04)      # the channel beside the spine on the row's side
    xv = min(VX, key=lambda v: abs(v - xm) + abs(v - b[0]))
    return [a, (xv, a[1]), (xv, CH[r]), (b[0], CH[r]), b]
plen = lambda p: sum(man(p[i], p[i + 1]) for i in range(len(p) - 1))
def at(p, s):
    for i in range(len(p) - 1):
        d = man(p[i], p[i + 1])
        if s <= d or i == len(p) - 2:
            f = 0 if d == 0 else min(1, s / d); return (p[i][0] + f * (p[i + 1][0] - p[i][0]), p[i][1] + f * (p[i + 1][1] - p[i][1]))
        s -= d
L = {ke: plen(path(ke)) for ke in range(64)}
FUN = 1                                                    # soft funnel stages
KST = [max(1, math.ceil(max(L[4 * kb + i] for i in range(4)) / float(os.environ.get("SEAT_STEP","360")) + 0.0) - 1 - FUN) for kb in range(16)]   # kvi stages by cluster
xd["XIN"] = 0; census["XIN in"] = dict(links=64, worst_path_um=round(max(L.values()), 1), kvi_stages_by_cluster=KST, soft_funnel_stages=FUN)
val = sum(xd[o] << (4 * i) for i, o in enumerate(order)) | (FUN << 44); kst = sum(k << (4 * i) for i, k in enumerate(KST))
print("XD = 48'h%012x (XINS %d)  KST = 64'h%016x %s" % (val, FUN, kst, KST))
relays = []; worst_hop = 0; over = 0; hops = []
for ke in sorted(range(64), key=lambda k: -L[k]):
    NST = KST[ke // 4]; p = path(ke); prev = at(p, L[ke] / (NST + 1 + FUN) * FUN)          # where the soft funnel stage hands over
    for st in range(NST):
        tx, ty = at(p, L[ke] * (st + 1 + FUN) / (NST + 1 + FUN)); tx -= 17.28; ty -= 17.28
        best = None
        for r in range(0, 40):
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    if max(abs(dx), abs(dy)) != r: continue
                    x, y = snap(tx + dx * 36.72), snap(ty + dy * 36.72)
                    if x < 0 or y < 0 or x + 34.56 > W or y + 34.56 > H or occ(x, y, 34.56, 34.56): continue
                    d = abs(x - tx) + abs(y - ty)
                    if best is None or d < best[0]: best = (d, x, y)
            if best: break
        assert best, ("no relay seat", ke, st)
        _, x, y = best; rects.append((f"kvi{ke}_{st}", x, y, x + 34.56, y + 34.56)); c = (x + 17.28, y + 17.28)
        hops.append(man(prev, c)); (man(prev, c) > HOP) and print('OVER', ke, st, [round(v) for v in prev], [round(v) for v in c], [round(tx), round(ty)], round(L[ke])); prev = c
        relays.append(dict(master="kvi", engine=ke, stage=st, origin_um=[round(x, 3), round(y, 3)], outline_um=[34.56, 34.56], orient="R0",
                           elaborated_path=f"u_bank.g_kve[{ke}].g_input_relay[{st}].u_relay"))
    hops.append(man(prev, C[("kve", ke)])); (hops[-1] > HOP) and print('OVERLAST', ke, [round(v) for v in prev], [round(v) for v in C[('kve', ke)]])
worst_hop = max(hops); over = sum(h > HOP for h in hops)
print("relays", len(relays), "kvi stages by cluster", KST, "worst relay hop centre um", round(worst_hop, 1), "hops over", HOP, ":", over, "of", len(hops))
wh = None
fixed = sum((c - a) * (d - b) for n, a, b, c, d in rects)
print("blocks", len(seats), "fixed area incl. band reserve mm2", round(fixed / 1e6, 3), "of", round(W * H / 1e6, 3), "=", f"{fixed / (W * H):.1%}")
out = dict(schema="opentallas.s81.kvleaf_t2_partb_seats.v1", lane="S81-KVLEAF-T2-ARCH-R2", outline_um=[W, H], part_a_reserve_um=[0, 0, 1460, 1245],
           hop_um=HOP, xd="48'h%012x" % val, kst="64'h%016x" % kst, xd_fields=xd, census=census, hard_seats=seats, relay_seats=relays,
           kv_store_sram=[dict(index=i, origin_um=[round(x, 3), round(y, 3)], outline_um=[31.992, 17.304]) for i, (x, y) in enumerate(sram)],
           note="v1 hand-drawn; distances are centre to centre (Manhattan); pair link abutted; input relay hop measured on seats; "
                "no placement / GRT probe yet; the 7 larger band SRAMs and the 23 band cores are part A (not seated here)")
json.dump(out, open(sys.argv[1] if len(sys.argv) > 1 else "partb_seats_v1.json", "w"), indent=1)
