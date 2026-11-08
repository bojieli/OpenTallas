#!/usr/bin/env python3
"""DIE-HEAD-84 hd_lep0N redesign model (geometry estimate, NOT placement / STA).
Fixed: vC outline, the 4 signed pair macros (positions/orientations of vC macro_place.tcl), die port pins (vC geom P rows).
Computes per data class: worst-bit Manhattan distance between fixed endpoints, register hops already on that leg,
hops needed at <= HOP um, added cycles; and the horizontal-track demand at every vertical cut of the mid band against
its capacity, for a range of hub (front end + RX state/merge) positions.  Output plan_model.json + plan.png."""
import json, math, sys
HOP = 340.0                      # target hop (r2r flag is 405)
DIE = (1762.56, 1226.88)
BAND = (509.76, 665.28)          # mid band between the lower and upper pair rows
PAIRS = {0: ((881.28, 17.28), 'MX'), 1: ((69.12, 665.28), 'R0'), 2: ((69.12, 17.28), 'MX'), 3: ((881.28, 665.28), 'MY')}
PW, PH = 777.6, 492.48
def kpins(t):                    # pair LEF: k_lo/k_li on S side, x 2..394
    (x0, y0), o = PAIRS[t]
    if o == 'MX': return (x0 + 2, x0 + 394, y0 + PH)
    if o == 'R0': return (x0 + 2, x0 + 394, y0)
    if o == 'MY': return (x0 + PW - 394, x0 + PW - 2, y0)
PORT = {'lepk_i0': (1762.46, 265.8, 511.0), 'lepk_o0': (1762.46, 10.2, 255.4), 'unit_i0': (1762.46, 800.1, 819.3),
        'ctrl_o0': (1762.46, 830.3, 849.4), 'lw_o': (1762.46, 1106.3, 1123.1)}
COLL0_PIN = ((480.07, 685.28), (702.11, 906.50), 1226.78)       # coll_i0 / coll_o0 on N
PP0_COLL = (881.28, 45.3, 507.8)                                  # pp0 (MX) W-side COLL pins: x, y span
# track capacity of a vertical cut through the band (horizontal layers M2 .036 / M4 .048 / M6 .064; SRAM OBS M1-M4)
PITCH = {'M2': .036, 'M4': .048, 'M6': .064}
USE = {'M2': .25, 'M4': .5, 'M6': .6}   # usable fraction (M2 shared with cell pins)
def cut_capacity(blocked_um):
    free = (BAND[1] - BAND[0]) - blocked_um
    c = free * (USE['M2'] / PITCH['M2'] + USE['M4'] / PITCH['M4'])
    c += (BAND[1] - BAND[0]) * USE['M6'] / PITCH['M6']
    return round(c)
def manh(a, b): return abs(a[0] - b[0]) + abs(a[1] - b[1])
def far(span_pts, p):           # worst point of a pin span to p
    return max(manh(q, p) for q in span_pts)
W = 553                         # H+1 lane word
LANES = range(4)
kc = {t: ((kpins(t)[0] + kpins(t)[1]) / 2, kpins(t)[2]) for t in LANES}
def lane_cluster(t):             # TX FIFO cluster: banks in the band beside the lane's K pins (proposal)
    x0, x1, y = kpins(t)
    return ((x0 + x1) / 2, BAND[0] + 25 if y < 600 else BAND[1] - 25)
def legs(hub):
    hx, hy = hub
    out = []
    pi = PORT['lepk_i0']; po = PORT['lepk_o0']
    ingress = [(pi[0], pi[1]), (pi[0], pi[2])]
    out.append(dict(cls='TX ro: lepk_i pins -> front end (hub)', bits=1104, d=far(ingress, hub), have=4,
                    note='ring, bin, rop (IN_PIPE), roq: placed FIRM along the leg instead of piled at the hub'))
    for t in LANES:
        lc = lane_cluster(t)
        out.append(dict(cls=f'TX lane{t}: front end (hub) -> lane{t} write (wdata)', bits=W + 20, d=manh(hub, lc), have=1,
                        note='per-lane KEPT ingress copy of hf/sq + push_lane/push_group bits'))
        x0, x1, y = kpins(t)
        out.append(dict(cls=f'TX lane{t}: od -> pair{t} k_lo pins', bits=W, d=max(manh(lc, (x0, y)), manh(lc, (x1, y))), have=1,
                        note='FIFO read side stays beside its own pair (vC put lane t in quarter t: wrong pair for lanes 0 and 2)'))
        out.append(dict(cls=f'RX lane{t}: pair{t} k_li pins -> RX landing (hub)', bits=W, d=max(manh((x0, y), hub), manh((x1, y), hub)), have=1,
                        note='pair release pop needs lanes 2k and 2k+1 together, so RX state is central; credit li_r returns the same way'))
    out.append(dict(cls='RX ri: merge rid (hub) -> lepk_o pins', bits=1104, d=far([(po[0], po[1]), (po[0], po[2])], hub), have=2,
                    note='rid -> bout ring -> pin'))
    out.append(dict(cls='MU mu_c: unit_i pins -> g_mtx (hub)', bits=34, d=far([(1762.46, 800.1), (1762.46, 819.3)], hub), have=3,
                    note='must keep the same added cycles as ro (stamp alignment)'))
    out.append(dict(cls='MU mu_rt: hub -> ctrl_o pins', bits=32, d=far([(1762.46, 830.3), (1762.46, 849.4)], hub), have=2,
                    note='must keep the same added cycles as ri (tag of the beat on ri)'))
    out.append(dict(cls='LAND ml_wd: merge (hub) -> u_land banks', bits=1104, d=0, have=1, note='land banks beside the hub'))
    out.append(dict(cls='LAND lw_o: u_land (hub) -> lw_o pins', bits=11, d=far([(1762.46, 1106.3), (1762.46, 1123.1)], hub), have=1,
                    note='11-bit notification'))
    ci, co, yN = COLL0_PIN
    p0 = [(PP0_COLL[0], PP0_COLL[1]), (PP0_COLL[0], PP0_COLL[2])]
    dci = max(manh((x, yN), p) for x in ci for p in p0)
    dco = max(manh((x, yN), p) for x in co for p in p0)
    out.append(dict(cls='COLL0 coll_i0: N pins -> pair0 W-side pins (seam x 881)', bits=514, d=dci, have=2, note='ring, bin'))
    out.append(dict(cls='COLL0 coll_o0: pair0 W-side pins -> N pins', bits=513, d=dco, have=2, note='bout ring'))
    for l in out:
        need = max(1, math.ceil(l['d'] / HOP)) if l['d'] else 1
        l['hops_needed'] = need; l['added_cycles'] = max(0, need - l['have']); l['d'] = round(l['d'], 1)
    return out
def cut_demand(hub, xcut):
    hx = hub[0]; d = 0
    if xcut > hx: d += 2 * 1104 + 34 + 32 + 11      # lepk_i, lepk_o (+unit/ctrl/lw) between hub and E face
    for t in LANES:
        lx = kc[t][0]
        if min(hx, lx) < xcut < max(hx, lx): d += (W + 20) + W + 1   # TX ingress + RX li (+credit)
    return d
def main(out_dir):
    blocked = 3 * 29.16                    # three SRAM rows across the band (vC rows y 518 / 561 / 604)
    cap = cut_capacity(blocked)
    cuts = [x for x in range(100, 1700, 50)]
    sweep = []
    for hx in range(500, 1700, 50):
        dem = {x: cut_demand((hx, 587.5), x) for x in cuts}
        xm = max(dem, key=dem.get)
        sweep.append(dict(hub_x=hx, worst_cut_x=xm, worst_demand=dem[xm], capacity=cap))
    best = min(sweep, key=lambda s: s['worst_demand'])
    hub = (best['hub_x'], 587.5)
    L = legs(hub)
    need_band = None
    per_um = (USE['M2'] / PITCH['M2'] + USE['M4'] / PITCH['M4'])
    m6 = USE['M6'] / PITCH['M6']
    # band height h with the same three SRAM rows that carries the best-hub demand
    for h in [x / 2 for x in range(300, 1200)]:
        c = (h - blocked) * per_um + h * m6
        if c >= best['worst_demand']: need_band = h; break
    res = dict(kind='GEOMETRY_MODEL_NOT_PLACE_NOT_STA', hop_um=HOP, band=BAND, band_height=round(BAND[1] - BAND[0], 2),
               cut_capacity_tracks=cap, usable_fraction=USE, hub_sweep=sweep, best_hub=best, legs=L,
               band_height_needed_um=need_band,
               added_cycles={l['cls']: l['added_cycles'] for l in L if l['added_cycles']})
    json.dump(res, open(out_dir + '/plan_model.json', 'w'), indent=1)
    draw(out_dir + '/plan.png', hub, L, sweep, cap)
    print(json.dumps(dict(best=best, capacity=cap, band_needed=need_band,
                          legs=[(l['cls'], l['d'], l['have'], l['hops_needed'], l['added_cycles']) for l in L]), indent=1))
def draw(path, hub, L, sweep, cap):
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(18, 7.5), gridspec_kw={'width_ratios': [1.6, 1]})
    ax.add_patch(Rectangle((0, 0), *DIE, fill=False, lw=1.5))
    for t, ((x0, y0), o) in PAIRS.items():
        ax.add_patch(Rectangle((x0, y0), PW, PH, color='0.85', hatch='//', ec='0.4'))
        ax.text(x0 + PW / 2, y0 + PH / 2, f'pair{t} ({o})\nlane {t}', ha='center', va='center', fontsize=10)
        k0, k1, ky = kpins(t)
        ax.plot([k0, k1], [ky, ky], color='red', lw=4)
        lc = lane_cluster(t)
        ax.plot(*lc, 's', color='tab:blue', ms=9)
        ax.annotate('', xy=lc, xytext=hub, arrowprops=dict(arrowstyle='->', color='tab:blue', lw=1.2))
    ax.axhspan(*BAND, color='khaki', alpha=.35)
    ax.plot(*hub, '*', color='k', ms=18)
    ax.text(hub[0], hub[1] + 25, 'hub: front end + RX state/merge + land', ha='center', fontsize=9)
    for n, (x, y0, y1) in PORT.items():
        ax.plot([x, x], [y0, y1], color='green', lw=5); ax.text(x - 10, (y0 + y1) / 2, n, ha='right', fontsize=8, color='green')
    ci, co, yN = COLL0_PIN
    ax.plot(ci, [yN, yN], color='purple', lw=5); ax.plot(co, [yN, yN], color='m', lw=5)
    ax.plot([PP0_COLL[0]] * 2, PP0_COLL[1:], color='purple', lw=5)
    ax.annotate('', xy=(PP0_COLL[0], 300), xytext=(600, yN), arrowprops=dict(arrowstyle='->', color='purple', lw=1.5))
    ax.text(890, 1000, 'coll_i0/o0 N pins -> pair0 W pins\n(seam 35 um wide)', color='purple', fontsize=8)
    ax.set_xlim(-60, 1830); ax.set_ylim(-20, 1260); ax.set_aspect('equal')
    ax.set_title('hd_lep0N plan (same outline): red = pair K pins, blue = TX lane FIFO beside its own pair')
    txt = '\n'.join(f"{l['cls'][:52]:52s} {l['d']:7.0f} um  +{l['added_cycles']}" for l in L if l['bits'] >= 500)
    ax.text(-50, -160, txt, fontsize=6.5, family='monospace', va='top')
    xs = [s['hub_x'] for s in sweep]; ys = [s['worst_demand'] for s in sweep]
    bx.plot(xs, ys, 'o-', label='worst vertical-cut demand (wires)')
    bx.axhline(cap, color='r', ls='--', label=f'usable capacity of the 155.5-um band ({cap})')
    bx.set_xlabel('hub x (um)'); bx.set_ylabel('horizontal wires through the band'); bx.legend(fontsize=8)
    bx.set_title('mid-band track demand vs hub position (lower bound: data buses only)')
    fig.tight_layout(); fig.subplots_adjust(bottom=.25); fig.savefig(path, dpi=110)
if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '.')
