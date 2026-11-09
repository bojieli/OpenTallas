#!/usr/bin/env python3
"""DIE-HEAD-84 hd_lep0N plan v2 (same outline, same pair macros, same pins): lane-correct TX banks, central hub,
declared leg stages.  Emits macro_place.tcl lines, the stage FIRM rects (landing_placement cland_groups entries),
the per-leg hop bounds before/after, the per-cut track model and plan_v2.png.  ESTIMATE, not placement."""
import json, math, sys
sys.path.insert(0, '/tmp/dh84lep')
import head_lep_vd_plan_model as P  # same directory
OUT = sys.argv[1] if len(sys.argv) > 1 else '/tmp/dh84lep'
HOP = 380.0                                # stage spacing target (r2r flag 405)
GRT_USE = 0.72                             # measured derate of the GRT deck (vC probe: 25-32 % reduction)
TXW, TXH = 169.368, 29.16                  # ot_sram_1r1w_512x128_m4_r0c0
RXW, RXH = 51.432, 20.808                  # ot_sram_1r1w_32x128_m1_r0c0
LDW, LDH = 91.8, 39.432                    # ot_sram_1r1w_128x256_m1_r0c0
ROWS = {1: 518.412, 2: 561.612, 3: 604.812}  # vC TX rows (43.2 pitch)
SLOT = lambda k: 69.228 + 181.44 * k
HUB = (1150.0, 585.0)
# slot plan: (row, k) -> what
TXS = {1: [(3, 0), (3, 1), (3, 2), (2, 2), (2, 3)],      # lane 1: K pins x 71-463 top
       2: [(1, 0), (1, 1), (1, 2), (2, 0), (2, 1)],      # lane 2: K pins x 71-463 bottom
       0: [(1, 3), (1, 4), (1, 5), (2, 4), (2, 5)],      # lane 0: K pins x 883-1275 bottom
       3: [(3, 7), (3, 8), (2, 8), (1, 8), (1, 7)]}      # lane 3: K pins x 1265-1657 top
RXSLOTS = [(3, 5), (3, 6)]                               # 6 RX banks a slot (3 x 2 sub-rows), at the hub
RXTOP = (69.228 + 181.44 * 7, 604.812 + 32.4, 3)         # + 3 RX banks on a row above lane 3's R3 banks (top margin)
RXE = (69.228 + 0.144 * 11325, 518.412, 5)               # + 5 RX banks stacked in the E strip at band level (21.6 pitch)
LDSLOTS = [(3, 3, 1), (3, 4, 1), (1, 6, 1), (2, 6, 1), (2, 7, 1)]              # (row, k, n land banks), at the hub
TXI = {0: 1, 1: 2, 2: 2, 3: 1}; KRX = {0: 0, 1: 2, 2: 2, 3: 1}; PIN, POUT, PLW = 2, 3, 3
def macros():
    m = []
    for t, sl in TXS.items():
        for b, (r, k) in enumerate(sl):
            m.append((f'u_core.u.u_lep.u.g_tx\\[{t}\\].g_safe_write.u_m.g_bank\\[{b}\\].u_m', SLOT(k), ROWS[r], TXW, TXH, f'tx{t}'))
    rx = []
    for (r, k) in RXSLOTS:
        for sub in range(2):
            for c in range(3):
                rx.append((SLOT(k) + c * 59.04, ROWS[r] + sub * 21.6))
    for c in range(RXTOP[2]):
        rx.append((RXTOP[0] + c * 59.04, RXTOP[1]))
    for c in range(RXE[2]):
        rx.append((RXE[0], RXE[1] + c * 21.6))
    for t in range(4):
        for b in range(5):
            x, y = rx[5 * t + b]
            m.append((f'u_core.u.u_lep.u.g_rx\\[{t}\\].g_sa.g_true_sram.u_rx_mem.g_bank\\[{b}\\].u_m', x, y, RXW, RXH, f'rx{t}'))
    i = 0
    for (r, k, n) in LDSLOTS:
        for c in range(n):
            m.append((f'u_core.u.u_land.g_sram.g_t\\[{i}\\].g_128.u_m', SLOT(k) + c * 93.96, ROWS[r], LDW, LDH, 'land')); i += 1
    return m
def centre(ms, tag):
    s = [(x + w / 2, y + h / 2) for (_, x, y, w, h, g) in ms if g == tag]
    return (sum(a for a, _ in s) / len(s), sum(b for _, b in s) / len(s))
def far_from(ms, tag, p):
    return max(max(abs(x - p[0]), abs(x + w - p[0])) + max(abs(y - p[1]), abs(y + h - p[1])) for (_, x, y, w, h, g) in ms if g == tag)
def legs(ms):
    L = []
    pi, po = P.PORT['lepk_i0'], P.PORT['lepk_o0']
    def add(cls, bits, d, have, added, note=''):
        need = max(1, math.ceil(d / HOP)); L.append(dict(cls=cls, bits=bits, d=round(d, 1), hops_have_after=have + added,
            added_cycles=added, hop_um=round(d / (have + added), 1), ok=d / (have + added) <= 405, note=note))
    add('TX ro: lepk_i pins -> frame (hub)', 1104, P.far([(pi[0], pi[1]), (pi[0], pi[2])], HUB), 1, PIN, 'bin -> PIN stages -> rop')
    add('MU mu_c: unit_i pins -> g_mtx (hub)', 34, P.far([(1762.46, 800.1), (1762.46, 819.3)], HUB), 1, PIN, 'same PIN as ro')
    for t in range(4):
        add(f'TX lane{t}: frame (hub) -> lane{t} FIFO write', 573, far_from(ms, f'tx{t}', HUB), 1, TXI[t], 'TXI stages')
        x0, x1, y = P.kpins(t); c = centre(ms, f'tx{t}')
        add(f'TX lane{t}: FIFO read -> pair{t} k_lo pins', 553, max(P.manh(c, (x0, y)), P.manh(c, (x1, y))), 2, 0, 'q -> odr (TXRP) -> od -> pin')
        add(f'RX lane{t}: pair{t} k_li pins -> RX FIFO (hub)', 553, max(P.manh((x0, y), HUB), P.manh((x1, y), HUB)), 1, KRX[t], 'KRX stages; li_r back the same')
    add('RX ri: merge (hub) -> lepk_o pins', 1104, P.far([(po[0], po[1]), (po[0], po[2])], HUB), 1, POUT, 'rid -> POUT -> bout')
    add('MU mu_rt: hub -> ctrl_o pins', 32, P.far([(1762.46, 830.3), (1762.46, 849.4)], HUB), 1, POUT, 'same POUT as ri')
    lc = centre(ms, 'land')
    add('LAND ml_wd: merge (hub) -> u_land SRAM', 1104, far_from(ms, 'land', HUB), 2, 0, 'merge reg -> land pin flop wdq -> SRAM pin')
    add('LAND lw_o: lw_r -> lw_o pins', 11, P.far([(1762.46, 1106.3), (1762.46, 1123.1)], lc), 1, PLW, 'PLW stages')
    ci, co, yN = P.COLL0_PIN
    p0 = [(P.PP0_COLL[0], P.PP0_COLL[1]), (P.PP0_COLL[0], P.PP0_COLL[2])]
    add('COLL0 coll_i0: N pins -> pair0 W pins (PLAN EVENT, not adopted)', 514, max(P.manh((x, yN), p) for x in ci for p in p0), 2, 0)
    add('COLL0 coll_o0: pair0 W pins -> N pins (PLAN EVENT, not adopted)', 513, max(P.manh((x, yN), p) for x in co for p in p0), 2, 0)
    return L
GAP_HI = 597.8; GAP_LO = 554.6; TOP_M = 650.5      # stage window centre y: gap R2/R3, gap R1/R2, top margin (+1 um: clear of land g_t[1], DIE-HEAD-86)
def along(pts, f):
    """point at arclength fraction f of the Manhattan polyline pts"""
    seg = [(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    tot = sum(abs(b[0] - a[0]) + abs(b[1] - a[1]) for a, b in seg); want = tot * f
    for a, b in seg:
        l = abs(b[0] - a[0]) + abs(b[1] - a[1])
        if want <= l and l > 0:
            g = want / l; return (a[0] + (b[0] - a[0]) * g, a[1] + (b[1] - a[1]) * g)
        want -= l
    return pts[-1]
def stage_rects():
    """stage j of a leg at arclength (j+1)/(N+1) of its routed path, in a free channel (gap between bank rows / top
    margin / E strip); window 44 x 12 um, 90 x 12 for the 1.1k-bit port legs, then size_from_demand() widens each."""
    R = []
    ms = macros()
    def leg(prefix_fmt, n, pts, ych, tag, w=44, extra=()):
        for j in range(n):
            x, y = along(pts, (j + 1) / (n + 1))
            if 517 < y < 662 and x < 1660: y = ych                       # in the band: the leg's channel
            elif x >= 1660: x = 1725.0                                    # E strip column
            r = (x - w / 2, y - 6, x + w / 2, y + 6)
            R.append((prefix_fmt.format(j=j), r, f'{tag}_s{j}'))
            for e in extra: R.append((e.format(j=j), r, f'{tag}_s{j}'))
    E = 1725.0
    leg(r'u_core\.u\.g_pin\.g_s\\\[{j}\\\]', PIN, [(E, 388), (E, GAP_HI), (HUB[0], GAP_HI)], GAP_HI, 'pin', 90)
    leg(r'u_core\.u\.g_pout\.g_s\\\[{j}\\\]', POUT, [(HUB[0], GAP_LO), (E, GAP_LO), (E, 140)], GAP_LO, 'pout', 90)
    lc = centre(ms, 'land')
    leg(r'u_core\.u\.g_plw\.g_s\\\[{j}\\\]', PLW, [(lc[0], GAP_HI), (E, GAP_HI), (E, 1114)], GAP_HI, 'plw', 20)
    for t in range(4):
        c = centre(ms, f'tx{t}')
        leg(r'u_core\.u\.u_lep\.u\.g_tx\\\[%d\\\]\.g_txi\.g_s\\\[{j}\\\]' % t, TXI[t], [HUB, (c[0], HUB[1])], GAP_HI, f'txi{t}')
        x0, x1, y = P.kpins(t)
        kx = (x0 + x1) / 2
        ych = TOP_M if (y > 600 and t == 1) else GAP_LO
        leg(r'u_core\.u\.g_kl\\\[%d\\\]\.g_rxf\.g_s\\\[{j}\\\]' % t, KRX[t], [(kx, ych), (HUB[0], ych)], ych, f'krx{t}',
            extra=(r'u_core\.u\.g_kl\\\[%d\\\]\.g_rxr\.g_s\\\[{j}\\\]' % t,))
    # hand-placed E-strip windows (clear of the face ring bands lepk_i0 y 265-511 / coll_i3 645-760 / lepf / unit 769-820)
    fix = {'pin_s1': (1440.0, 591.8, 1530.0, 603.8), 'plw_s0': (1252.0, 548.6, 1280.0, 560.6), 'txi3_s0': (1272.0, 591.8, 1316.0, 603.8),
           'pin_s0': (1693.0, 627.5, 1757.0, 644.5), 'pout_s2': (1661.0, 225.0, 1671.5, 365.0), 'plw_s2': (1690.0, 856.0, 1740.0, 868.0)}
    R = [(p, fix.get(t, r), t) for (p, r, t) in R]
    return size_from_demand(R)
# DIE-HEAD-86 11-08: the 44 x 12 windows were sized for flops only ("575 flops at 0.4"), but landing_placement reserves
# ceil(w/0.4) sites for EVERY cell of the stage group (flops + the TXI kept-leaf logic).  Measured on the vE kit
# (3_2_place_iop.odb, tools/s81_head/head_lep_stage_resize.py): one TXI stage = 1163 cells = 1845 um of row, but a
# 44 x 12 window holds ~1600 um, so vE PLACE died "OT_CLAND no legal ... row/site in reserved band (stage:txi0_s0)".
# Every window is now widened about its centre until it holds DEMAND_MARGIN x its reserve row length at
# ROWS_PER_UM usable rows per um of width (36: 12-um windows between macro rows, edge rows cut), then windows that
# share a channel are pushed apart east (1 um gap).  Measured reserve row length per stage (um):
STAGE_DEMAND_UM = {'txi': 1845.0, 'krx': 1547.0, 'pin': 3168.0, 'pout': 3132.0, 'plw': 43.0}
DEMAND_MARGIN, ROWS_PER_UM = 1.25, 36.0
def size_from_demand(R):
    win = {}
    for (p, r, t) in R:
        if t in win: continue
        x0, y0, x1, y1 = r
        if (y1 - y0) > (x1 - x0):                      # vertical E-strip column: keep (pout_s2 holds 1.7x)
            win[t] = [x0, y0, x1, y1]; continue
        need = STAGE_DEMAND_UM[t.rsplit('_s', 1)[0].rstrip('0123456789')] * DEMAND_MARGIN / ROWS_PER_UM
        w = max(x1 - x0, 2.0 * math.ceil(need / 2.0)); cx = (x0 + x1) / 2
        win[t] = [cx - w / 2, y0, cx + w / 2, y1]
    for _ in range(20):
        moved = False
        items = sorted(win.items(), key=lambda kv: (round(kv[1][1], 1), kv[1][0]))
        for (ta, ra), (tb, rb) in zip(items, items[1:]):
            if abs(ra[1] - rb[1]) < 0.5 and rb[0] < ra[2] + 1.0:
                d = ra[2] + 1.0 - rb[0]; rb[0] += d; rb[2] += d; moved = True
        if not moved: break
    return [(p, tuple(win[t]), t) for (p, r, t) in R]
def cut_model(ms):
    cuts = list(range(100, 1700, 25)); out = []
    for xc in cuts:
        blocked = 0.0
        for (_, x, y, w, h, g) in ms:
            if x <= xc <= x + w: blocked += h
        blocked = min(blocked, P.BAND[1] - P.BAND[0])
        hgt = P.BAND[1] - P.BAND[0]
        cap = (hgt - blocked) * (GRT_USE / 0.039 + GRT_USE / 0.048) + hgt * GRT_USE / 0.064
        d = 0
        if xc > HUB[0]: d += 2 * 1104 + 34 + 32 + 11
        for t in range(4):
            cx = centre(ms, f'tx{t}')[0]; kx = sum(P.kpins(t)[:2]) / 2
            if min(HUB[0], cx) < xc < max(HUB[0], cx): d += 573
            if min(HUB[0], kx) < xc < max(HUB[0], kx): d += 553 + 2
        out.append(dict(x=xc, demand=d, capacity=round(cap), blocked_um=round(blocked, 1)))
    return out
def main():
    ms = macros(); L = legs(ms); R = stage_rects(); C = cut_model(ms)
    with open(OUT + '/macro_place_v2.tcl', 'w') as f:
        for k in range(4):
            (x, y), o = P.PAIRS[k]
            f.write(f'place_macro -macro_name {{u_core.u.g_pp\\[{k}\\].u_pair}} -location {{{x:.4f} {y:.4f}}} -orientation {o} -exact\n')
        for (n, x, y, w, h, g) in ms:
            f.write(f'place_macro -macro_name {{{n}}} -location {{{x:.4f} {y:.4f}}} -orientation R0 -exact\n')
    with open(OUT + '/stage_groups_v2.tcl', 'w') as f:
        for (p, r, tag) in R:
            f.write('  {{%s} {%.5f %.5f %.5f %.5f} stage:%s}\n' % (p, *r, tag))
    worst = min(C, key=lambda c: c['capacity'] - c['demand'])
    res = dict(kind='PLAN_V2_ESTIMATE_NOT_PLACE', hub=HUB, hop_um=HOP, grt_use=GRT_USE,
               declared_cycles=dict(TXI=TXI, KRX=KRX, PIN=PIN, POUT=POUT, PLW=PLW), legs=L, cuts=C, worst_cut=worst,
               n_stage_rects=len(R))
    json.dump(res, open(OUT + '/plan_v2.json', 'w'), indent=1)
    draw(ms, L, R, C)
    for l in L: print('%-62s %6.0f um  hops %d  hop %6.1f  +%d %s' % (l['cls'], l['d'], l['hops_have_after'], l['hop_um'], l['added_cycles'], 'OK' if l['ok'] else 'OVER'))
    print('worst cut', worst)
def draw(ms, L, R, C):
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig, (ax, bx) = plt.subplots(2, 1, figsize=(16, 15), gridspec_kw={'height_ratios': [2.2, 1]})
    ax.add_patch(Rectangle((0, 0), *P.DIE, fill=False, lw=1.5))
    col = {'tx0': 'tab:red', 'tx1': 'tab:blue', 'tx2': 'tab:green', 'tx3': 'tab:orange', 'land': 'tab:purple',
           'rx0': 'salmon', 'rx1': 'lightblue', 'rx2': 'lightgreen', 'rx3': 'moccasin'}
    for t, ((x0, y0), o) in P.PAIRS.items():
        ax.add_patch(Rectangle((x0, y0), P.PW, P.PH, color='0.88', ec='0.5'))
        ax.text(x0 + P.PW / 2, y0 + P.PH / 2, f'pair{t} ({o}) = lane {t}', ha='center', va='center', fontsize=11)
        k0, k1, ky = P.kpins(t); ax.plot([k0, k1], [ky, ky], color=col[f'tx{t}'], lw=5)
    for (n, x, y, w, h, g) in ms:
        ax.add_patch(Rectangle((x, y), w, h, color=col[g], alpha=.8))
    for (p, (a, b, c, d), tag) in R:
        ax.add_patch(Rectangle((a, b), c - a, d - b, fill=False, ec='k', lw=.8))
    ax.plot(*HUB, '*', color='k', ms=16)
    for n, (x, y0, y1) in P.PORT.items():
        ax.plot([x, x], [y0, y1], color='green', lw=5); ax.text(x - 8, (y0 + y1) / 2, n, ha='right', fontsize=8, color='green')
    ci, co, yN = P.COLL0_PIN
    ax.plot(ci, [yN, yN], color='purple', lw=5); ax.plot(co, [yN, yN], color='m', lw=5)
    ax.set_xlim(-30, 1800); ax.set_ylim(440, 720); ax.set_aspect('equal')
    ax.set_title('hd_lep0N plan v2 band (y 440-720): TX banks by lane colour beside their own pair K pins (bars), RX (light) + land '
                 '(purple) at the hub (star); black boxes = FIRM stage windows', fontsize=10)
    xs = [c['x'] for c in C]
    bx.plot(xs, [c['demand'] for c in C], 'o-', label='data-bus wires crossing the cut (lower bound)')
    bx.plot(xs, [c['capacity'] for c in C], 's--', color='r', label=f'horizontal capacity M2/M4/M6 at {GRT_USE:.0%} minus bank rows')
    bx.set_xlabel('vertical cut x (um)'); bx.set_ylabel('wires'); bx.legend(fontsize=9)
    bx.set_title('mid-band cut demand vs capacity (estimate)')
    fig.tight_layout(); fig.savefig(OUT + '/plan_v2.png', dpi=100)
if __name__ == '__main__':
    main()
