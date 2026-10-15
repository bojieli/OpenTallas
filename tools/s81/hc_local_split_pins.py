#!/usr/bin/env python3
"""S-DIE grants for the HC NORM-tree LOCAL_SPLIT (S-NORM requests 1-3, el1011-s81die.log 2026-10-15 06:04/06:14).

1. ot_s81_hc_ctfxs_nt adopts the ctfx_nt slot (576.72 x 25.92): the granted v20_hc_capture ctfx_nt rectangles minus
   fdx_local / fv_local, every other rectangle unchanged (checked bit by bit).
2. ot_s81_hc_ctfl_nt: a new 576.72 x 25.92 row directly below ctfxs_nt in every cth_nt (cth_nt 751.68 -> 777.60).
   N face: fdx[1128] / fv[7] on M5 exactly below ctfxs_nt.fdx / fv (abutted rows, jog 0).  S face: fdx_local / fv_local
   on M3, spread in CPL bit order over >= 2x the old 115-um span, every bit placed so all 8 CLOSED CTPL receivers stay
   <= 499.8 um (Manhattan, pin to pin).  W face: clk, rst_in (M4; rst_in <= ctfn.rst_c, W face of the row below).
3. ot_s81_hc_ctfn.fdm (S) and ot_s81_hc_ctfs_nt.fdm (N): one straight vertical bus over the full strip width outside the
   NORM dl/ul/cs lanes (x 40.03-86.06), same bit order, same x on both faces (jog 0); fvm untouched.
Geometry only: native TT/FF/DRC and the CTRA/CTRB hops (no published LEF) remain owed by S-NORM.
"""
import json
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import v19_pins_1014 as V  # noqa: E402

OUT = R / 'physical/s81_die_pins/v22_hc_local_split'
W, HS = 576.72, 25.92
M3 = lambda n: round(.012 + .048 * n, 3)          # ASAP7 M3 / M5 vertical track centres
REACH = 499.8
OLD_SPAN = 115.0


def load(p):
    return json.loads((R / p).read_text())


def write(master, ports, case, extra=None):
    rec = dict(schema='opentallas.s81.assigned_pins.v1', master=master, case=case, outline_um=[W, HS],
               clock_entries={'stream': ['clk']}, source='tools/s81/hc_local_split_pins.py',
               ports={p: {'bits': len(v), 'uniform': False, 'per_bit': v} for p, v in ports.items()})
    rec.update(extra or {})
    (OUT / (master + '.json')).write_text(json.dumps(rec, indent=1) + '\n')
    lines = []
    for p, ps in ports.items():
        for i, (f, ly, c, _d) in enumerate(ps):
            x, y = {'S': (c, .042), 'N': (c, HS - .042), 'W': (.042, c), 'E': (W - .042, c)}[f]
            nm = p if len(ps) == 1 else f'{p}[{i}]'
            lines.append(f'place_pin -pin_name {{{nm}}} -layer {ly} -location {{{x:.3f} {y:.3f}}} -force_to_die_boundary')
    (OUT / (master + '.tcl')).write_text('\n'.join(lines) + '\n')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report = {}
    # ---- 1. ctfxs_nt = granted ctfx_nt minus the local pair
    cap = load('physical/s81_die_pins/v20_hc_capture/ot_s81_hc_ctfx_nt.json')
    xs_ports = {p: v['per_bit'] for p, v in cap['ports'].items() if p not in ('fdx_local', 'fv_local')}
    write('ot_s81_hc_ctfxs_nt', xs_ports, 'v22_hc_local_split_GRANTED',
          dict(rule='S-DIE r11 grant 2026-10-15: the v20_hc_capture ctfx_nt slot and rectangles minus fdx_local/fv_local'))
    report['ctfxs_nt'] = dict(ports=sorted(xs_ports), removed=['fdx_local', 'fv_local'], slot='ctfx_nt row, unchanged')

    # ---- 2. ctfl_nt
    _, cpl = V.lef_bits('physical/ref_tile/s81hc_ctpl_ref/views/ot_s81_hc_ctpl/ot_s81_hc_ctpl.lef')
    H = 751.68 + HS                                  # cth_nt with the new row
    sy = H - (390.96 + HS)                           # ctfl S face, y from the cth_nt bottom (= 360.72, unchanged)
    rows = [(g, h, 144.72 * g, H - y - 118.8) for g in range(4) for h, y in enumerate((203.04, 416.88 + HS))]
    ports = {'clk': [['W', 'M4', 6.108, .084]], 'rst_in': [['W', 'M4', 6.204, .084]]}
    ports['fdx'] = [['N', 'M5', b[2], .084] for b in xs_ports['fdx']]
    ports['fv'] = [['N', 'M5', b[2], .084] for b in xs_ports['fv']]
    used, proof = set(), []
    for port, src in (('fdx_local', 'fdx'), ('fv_local', 'fv')):
        bits = sorted(cpl[src])
        iv = {}
        for b in bits:
            pin = cpl[src][b]
            lim = [(x + pin[2] - (REACH - abs(sy - y - pin[3])), x + pin[2] + (REACH - abs(sy - y - pin[3])))
                   for _g, _h, x, y in rows]
            lo, hi = max(t[0] for t in lim), min(t[1] for t in lim)
            assert lo <= hi, (port, b, 'no CPL reach solution', lo, hi)
            iv[b] = (lo, hi, (lo + hi) / 2)
        order = sorted(bits, key=lambda b: (iv[b][2], b))
        c = sum(iv[b][2] for b in bits) / len(bits)
        span = max(2.5 * OLD_SPAN, .096 * 2 * len(bits)) if len(bits) > 8 else 2.0
        out = [None] * len(bits)
        for k, b in enumerate(order):
            t = c - span / 2 + span * (k + .5) / len(bits)
            lo, hi, _ = iv[b]
            t = min(max(t, lo), hi)
            n0 = round((t - .012) / .048)
            for dn in sorted(range(-400, 401), key=abs):
                x = M3(n0 + dn)
                if lo <= x <= hi and all(abs(x - u) >= .095 for u in used if abs(x - u) < .2):
                    break
            else:
                raise SystemExit(f'no M3 track for {port}[{b}]')
            used.add(x)
            out[b] = ['S', 'M3', x, .084]
        ports[port] = out
        for b in bits:
            pin = cpl[src][b]
            for g, h, x, y in rows:
                proof.append(dict(port=port, bit=b, group=g, half=h,
                                  length_um=round(abs(out[b][2] - x - pin[2]) + abs(sy - y - pin[3]), 3)))
        xs = [q[2] for q in out]
        report.setdefault('ctfl_nt_span_um', {})[port] = [min(xs), max(xs), round(max(xs) - min(xs), 3)]
    write('ot_s81_hc_ctfl_nt', ports, 'v22_hc_local_split_GRANTED',
          dict(rule='S-DIE r11 grant 2026-10-15: new cth_nt row below ctfxs_nt; N straight below ctfxs_nt fdx/fv, '
                    'S fdx_local/fv_local spread on M3 within the CTPL reach'))
    mx = max(r['length_um'] for r in proof)
    report['ctfl_nt'] = dict(slot=dict(row_y_from_N=390.96, outline=[W, HS], cth_nt_height=[751.68, H]),
                             cpl_reach_max_um=mx, over500=[r for r in proof if r['length_um'] > 500],
                             ctra_ctrb='unverified (no published LEF)', hops=proof)
    assert mx <= 500, mx

    # ---- 3. ctfn.fdm (S) / ctfs_nt.fdm (N): straight, full width outside the NORM lanes
    fn = load('physical/s81_die_pins/v20_hc_inherited/ot_s81_hc_ctfn.json')
    fs = load('physical/s81_die_pins/v19_ntree/ot_s81_hc_ctfs_nt.json')
    keep = [q[2] for q in fn['ports']['fvm']['per_bit']] + [q[2] for q in fs['ports']['fvm']['per_bit']]
    tracks = [M3(n) for n in range(0, int((W - .5) / .048)) if (1.0 <= M3(n) <= 38.0 or 88.0 <= M3(n) <= W - 1.2)]
    tracks = [t for t in tracks if all(abs(t - k) > .1 for k in keep)]
    nb = fn['ports']['fdm']['bits']
    assert nb == fs['ports']['fdm']['bits'] == 2920 and len(tracks) >= 2 * nb
    pick = [tracks[int(i * (len(tracks) - 1) / (nb - 1))] for i in range(nb)]
    assert len(set(pick)) == nb and all(b - a >= .095 for a, b in zip(pick, pick[1:]))
    # one bit -> x map for both faces (straight, jog 0), in ctfn's old fdm rank order
    rank = sorted(range(nb), key=lambda i: fn['ports']['fdm']['per_bit'][i][2])
    xmap = {i: pick[k] for k, i in enumerate(rank)}
    for rec, face, master in ((fn, 'S', 'ot_s81_hc_ctfn'), (fs, 'N', 'ot_s81_hc_ctfs_nt')):
        old = rec['ports']['fdm']['per_bit']
        p2 = {p: v['per_bit'] for p, v in rec['ports'].items()}
        p2['fdm'] = [[face, 'M5', xmap[i], old[i][3]] for i in range(nb)]
        write(master, p2, 'v22_hc_local_split_GRANTED',
              dict(rule='S-DIE r11 grant 2026-10-15 (S-NORM request 3): fdm one straight bus over x 1.0-38.0 + 88.0-575.5 '
                        '(NORM lanes 40.03-86.06 kept free), bit i at the same x on ctfn S and ctfs_nt N, ctfn rank order'))
    rb = sorted(range(nb), key=lambda i: fs['ports']['fdm']['per_bit'][i][2])
    report['fdm'] = dict(span_um=[pick[0], pick[-1]], old_span_ctfn=[77.532, 455.292], old_span_ctfs_nt=[139.932, 432.348],
                         straight=True, ctfs_nt_old_order_same_as_ctfn=rank == rb,
                         note='ctfs_nt is CLOSED (native PASS): re-pinned by this table entry (S-NORM request 3)')
    report['die_cost'] = dict(cth_nt_um=[751.68, H], note='+25.92 per cth_nt row; at the NT swap sp_hc_s (10 rows) +259.2 '
                              'and sp_hc_t (12 rows) +311.04 vs v19_ntree; vs the bound serial v20 cth (758.16) +19.44/row '
                              '= +194.4 / +233.28 um. Not absorbed in GEN18 (NT is default-off); the swap GEN must take it '
                              'from the hc_corridor (1512) or report the die change.',
                              area_um2_per_strip=round(W * HS, 1), cycles=0)
    (OUT / 'layout.json').write_text(json.dumps(report, indent=1) + '\n')
    print('HC_LOCAL_SPLIT_PINS ctfl reach max', mx, 'spans', report['ctfl_nt_span_um'], 'fdm', report['fdm']['span_um'],
          'straight', report['fdm']['straight'])


if __name__ == '__main__':
    main()
