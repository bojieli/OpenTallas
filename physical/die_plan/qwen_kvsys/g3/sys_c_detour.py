#!/usr/bin/env python3
"""Selected Qwen path: SYS_C actual macros and registered north-channel detour (PATH-KV-SYSC2 rev, GEOM F1-F3).

Consumes the KV plan (the Codex frozen combined plan codex/kv-plan-1713, which already carries the five macros, or
the f7ch plan + the macro proposal) and the type's own pins (gen_phys.type_pins on the input plan).  Emits a plan
delta plus cycle receipt.  Physical-model geometry only: no route, no PG sign-off.

GEOM-REVIEW 10-25 14:21 FAIL -> structural fixes here:
  F1  ft1 (523 bits, W face -> N corridor -> E face): every bit owns ONE vertical column in a turn band
      (W x 525..650 above the SRAM stack, E x 1512..1640 between the E pin band and the N corridor).  All three
      turn-side stations of a bit sit on its column: bottom corner (col, pin y), a compact 7-row bank at y 690
      (one lattice column holds ~6 bits), top corner (col, corridor y).  Planar order: lowest W pin y -> easternmost
      W column -> lowest corridor y -> westernmost E column (E pin-order inversions are counted and reported).
      Corridor stations s4/s5 at 1/3, 2/3 of each bit's own W-col -> E-col span (<= 405 per hop).
  F2  clock.keepouts_um = VDDPHY domain (body + guard) + tap-buffer width + 1 site; clock.tap_recentre "sinks":
      grid taps pushed off the PHY re-centre on the weighted L1 median of their real sinks (SRAM clock pins via
      clock.sink_sites_um + per-bit stations); per-tap planned load / radius reported.
  F3  clock and reset root tap_um moved W of the turn band, between the SRAM-stack top and the ft1 W pin band.
Keeps: VDDPHY domain [682.56,8.64,1477.44,803.52] (asserted: no ft site / station / SRAM / tap inside), N corridor.
"""
import argparse
import copy
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[3] / 'tools' / 'die_plan'))
import ft_bit_sites_gen as F  # noqa: E402

PHY = [691.2, 17.28, 1468.8, 794.88]
GUARD = 8.64    # VDDPHY guard ring W/E/N inside sys_c
S_MOAT = 8.64   # S side: the domain stops 8.64 um inside the partition edge
NORTH = 829.44  # first corridor track (one bit per 0.27-um row up to 970.38)
WBAND = (525.0, 650.0)     # W turn band: x range of the 523 W columns (easternmost = lowest W pin)
EBAND = (1512.0, 1640.0)   # E turn band (westernmost = lowest corridor track)
BANK_Y = 690.0             # mid-turn compact row bank (W and E)
ROOT = [466.56, 397.44]    # F3: clock/reset root, W of the W band, between SRAM top 344 and the W pin band 445
FWD_Y = 816.48             # o_host_link_rst_n trunk: between the domain top 803.52 and the corridor 829.44
FWD_W, FWD_E = 665.28, 1494.72   # FWD vertical legs: between the turn bands and the domain (clear of both)
TAPBUF_UM = 4.32           # >= BUFx24 clock-tap root buffer width (ASAP7) ...
SITE_UM = 0.054            # ... + one placement site halo
BASE = {'slot:ft1': 6, 'bus:o_host_link_rst_n': 5}   # f7ch station counts before any SYS_C detour (ledger basis)
MACROS = ('ot_qkvd_ucie_x64_phy', 'd2d_sram_1r1w_64x137_m1_r2c2_p288')


def split_path(path):
    pts = []
    for a, b in zip(path, path[1:]):
        n = max(1, math.ceil(F.man(a, b) / 405))
        pts.extend([round(a[0] + (b[0] - a[0]) * j / n, 4), round(a[1] + (b[1] - a[1]) * j / n, 4)]
                   for j in range(1, n + 1))
    return pts


def inversions(seq):
    """number of out-of-order pairs (merge count)."""
    def rec(a):
        if len(a) < 2:
            return a, 0
        m = len(a) // 2
        l, x = rec(a[:m]); r, y = rec(a[m:])
        out, i, j, c = [], 0, 0, x + y
        while i < len(l) and j < len(r):
            if l[i] <= r[j]:
                out.append(l[i]); i += 1
            else:
                out.append(r[j]); j += 1; c += len(l) - i
        out += l[i:] + r[j:]
        return out, c
    return rec(list(seq))[1]


def apply(raw, proposal=None):
    import schema as S
    import gen_phys as G
    import taps as TP
    t = raw['partition_types']['kv3_sys_c']
    W, H = t['outline_um']
    have = sorted(m['module'] for m in t.get('contents', []) if 'origin_um' in m)
    if have != sorted(['ot_qkvd_ucie_x64_phy'] + ['d2d_sram_1r1w_64x137_m1_r2c2_p288'] * 4):
        if proposal is None:
            raise ValueError(f'kv3_sys_c contents {have}: need the macro proposal')
        t['contents'] = copy.deepcopy(proposal['macros'])
    dom_t = [round(PHY[0] - GUARD, 4), round(PHY[1] - S_MOAT, 4), round(PHY[2] + GUARD, 4), round(PHY[3] + GUARD, 4)]
    assert dom_t == [682.56, 8.64, 1477.44, 803.52], dom_t

    def inside(x, y, r=dom_t, m=0.0):
        return r[0] - m <= x <= r[2] + m and r[1] - m <= y <= r[3] + m

    # F3 + F2 clock record (clock/reset roots off the band; PHY keepout for every tap; displaced taps re-centred)
    srams = [m for m in t['contents'] if m['module'].startswith('d2d_sram')]
    ck = t.setdefault('clock', {})
    ck['tap_um'] = list(ROOT)
    t.setdefault('reset', {})['tap_um'] = list(ROOT)
    g = TAPBUF_UM + SITE_UM
    ck['keepouts_um'] = [[round(dom_t[0] - g, 4), round(dom_t[1] - g, 4), round(dom_t[2] + g, 4),
                          round(dom_t[3] + g, 4)]]
    ck['tap_recentre'] = 'sinks'
    # SRAM clk pin (LEF: M4 RECT 0 0.768 0.024 0.792 on the W edge), one sink each
    ck['sink_sites_um'] = [[round(m['origin_um'][0] + 0.012, 4), round(m['origin_um'][1] + 0.78, 4), 1] for m in srams]

    # FWD o_host_link_rst_n: own trunk below the corridor, vertical legs between band and domain
    ledger = []
    fwd_blocks = []
    for e in t.get('internal_stations', []):
        if e.get('conn') != 'bus:o_host_link_rst_n':
            continue
        a, b = e['from_um'], e['to_um']
        before = len(e['regs_um'])
        path = [a, [FWD_W, a[1]], [FWD_W, FWD_Y], [FWD_E, FWD_Y], [FWD_E, b[1]], b]
        e['regs_um'] = split_path(path)[:-1]
        e['note'] = ('SYS_C UCIe north detour (PATH-KV-SYSC2): own trunk y 816.48 below the ft1 corridor, legs at '
                     'x 665.28 / 1494.72 between the ft1 turn bands and the VDDPHY domain; <=405um')
        hops = [F.man(p, q) for p, q in zip([a] + e['regs_um'], e['regs_um'] + [b])]
        ledger.append(dict(conn=e['conn'], before_f7ch=BASE[e['conn']], before_input=before, after=len(e['regs_um']),
                           added_cycles=len(e['regs_um']) - BASE[e['conn']], max_hop_um=round(max(hops), 3)))
        fwd_blocks += [(x - 3, y - 3, x + 3, y + 3) for x, y in e['regs_um']]
    blocks = [(*m['origin_um'], m['origin_um'][0] + m['outline_um'][0], m['origin_um'][1] + m['outline_um'][1])
              for m in t['contents']]
    blocks.append(tuple(dom_t))                                   # no ft site inside the VDDPHY domain
    blocks += fwd_blocks
    blocks += [(x - 3, y - 3, x + 3, y + 3) for e in t.get('internal_stations', [])
               if e.get('conn') != 'bus:o_host_link_rst_n' for x, y in e['regs_um']]
    blocks.append((ROOT[0] - 4.32, ROOT[1] - 4.32, ROOT[0] + 4.32, ROOT[1] + 4.32))   # root buffer
    F.FACE_KEEP_UM = 7.
    sites = F.Sites(W, H, blocks)

    P = S.Plan(raw)
    by = {}
    for name, bit, _ln, x, y, _face in G.type_pins(P, 'kv3_sys_c'):
        by.setdefault(name, {})[bit] = (x, y)
    slot = next(s for s in t['ft_slots'] if s['name'] == 'ft1')
    n = slot['width'] + 1
    A, B = by['ft1_i'], by['ft1_o']
    order = sorted(range(n), key=lambda i: (A[i][1], i))
    rank = {i: r for r, i in enumerate(order)}
    stages = [[None] * n for _ in range(11)]
    maxhop = maxout = 0.0
    hopmax_by_stage = [0.0] * 12
    draw = []
    for i in order:
        r = rank[i]
        f = r / (n - 1)
        xw = WBAND[1] - f * (WBAND[1] - WBAND[0])     # lowest W pin -> easternmost W column
        xe = EBAND[0] + f * (EBAND[1] - EBAND[0])     # lowest corridor track -> westernmost E column
        yn = NORTH + r * F.ROW
        span = xe - xw
        pts = [(xw / 2, A[i][1]), (xw, A[i][1]), (xw, BANK_Y), (xw, yn),
               (xw + span / 3, yn), (xw + 2 * span / 3, yn), (xe, yn),
               (xe, BANK_Y), (xe, B[i][1]), ((xe + W - 12) / 2, B[i][1]), (W - 12, B[i][1])]
        horiz = (True, False, False, True, True, True, True, False, True, True, True)
        out = []
        for j, p in enumerate(pts):
            xy = sites.take(*p, horiz=horiz[j])
            stages[j][i] = [round(xy[0], 6), round(xy[1], 6)]
            out.append((xy[0] + F.CELL[0] / 2, xy[1] + F.CELL[1] / 2))
        chain = [A[i]] + out + [B[i]]
        hops = [F.man(a, b) for a, b in zip(chain, chain[1:])]
        for k, h in enumerate(hops):
            hopmax_by_stage[k] = max(hopmax_by_stage[k], h)
        maxhop = max(maxhop, max(hops))
        maxout = max(maxout, hops[-1])
        if r % 32 == 0 or r == n - 1:
            draw.append(dict(bit=i, rank=r, path=[list(p) for p in chain]))
    if maxhop > 405 or maxout > 20:
        raise ValueError(f'actual FT hop/outface fail: {maxhop}/{maxout}')
    before = slot['stations']
    slot.update(stations=12, bit_sites_um=stages, bit_site_cell_um=list(F.CELL))
    slot.pop('regs_um', None)
    slot['note'] = ('PATH-KV-SYSC2 (GEOM F1): per-bit turn columns W x 525-650 / E x 1512-1640, turn stations on the '
                    'bit column (corner, 7-row bank y 690, corner), planar W order, N corridor y 829.44-970.38')
    ledger.append(dict(conn='slot:ft1', bits=n, before_f7ch=BASE['slot:ft1'], before_input=before, after=12,
                       added_cycles=12 - BASE['slot:ft1'], added_flops=(12 - BASE['slot:ft1']) * n))

    # turn-band geometry metrics (F1)
    def band(js):
        cs = [sites_xy for j in js for sites_xy in stages[j]]
        x = [c[0] for c in cs]; y = [c[1] for c in cs]
        return dict(stations=len(cs), x=[round(min(x), 3), round(max(x) + F.CELL[0], 3)],
                    y=[round(min(y), 3), round(max(y) + F.CELL[1], 3)])
    bankW = [stages[2][i][1] for i in range(n)]; bankE = [stages[7][i][1] for i in range(n)]
    col_dev = max(max(abs(stages[j][i][0] + F.CELL[0] / 2 - (WBAND[1] - rank[i] / (n - 1) * (WBAND[1] - WBAND[0])))
                      for i in range(n)) for j in (1, 2, 3))
    col_dev_e = max(max(abs(stages[j][i][0] + F.CELL[0] / 2 - (EBAND[0] + rank[i] / (n - 1) * (EBAND[1] - EBAND[0])))
                        for i in range(n)) for j in (6, 7, 8))
    b_order = [B[i][1] for i in order]
    turn = dict(W_band_x=list(WBAND), E_band_x=list(EBAND), column_pitch_um=round((WBAND[1] - WBAND[0]) / (n - 1), 4),
                bits_per_um_W=round(n / (WBAND[1] - WBAND[0]), 2), bits_per_um_E=round(n / (EBAND[1] - EBAND[0]), 2),
                corridor_bits_per_um=round(n / (n * F.ROW), 2),
                W_turn_stations=band((1, 2, 3)), E_turn_stations=band((6, 7, 8)),
                W_bank_rows=len(set(round(v, 3) for v in bankW)), E_bank_rows=len(set(round(v, 3) for v in bankE)),
                max_station_offset_from_own_column_um=dict(W=round(col_dev, 3), E=round(col_dev_e, 3)),
                W_crossings=0, E_pin_order_inversions=inversions(b_order),
                E_pin_order_note='W side planar by construction (rank = W pin y); E crossings = pairs whose E pin '
                                 'order differs from their W pin order (face assignment; H/V layer crossings)',
                hop_max_by_stage_um=[round(h, 3) for h in hopmax_by_stage])

    # VDDPHY domain record (unchanged form) + asserts
    bad = [('ft1', xy) for st in stages for xy in st if xy and (inside(*xy) or inside(xy[0] + F.CELL[0], xy[1] + F.CELL[1]))]
    bad += [(e['conn'], xy) for e in t.get('internal_stations', []) for xy in e['regs_um'] if inside(*xy)]
    bad += [(m['inst'], m['origin_um']) for m in t['contents'] if m['module'] != 'ot_qkvd_ucie_x64_phy' and
            m['origin_um'][0] + m['outline_um'][0] > dom_t[0] and m['origin_um'][0] < dom_t[2] and
            m['origin_um'][1] + m['outline_um'][1] > dom_t[1] and m['origin_um'][1] < dom_t[3]]
    part = next(p for p in raw['partitions'] if p['type'] == 'kv3_sys_c')
    ox, oy = part['origin_um']
    rect = [round(PHY[0] + ox, 4), round(PHY[1] + oy, 4), round(PHY[2] + ox, 4), round(PHY[3] + oy, 4)]
    drect = [round(dom_t[0] + ox, 4), round(dom_t[1] + oy, 4), round(dom_t[2] + ox, 4), round(dom_t[3] + oy, 4)]
    pg = raw['die'].setdefault('pg', {})
    domains = pg.setdefault('domains', [])
    old = next((d for d in domains if d['name'] == 'phy_sys_c_ucie'), None)
    if old is None:
        old = dict(name='phy_sys_c_ucie', nets=['VDDPHY', 'VSS'], io=['io_sys_c_ucie_rom'],
                   grid=[dict(layer=l, width_um=1.92, pitch_um=8.64, offset_um=4.32, nets=['VDDPHY', 'VSS'])
                         for l in ['M8', 'M9']],
                   bumps=dict(rect_um=rect, pitch_um=45., use='power_ground',
                              note='dedicated VDDPHY/VSS C4 rows over the UCIe macro (45-um array); academic bump '
                                   'assumption, not vendor escape qualification'),
                   note='OWNER decision 7: separate PHY supply on the UCIe macro, guard ring inside sys_c, no core-VDD '
                        'object inside')
        domains.append(old)
    old['rect_um'] = drect

    # taps (F2): the plan's own tap grid with the keepout + re-centre, then per-tap load / radius
    P = S.Plan(raw)
    TP._CACHE.clear()
    grid = S.tap_grid(P, 'kv3_sys_c')
    sinks = TP.recentre_sinks(P, 'kv3_sys_c')
    loads = TP.tap_loads([(x, y) for _, x, y in grid], sinks)
    ko = ck['keepouts_um'][0]
    tap_rows = []
    for (nm, x, y), (ld, far) in zip(grid, loads):
        d = max(dom_t[0] - x, x - dom_t[2], dom_t[1] - y, y - dom_t[3])
        tap_rows.append(dict(port=nm, xy=[x, y], planned_sinks=int(ld), radius_um=round(far, 1),
                             dist_to_domain_um=round(d, 2)))
        if inside(x, y, ko):
            bad.append(('tap ' + nm, [x, y]))
    rs = G.tap_points(P, 'kv3_sys_c')[1]
    if inside(*rs, ko):
        bad.append(('reset tap', rs))
    if bad:
        raise ValueError(f'core-VDD objects inside the PHY PG domain / tap keepout: {bad[:5]}')
    mv = [r for r in tap_rows if r['dist_to_domain_um'] < 60]
    report = dict(type='kv3_sys_c', verdict='GEOMETRY_PLAN_F1F2F3', max_ft_hop_um=round(maxhop, 3),
                  max_out_hop_um=round(maxout, 3), ft_sites=len(sites.used), ledger=ledger, turn=turn,
                  root=dict(clock_tap_um=ck['tap_um'], reset_tap_um=t['reset']['tap_um'], reset_snapped=list(rs),
                            note='W of the W turn band (x 525), between SRAM top 344 and the W pin band 445'),
                  tap_keepout_um=ko, tap_keepout_basis=f'domain + {TAPBUF_UM} tap buffer + {SITE_UM} site; '
                  f'tap_clear adds {S.TAP_CLEAR_UM} clearance', taps=tap_rows, taps_near_phy=mv,
                  tap_sinks_note='planned FIRM sinks only (face regs, per-bit ft stations, FWD excluded, 4 SRAM clk); '
                                 'internal logic is placed by the kit and served by the fixed grid taps',
                  phy_rect_type_um=PHY, phy_rect_die_um=rect, pg_domain_type_um=dom_t, pg_domain_die_um=drect,
                  sampled=draw, required='GEOM PASS, then: KV per-die delta (+6 ft1 / +3 FWD), regenerate '
                                         'latency/R8/native bound RTL, kit + actual G2 with the VDDPHY blockage')
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument('plan'); p.add_argument('io'); p.add_argument('out')
    p.add_argument('--proposal'); p.add_argument('--report', required=True); p.add_argument('--io-out', required=True)
    p.add_argument('--delta', help='write the kv3_sys_c type + pg domain as a plan delta JSON')
    a = p.parse_args()
    raw = json.loads(Path(a.plan).read_text())
    io = json.loads(Path(a.io).read_text())
    prop = json.loads(Path(a.proposal).read_text()) if a.proposal else None
    r = apply(raw, prop)
    for e in io:
        if e['name'] == 'io_sys_c_ucie_rom':
            e['rect_um'] = r['phy_rect_die_um']
            e['sites'] = int(777.6 // 45) ** 2
            if 'dedicated VDDPHY' not in e.get('note', ''):
                e['note'] = e.get('note', '') + ' | actual native macro abstract footprint; dedicated VDDPHY domain phy_sys_c_ucie'
    Path(a.out).write_text(json.dumps(raw, indent=1) + '\n')
    Path(a.io_out).write_text(json.dumps(io, indent=1) + '\n')
    Path(a.report).write_text(json.dumps(r, indent=1) + '\n')
    if a.delta:
        Path(a.delta).write_text(json.dumps(dict(pg_domains=[d for d in raw['die']['pg']['domains']
                                                             if d['name'] == 'phy_sys_c_ucie'],
                                                 kv3_sys_c=raw['partition_types']['kv3_sys_c'])) + '\n')
    print(json.dumps({k: v for k, v in r.items() if k not in ('sampled', 'taps')}, indent=1))


if __name__ == '__main__':
    main()
