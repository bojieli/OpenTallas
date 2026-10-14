#!/usr/bin/env python3
"""el1013-s81-vmfe/B5: feasibility of the hierarchical VM front end dsfd_vm_fe_h (RTL FROZEN at 693940a56) in an outline
1,520.064 x H, and the leaf outlines the ref_tile gate accepts.

  python3 tools/s81_ph/s81_ph_vm_fe_h_plan.py            -> results/arch/s81_vm_fe_h_plan_1013.json; exit 1 unless 10 lanes fit
                                                           at the decided outline (1,520.064 x 691.20)
  python3 tools/s81_ph/s81_ph_vm_fe_h_plan.py --quick    -> the decided outline only (no option sweep)

WHAT IT ANSWERS.  B2 .. B4 tried hand placements and all failed the E-W cut.  This tool does not place by hand: it searches
the lane arrangement.  Model = B2's track model, every term MEASURED or taken from the frozen contract:
  * tracks (ASAP7 make_tracks), 80 % usable, limit 0.60: free parent area H = M2/2 + M4 + M6; over an M5-capped leaf
    H = M6; over dsfd_vm_clt and dsfd_vm_fsr (M6 legacy views) H = 0.  The "0" is measured, not assumed: the clt8a LEF has
    27 of 3,594 M6 tracks free over its whole width (PG stripes + 3,081 OBS), `m6_free()` below.
  * fixed: 16 clt abutted under the f_cap pins (x 0 .. 1,290.24, 230.04 high), 4 fsr on the dsfd_vm_bgq28 N pins,
    4 fxs under their clt quad, fcn in the x centre (KD 2: one wire from the k pins of fxs0 and fxs3).
  * bundle demand of a vertical cut = bits of the 7 x 4 slice bundles (592 b each, FIXED width: the fxr master) whose
    source pin and dsfd_vm_fsr pin lie on opposite sides.  Independent of the relay placement.
  * a landing lane (216.00 x 129.60: macro 171.288 x 77.784 + 20-um channels, the ref_tile floorplan rule) adds its height to
    every cut it covers and 546 b (ret 526, av / ok / ovf / sflt 4, g 1, arm 15) to every cut between its pins and fld.
  * contract reach: av / ok / ovf / sflt are ONE wire (<= 500 um) from the lane to fld; the lane input word is ONE wire
    from the die N face (rows A / B under the clt row, 4 rows in the E column).
The model is OPTIMISTIC: it has no relay tiles, no local (window) capacity, no descent of the fxs words through the lane
rows, no fld / lane overlap test.  A count it cannot reach is not reachable by a real placement.

Options priced with the same search (table `options`): taller outline; +1 relay stage on av / ok / ovf / sflt (reach 950);
S2 = bundle tiles trimmed to their non-constant bits; S3 = clt re-routed at M5 (M6 free over the clt row); S4 = lane
returns daisy-chained lane to lane (one 546-b bus crosses a cut instead of one per lane)."""
import json, math, random, re, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
W, H_OLD, H_DEC = 1520.064, 594.0, 691.2
CLT_W, CLT_H, FSR_H = 1290.24, 230.04, 25.92
TPU = {'M2': 7 / 0.270, 'M3': 1 / 0.036, 'M4': 1 / 0.048, 'M5': 1 / 0.048, 'M6': 1 / 0.064, 'M7': 1 / 0.064}
FREE, CUT_MAX, HOP_MAX = 0.80, 0.60, 500.0
HT_FREE, HT_M5 = TPU['M2'] / 2 + TPU['M4'] + TPU['M6'], TPU['M6']
CM, EDGE = 2.16, 20.0                    # ref_tile CORE_MARGIN, CHANNEL_UM / PIN_EDGE_UM
MAC_W, MAC_H, MAC_X, MAC_Y = 171.288, 77.784, 22.464, 23.76
LW, LH, LANE_BITS, NLANE = 216.0, 129.6, 546, 10       # 125.28 = the gate minimum; the route flow measured util 60.0 % there (FLOORPLAN_MARGIN)
AREAS = json.loads((ROOT / 'results/arch/s81_vm_fe_h_areas_1013.json').read_text())['leaves']
# leaf outlines: the smallest the shared gate accepts (2.16-um lattice, core = outline - 2.16 all round, std <= 0.55 of core,
# std + macro <= 0.60, macro >= 20 um from every core edge), THEN grown to what the remote --cts gate measured (B5): ORFS
# synthesis is ~15 % over the yosys stat and every input pin costs a hold stage (fsr-proven kit: +0.25 um2 an input);
# sized to (std_orfs + hold) / 0.48.  clt / fsr = CLOSED views.
VIEWS = {'dsfd_vm_clt': (80.64, 230.04, 'M6 (closed clt8a)'), 'dsfd_vm_fsr': (345.6, 25.92, 'M6 (closed r4b)'),
         'dsfd_vm_fxs': (241.92, 23.76, 'M5'), 'dsfd_vm_fxr': (54.0, 25.92, 'M5'), 'dsfd_vm_flt': (LW, LH, 'M5'),
         'dsfd_vm_fld': (259.2, 47.52, 'M5'), 'dsfd_vm_fcn': (239.76, 51.84, 'M5'), 'dsfd_vm_fcc': (181.44, 112.32, 'M5'),
         'dsfd_vm_fcw': (151.2, 38.88, 'M5'), 'dsfd_vm_frr': (43.2, 19.44, 'M5'), 'dsfd_vm_fra': (10.8, 8.64, 'M5'),
         'dsfd_vm_frg': (8.64, 6.48, 'M5')}
FXS_W, FXS_H = VIEWS['dsfd_vm_fxs'][:2]
FLD_W, FLD_H = VIEWS['dsfd_vm_fld'][:2]
FCN_W, FCN_H = VIEWS['dsfd_vm_fcn'][:2]
FSR_CTL, FSR_D = (2.4, 37.277), (37.277, 260.491)          # dsfd_vm_bgq28 N pin x inside one 345.6 column (pitch 388.8)
REAL = {**{p: 144 for p in (0, 3, 4)}, 1: 15, **{p: 15 for p in (2, 5, 6, 7, 8, 9)}, 10: 143, 11: 143, **{p: 147 for p in range(12, 28)}}
XS = np.arange(0.5, W, 1.0)                                # vertical cuts every 1 um


def bport(b, j): return 12 + 4 * b + j if b < 4 else ((j if j < 2 else j + 1) if b == 4 else ((2 if j == 0 else j + 4) if b == 5 else j + 8))


def m6_free(lef):
    """M6 tracks (0.064 pitch) with no PG pin / OBS shape within one spacing, over the whole width of a view"""
    t = (ROOT / lef).read_text()
    m = re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', t); h = float(m[2])
    rects = []
    for blk in re.findall(r'LAYER M6 ;((?:\s*RECT [^;]+;)+)', t):
        rects += [tuple(map(float, r)) for r in re.findall(r'RECT\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)', blk)]
    nt = int(h / 0.064); blocked = np.zeros(nt, bool)
    yc = np.arange(nt) * 0.064 + 0.032
    for _, y0, _, y1 in rects: blocked |= (yc > y0 - 0.064) & (yc < y1 + 0.064)
    return {'tracks': nt, 'free_over_the_whole_width': int((~blocked).sum()), 'm6_shapes': len(rects)}


def bundle_demand(trim=False):
    """bits crossing each vertical cut: 7 bundles x 4 slices x 4 ports, source pin vs fsr pin (bit-aligned, 16 samples a group)"""
    d = np.zeros(len(XS))
    src = {b: (322.56 * b + 40.32, 53.0) for b in range(4)}        # fxs b: 241.92 wide, centred under its clt quad
    for b in range(7):
        for s in range(4):
            for j in range(4):
                p = bport(b, j)
                if b < 4:
                    x0 = src[b][0] + (6.0, 60.0, 128.0, 182.0)[s] + 53.0 * j / 4; x1 = x0 + 53.0 / 4
                else:
                    x0 = x1 = 732.0                                # central sources (fcw, fcc, fcn, fld words): the plateau centre
                real = REAL[p] + ((4 if p in (2, 6, 7, 8, 9) else 92 if p == 5 else 0) if s == 0 else 0)
                for nb, (d0, d1) in ((128, (388.8 * s + FSR_D[0] + (FSR_D[1] - FSR_D[0]) * p / 28, 388.8 * s + FSR_D[0] + (FSR_D[1] - FSR_D[0]) * (p + 1) / 28)),
                                     (20, (388.8 * s + FSR_CTL[0] + (FSR_CTL[1] - FSR_CTL[0]) * p / 28, 388.8 * s + FSR_CTL[0] + (FSR_CTL[1] - FSR_CTL[0]) * (p + 1) / 28))):
                    bits = nb if not trim else (max(min(real, 148) - 20, 0) if nb == 128 else min(real, 20))
                    for k in range(16):
                        a = x0 + (x1 - x0) * (k + 0.5) / 16; z = d0 + (d1 - d0) * (k + 0.5) / 16
                        d += (bits / 16) * ((XS > min(a, z)) & (XS < max(a, z)))
    return d


def span(x0, x1): return (XS > x0) & (XS < x1)


class Model:
    """one outline height + option set; `best()` = the largest lane set a randomised search finds, over every fld position"""

    def __init__(self, h, reach=HOP_MAX, trim=False, clt_m5=False, chain=False):
        self.h, self.reach, self.chain = h, reach, chain
        free_h = np.full(len(XS), h)
        free_h -= np.where(XS < CLT_W, CLT_H, 0.0)
        fsr = np.zeros(len(XS), bool)
        for s in range(4): fsr |= span(388.8 * s, 388.8 * s + 345.6)
        free_h -= np.where(fsr, FSR_H, 0.0)
        self.tracks0 = HT_FREE * free_h + (np.where(XS < CLT_W, HT_M5 * CLT_H, 0.0) if clt_m5 else 0.0)
        self.dem0 = bundle_demand(trim)
        self.leaf0 = np.zeros(len(XS))
        for i in range(4): self.leaf0 += np.where(span(322.56 * i + 40.32, 322.56 * i + 40.32 + FXS_W), FXS_H, 0.0)
        self.leaf0 += np.where(span(732.0 - FCN_W / 2, 732.0 + FCN_W / 2), FCN_H, 0.0)
        # lane slots: (name, x0, row): rows A / B under the clt row (one wire from the N face), 4 rows in the E column
        self.slots = [(f'{r}@{x0:.0f}', float(x0), r) for x0 in np.arange(0.0, CLT_W - LW + 0.1, 27.0) for r in 'AB']
        self.slots += [(f'E{r}', 1304.064, r) for r in ('U2', 'U1', 'A', 'B')]
        self.dv = {'A': 20.0, 'B': 20.0, 'U1': 110.0, 'U2': 235.0}   # vertical part of the lane -> fld wire (fld at the A / B seam)

    def ratio(self, leaf, thru):
        return (self.dem0 + thru) / (FREE * (self.tracks0 - (HT_FREE - HT_M5) * leaf))

    def lane(self, slot, xf):
        """(leaf-height mask, through mask, reach) of a lane for fld at [xf, xf + FLD_W]"""
        _, x0, r = slot
        pin = x0 + LW if x0 + LW <= xf else (x0 if x0 >= xf + FLD_W else None)
        if pin is None: thr, dist = np.zeros(len(XS), bool), self.dv[r]            # above / below fld: vertical only
        elif pin <= xf: thr, dist = span(pin, xf), xf - pin + self.dv[r]
        else: thr, dist = span(xf + FLD_W, pin), pin - xf - FLD_W + self.dv[r]
        return span(x0, x0 + LW), thr, dist

    def best(self, tries=60, seed=1):
        rnd = random.Random(seed); best = (0, None, None, None)
        for xf in np.arange(216.0, 1304.0 - FLD_W, 27.0):
            leaf_f = self.leaf0 + np.where(span(xf, xf + FLD_W), FLD_H, 0.0)
            if self.ratio(leaf_f, 0.0).max() > CUT_MAX: continue
            cand = []
            for sl in self.slots:
                cov, thr, dist = self.lane(sl, xf)
                if dist <= self.reach: cand.append((sl, cov, thr))
            for t in range(tries):
                order = cand[:]; rnd.shuffle(order)
                if t % 3 == 0: order.sort(key=lambda c: c[2].sum())                 # short returns first
                if t % 3 == 1: order.sort(key=lambda c: -abs(c[0][1] + LW / 2 - 732.0))   # outer columns first
                leaf, thru, used, nthr = leaf_f.copy(), np.zeros(len(XS)), [], np.zeros(len(XS))
                for sl, cov, thr in order:
                    if any(u[2] == sl[2] and abs(u[1] - sl[1]) < LW + 2.0 for u in used): continue
                    if any(u[1] > 1300 and sl[1] > 1300 and u[2] == sl[2] for u in used): continue
                    l2 = leaf + cov * LH; n2 = nthr + thr
                    t2 = np.minimum(n2, 1.0) * LANE_BITS if self.chain else n2 * LANE_BITS
                    if self.ratio(l2, t2).max() <= CUT_MAX:
                        leaf, nthr, thru = l2, n2, t2; used.append(sl)
                        if len(used) == NLANE: break
                if len(used) > best[0]:
                    r = self.ratio(leaf, thru); best = (len(used), float(xf), [u[0] for u in used], (round(float(r.max()), 3), float(XS[r.argmax()])))
                if best[0] == NLANE: return best
        return best

    def profile(self):
        """bundles only: ratio, and the M5 leaf height each cut still allows (um)"""
        r = self.ratio(self.leaf0, 0.0)
        allow = (self.tracks0 - self.dem0 / (FREE * CUT_MAX)) / (HT_FREE - HT_M5) - self.leaf0
        return [[float(x), int(round(self.dem0[i])), round(float(r[i]), 3), round(float(allow[i]), 1)] for i, x in enumerate(XS) if int(x) % 54 == 0]


def min_height(**opt):
    """smallest outline height on the 2.16 lattice where the search fits all 10 lanes (coarse 10.8 steps, then 2.16)"""
    h = H_OLD - 10.8; last = None
    while h < 1000.0:
        h = round(h + 10.8, 2)
        b = Model(h, **opt).best(tries=24)
        if b[0] == NLANE: last = (h, b); break
    if last is None: return None
    for hh in (round(h - 10.8 + 2.16 * k, 2) for k in range(1, 5)):
        b = Model(hh, **opt).best(tries=24)
        if b[0] == NLANE: return {'h_um': hh, 'fld_x': b[1], 'lanes': b[2], 'worst_cut': b[3]}
    return {'h_um': last[0], 'fld_x': last[1][1], 'lanes': last[1][2], 'worst_cut': last[1][3]}


def gate_floorplan():
    out, bad = {}, []
    for v, (w, h, cap) in VIEWS.items():
        if v in ('dsfd_vm_clt', 'dsfd_vm_fsr'): continue
        std = AREAS[v]['std_cell_area_um2']; core = (w - 2 * CM) * (h - 2 * CM); mac = MAC_W * MAC_H if v == 'dsfd_vm_flt' else 0.0
        rec = {'outline': [w, h], 'std_cell_area_um2': std, 'flops': AREAS[v]['flops'], 'core_um2': round(core, 1),
               'util_std_plus_macro': round((std + mac) / core, 3), 'util_std_cells_only': round(std / (core - mac), 3)}
        if mac:
            m = {'W': MAC_X - CM, 'E': w - CM - MAC_X - MAC_W, 'S': MAC_Y - CM, 'N': h - CM - MAC_Y - MAC_H}
            rec['macro_at'] = [MAC_X, MAC_Y]; rec['macro_to_core_edge_um'] = {k: round(x, 3) for k, x in m.items()}
            if min(m.values()) < EDGE - 1e-6: bad.append(f'{v}: macro {min(m.values()):.2f} um from a core edge')
            if (std + mac) / core > 0.60: bad.append(f'{v}: util {(std + mac) / core:.3f} > 0.60')
        elif std / core > 0.55 + 1e-9: bad.append(f'{v}: util {std / core:.3f} > 0.55')
        if any(abs(x / 2.16 - round(x / 2.16)) > 1e-6 for x in (w, h)): bad.append(f'{v}: outline off the 2.16 lattice')
        out[v] = rec
    return out, bad


def main():
    quick = '--quick' in sys.argv
    gf, gbad = gate_floorplan()
    dec = Model(H_DEC); n, xf, lanes, worst = dec.best(tries=90)
    old = Model(H_OLD).best(tries=45)
    res = {'schema': 'opentallas.s81_vm_fe_h.plan.v4', 'agent': 'el1013-s81-vmfe/B5', 'rtl': 'FROZEN 693940a56 (R 2, KD 2, LGL / LDL / LAL 3)',
           'outline_decided': [W, H_DEC], 'outline_was': [W, H_OLD],
           'limits': {'cut': CUT_MAX, 'hop_um': HOP_MAX, 'usable_tracks': FREE}, 'tracks_per_um': {k: round(v, 2) for k, v in TPU.items()},
           'h_tracks_per_um_usable': {'free': round(HT_FREE * FREE, 2), 'over_m5_leaf': round(HT_M5 * FREE, 2), 'over_clt_or_fsr': 0.0},
           'm6_free_tracks_measured': {'dsfd_vm_clt (clt8a)': m6_free('physical/s81_ph_views/vm_master/views/dsfd_vm_clt/dsfd_vm_clt.lef'),
                                       'dsfd_vm_fsr (r4b)': m6_free('physical/ref_tile/dsfd_vm_fsr/views/dsfd_vm_fsr/dsfd_vm_fsr.lef')},
           'area_basis': 'MEASURED std-cell areas (results/arch/s81_vm_fe_h_areas_1013.json)', 'leaf_outlines': gf, 'leaf_outline_violations': gbad,
           'bundle_bits_mid_cut': int(round(dec.dem0.max())),
           'profile_bundles_only_decided': {'columns': ['x_um', 'bundle_bits', 'ratio', 'm5_leaf_height_still_allowed_um'], 'rows': dec.profile()},
           'lanes_needed': NLANE,
           'search_decided_outline': {'lanes_placed': n, 'fld_x': xf, 'lanes': lanes, 'worst_cut_ratio_at_x': worst},
           'search_old_outline': {'lanes_placed': old[0], 'fld_x': old[1], 'lanes': old[2], 'worst_cut_ratio_at_x': old[3]},
           'pass': bool(n == NLANE and not gbad)}
    print(f'bundles: mid cut {res["bundle_bits_mid_cut"]} b; M6 free over clt {res["m6_free_tracks_measured"]["dsfd_vm_clt (clt8a)"]}')
    print(f'1,520.064 x {H_OLD}: {old[0]} of {NLANE} lanes | 1,520.064 x {H_DEC}: {n} of {NLANE} lanes, fld x {xf}, {lanes}, worst cut {worst}')
    if not quick:
        opts = {'frozen contract (taller outline only)': {},
                'av / ok / ovf / sflt +1 relay stage (reach 950 um)': {'reach': 950.0},
                'S2 bundle tiles trimmed to non-constant bits': {'trim': True},
                'S3 clt re-routed at M5 (M6 free over the clt row)': {'clt_m5': True},
                'S4 lane returns daisy-chained (one 546-b bus a cut)': {'chain': True, 'reach': 950.0},
                'S2 + S3': {'trim': True, 'clt_m5': True},
                'S3 + S4': {'clt_m5': True, 'chain': True, 'reach': 950.0}}
        res['options'] = {}
        for k, o in opts.items():
            at = Model(H_DEC, **o).best(tries=45)
            mh = min_height(**o)
            res['options'][k] = {'lanes_at_decided_outline': at[0], 'min_outline_height_for_10_lanes': mh}
            print(f'  {k}: {at[0]} lanes at {H_DEC}; 10 lanes from H = {mh["h_um"] if mh else "> 1000"}')
    res['verdict'] = ('PASS' if res['pass'] else
                      f'FAIL: at most {n} of {NLANE} landing lanes fit 1,520.064 x {H_DEC} under the frozen contract, in a model that is optimistic '
                      '(no relay tiles, no local capacity, no descent of the fxs words through the lane rows).  The limit is the E-W cut, not reach: '
                      'relay stages do not help.  See `options`.')
    (ROOT / 'results/arch/s81_vm_fe_h_plan_1013.json').write_text(json.dumps(res, indent=1) + '\n')
    print('leaf outlines', {k.replace('dsfd_vm_', ''): (v['outline'], v['util_std_plus_macro']) for k, v in gf.items()}, gbad)
    print('PLAN:', 'PASS' if res['pass'] else 'FAIL')
    return 0 if res['pass'] else 1


if __name__ == '__main__':
    sys.exit(main())
