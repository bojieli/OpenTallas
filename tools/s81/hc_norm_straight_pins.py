#!/usr/bin/env python3
"""S-NORM candidate (2026-10-15): ONE bit order for the whole NORM-tree forward bus, producer + all consumers together.

Measured defect (v22_hc_local_split): the fd bus carries a different x order on every face of the per-half-tile chain
  ctfs_nt(k-1).fd_out (S) -> ctfn(k).fd_in (N) + ctfxs_nt(k).fd_in[0:1127] (N);  ctfn(k).fdm (S) -> ctfs_nt(k).fdm (N)
so some strip or seam always carries a full 2,920-bit permutation:
  * ctfs_nt v3 (fdm full-span rank order, fd_out old order): max vertical-cut crossing 1,971 bits in a 25.92-um strip ->
    GRT-0116 229,288 overflow (M2 105 %, M4 88 %) (s81hc_ctfsnt_ref-v3-ck4-cbddac3f6);
  * aligning only ctfs.fd_out + ctfn.fd_in to fdm (Codex 0815 proposal) leaves ctfxs_nt.fd_in behind: 544 / 1,128 die
    legs > 500 um (max 666.8).
Fix (geometry only, 0 cycles, 0 area): the bus order is chosen ONCE.  Bits 0..1127 (the ctfxs_nt broadcast subset) sit at
the granted ctfxs_nt.fd_in x (unchanged: ctfxs_nt.fd_in -> fdx -> ctnl / ctfl keeps its routed internal order); bits
1128..2919 continue monotonically east of that window (y-shift fdm[104+j] <= fd[104+j+128] stays local).  The same
x is used on ctfs_nt.fd_out, ctfn.fd_in, ctfn.fdm and ctfs_nt.fdm, so ctfs_nt is a straight relay, every chain seam
is vertical (jog 0), and ctfn only carries the 128-slot y shift.  fv (7 b) gets the same treatment at ctfxs_nt.fv_in.
Also ctfl_nt: fdx_local placed at the fdx x of the same bit wherever the 8 CLOSED CTPL receivers stay <= 499.8 um
(else the nearest legal x), so the relay is straight and its single flop sits at both pins.

    hc_norm_straight_pins.py   -> physical/s81_die_pins/v23_hc_norm_straight_candidate/{masters}.json/.tcl, report.json
CANDIDATE for S-DIE adoption (top-down rule): the die lead grants; first/last chain anchors (crootr.ch_fd, chain end)
are reported, not re-pinned here.
"""
import json
import sys
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import v19_pins_1014 as V  # noqa: E402

SRC = R / 'physical/s81_die_pins/v22_hc_local_split'
OUT = R / 'physical/s81_die_pins/v23_hc_norm_straight_candidate'
W, HS = 576.72, 25.92
M5 = lambda n: round(.012 + .048 * n, 3)          # ASAP7 M3 / M5 vertical track centres (same grid as v22)
LANES = (38.0, 88.0)                               # NORM dl / ul / cs lane window (x 40.03-86.06) kept free
REACH = 499.8
NB, NX, O_D, GT32 = 2920, 1128, 104, 128
# cth_nt rows (N offset, um; H 777.60 with ctfl): ctfxs 365.04, ctfl 390.96, ctfn 416.88, ctfs_nt 751.68
H, Y_XS, Y_FL, Y_FN, Y_FS = 777.6, 365.04, 390.96, 416.88, 751.68


def load(m):
    return json.loads((SRC / f'{m}.json').read_text())


def write(master, ports, extra):
    rec = dict(schema='opentallas.s81.assigned_pins.v1', master=master, case='v23_hc_norm_straight_CANDIDATE',
               outline_um=[W, HS], clock_entries={'stream': ['clk']}, source='tools/s81/hc_norm_straight_pins.py',
               ports={p: {'bits': len(v), 'uniform': False, 'per_bit': v} for p, v in ports.items()})
    rec.update(extra)
    (OUT / f'{master}.json').write_text(json.dumps(rec, indent=1) + '\n')
    lines = []
    for p, ps in ports.items():
        for i, (f, ly, c, _d) in enumerate(ps):
            x, y = {'S': (c, .042), 'N': (c, HS - .042), 'W': (.042, c), 'E': (W - .042, c)}[f]
            nm = p if len(ps) == 1 else f'{p}[{i}]'
            lines.append(f'place_pin -pin_name {{{nm}}} -layer {ly} -location {{{x:.3f} {y:.3f}}} -force_to_die_boundary')
    (OUT / f'{master}.tcl').write_text('\n'.join(lines) + '\n')


def xs(rec, p):
    return [b[2] for b in rec['ports'][p]['per_bit']]


def cut(pairs):
    """max number of (src x, dst x) wires crossing one vertical cut, and the sum of lateral um"""
    a = np.array([p[0] for p in pairs]); b = np.array([p[1] for p in pairs])
    lo, hi = np.minimum(a, b), np.maximum(a, b)
    best = max(int(((lo < x) & (hi > x)).sum()) for x in np.arange(0.5, W, 0.5))
    return dict(max_cut_bits=best, lateral_sum_um=round(float((hi - lo).sum()), 1), max_lateral_um=round(float((hi - lo).max()), 3))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    fn, fs, fx, fl = (load(m) for m in ('ot_s81_hc_ctfn', 'ot_s81_hc_ctfs_nt', 'ot_s81_hc_ctfxs_nt', 'ot_s81_hc_ctfl_nt'))
    rep = {}
    # ---- the one fd / fv order
    xfd = xs(fx, 'fd_in')                          # bits 0..1127: granted ctfxs_nt.fd_in x (unchanged)
    xfv = xs(fx, 'fv_in')                          # fv[0..6]: granted ctfxs_nt.fv_in x (unchanged)
    taken = sorted(xfd + xfv)
    east0 = max(taken) + .096
    tracks = [M5(n) for n in range(int(east0 / .048) + 1, int((W - 1.2) / .048)) if M5(n) >= east0]
    need = NB - NX
    step = len(tracks) / need
    assert step >= 2.0, ('east window too small for one bus per other track', len(tracks), need)
    east = [tracks[int(k * step)] for k in range(need)]
    assert all(b - a >= .095 for a, b in zip(east, east[1:]))
    xmap = xfd + east                              # bit i -> x
    assert len(xmap) == NB and len(set(xmap)) == NB
    rep['order'] = dict(bits_0_1127='ctfxs_nt.fd_in granted x (unchanged)', span_0_1127=[min(xfd), max(xfd)],
                        bits_1128_2919='monotone east', span_1128_2919=[east[0], east[-1]],
                        east_pitch_um=round((east[-1] - east[0]) / (need - 1), 4), fv='ctfxs_nt.fv_in granted x')
    # ---- masters
    def repl(rec, changes):
        p2 = {p: [list(b) for b in v['per_bit']] for p, v in rec['ports'].items()}
        for port, (face, xl) in changes.items():
            old = rec['ports'][port]['per_bit']
            p2[port] = [[face, 'M5', round(xl[i], 3), old[i][3]] for i in range(len(xl))]
        return p2
    pn = repl(fn, {'fd_in': ('N', xmap), 'fdm': ('S', xmap), 'fv_in': ('N', xfv), 'fvm': ('S', xfv)})
    ps = repl(fs, {'fdm': ('N', xmap), 'fd_out': ('S', xmap), 'fvm': ('N', xfv), 'fv_out': ('S', xfv)})
    # keep the ctfs_nt rst_out next to fv_out (old relation: rst_out 0.09 um east of fv_out[6])
    ps['rst_out'] = [['S', 'M5', round(max(xfv) + .192, 3), fs['ports']['rst_out']['per_bit'][0][3]]]
    assert ps['rst_out'][0][2] not in xmap
    # ---- ctfl_nt: straight where the CTPL reach allows
    _, cpl = V.lef_bits('physical/ref_tile/s81hc_ctpl_ref/views/ot_s81_hc_ctpl/ot_s81_hc_ctpl.lef')
    sy = H - (Y_FL + HS)
    rows = [(g, h, 144.72 * g, H - y - 118.8) for g in range(4) for h, y in enumerate((203.04, 416.88 + HS))]
    pl = {p: [list(b) for b in v['per_bit']] for p, v in fl['ports'].items()}
    moved, used, proof = [], set(), []
    for port, src in (('fdx_local', 'fdx'), ('fv_local', 'fv')):
        xn = xs(fl, src)
        out = []
        for b in range(len(xn)):
            pin = cpl[src][b]
            lim = [(x + pin[2] - (REACH - abs(sy - y - pin[3])), x + pin[2] + (REACH - abs(sy - y - pin[3])))
                   for _g, _h, x, y in rows]
            lo, hi = max(t[0] for t in lim), min(t[1] for t in lim)
            assert lo <= hi
            t = min(max(xn[b], lo), hi)
            n0 = round((t - .012) / .048)
            for dn in sorted(range(-400, 401), key=abs):
                x = M5(n0 + dn)
                if lo <= x <= hi and all(abs(x - u) >= .095 for u in used if abs(x - u) < .2):
                    break
            used.add(x)
            if abs(x - xn[b]) > .2:
                moved.append(dict(port=port, bit=b, n_x=xn[b], s_x=x, lateral_um=round(abs(x - xn[b]), 3)))
            out.append(['S', 'M5', x, .084])
            for g, h, xr, yr in rows:
                proof.append(round(abs(x - xr - pin[2]) + abs(sy - yr - pin[3]), 3))
        pl[port] = out
    assert max(proof) <= 500, max(proof)
    rep['ctfl_nt'] = dict(rule='fdx_local / fv_local at the fdx / fv x of the same bit unless the CTPL reach forbids',
                          cpl_reach_max_um=max(proof), moved_bits=len(moved),
                          max_lateral_um=max([m['lateral_um'] for m in moved], default=0.0),
                          layer='M5 (was M3 spread)', internal=cut(list(zip(xs(fl, 'fdx') + xs(fl, 'fv'),
                                                                          [q[2] for q in pl['fdx_local'] + pl['fv_local']]))),
                          v22_internal=cut(list(zip(xs(fl, 'fdx') + xs(fl, 'fv'), xs(fl, 'fdx_local') + xs(fl, 'fv_local')))),
                          moved=moved[:50])
    # ---- measurements: every incident seam and strip of the fd / fv chain
    ysh = [(xmap[O_D + j + GT32], xmap[O_D + j]) for j in range(NB - O_D - GT32)]
    rep['strips'] = dict(
        ctfs_nt=dict(v23=cut(list(zip(xmap, xmap))), v22=cut(list(zip(xs(fs, 'fdm'), xs(fs, 'fd_out'))))),
        ctfn=dict(v23_through=cut(list(zip(xmap, xmap))), v23_yshift=cut(ysh),
                  v22_through=cut(list(zip(xs(fn, 'fd_in'), xs(fn, 'fdm')))),
                  v22_yshift=cut([(xs(fn, 'fd_in')[O_D + j + GT32], xs(fn, 'fdm')[O_D + j]) for j in range(NB - O_D - GT32)])),
        ctfxs_nt='unchanged (fd_in / fdx / fv_in granted v22)')
    gap_xs, gap_fn = Y_XS, Y_FN                     # ctfs(k-1) S face = cth(k) N edge (abutted cth rows)
    seam = lambda a, b, dy: [abs(p - q) + dy for p, q in zip(a, b)]
    s = dict(
        fd_ctfs_to_ctfxs=dict(v23=max(seam(xmap[:NX], xfd, gap_xs)), v22=max(seam(xs(fs, 'fd_out')[:NX], xfd, gap_xs))),
        fd_ctfs_to_ctfn=dict(v23=max(seam(xmap, xmap, gap_fn)), v22=max(seam(xs(fs, 'fd_out'), xs(fn, 'fd_in'), gap_fn))),
        fdm_ctfn_to_ctfs=dict(v23=max(seam(xmap, xmap, Y_FS - Y_FN - HS)),
                              v22=max(seam(xs(fn, 'fdm'), xs(fs, 'fdm'), Y_FS - Y_FN - HS))),
        fv_ctfs_to_ctfxs=dict(v23=max(seam(xfv, xfv, gap_xs)), v22=max(seam(xs(fs, 'fv_out'), xfv, gap_xs))),
        fv_ctfs_to_ctfn=dict(v23=max(seam(xfv, xfv, gap_fn)), v22=max(seam(xs(fs, 'fv_out'), xs(fn, 'fv_in'), gap_fn))),
        fvm_ctfn_to_ctfs=dict(v23=max(seam(xfv, xfv, Y_FS - Y_FN - HS)),
                              v22=max(seam(xs(fn, 'fvm'), xs(fs, 'fvm'), Y_FS - Y_FN - HS))))
    for k, v in s.items():
        v.update(v23=round(v['v23'], 3), v22=round(v['v22'], 3))
    s['over500_v23'] = sum(1 for k, v in s.items() if isinstance(v, dict) and v['v23'] > 500)
    s['geometry'] = ('abutted cth_nt rows; ctfs_nt S face of half-tile k-1 = N edge of half-tile k; rows ctfxs 365.04, '
                     'ctfl 390.96, ctfn 416.88, ctfs_nt 751.68 (N offsets, H 777.60). Lower bound Manhattan, pin to pin.')
    rep['seams_max_um'] = s
    rep['chain_anchors'] = dict(
        first='crootr.ch_fd -> first cth ctfn.fd_in + ctfxs_nt.fd_in: ctfxs side unchanged; ctfn.fd_in bits 0..1127 now '
              'coincide with ctfxs_nt.fd_in (same x), bits 1128..2919 move east (x %.2f..%.2f, was %.2f..%.2f): S-DIE to '
              're-measure the crootr legs' % (east[0], east[-1], min(xs(fn, 'fd_in')), max(xs(fn, 'fd_in'))),
        last='last cth fd_out: same consumers as before (chain end), S-DIE to re-measure')
    rep['cost'] = dict(cycles=0, area_um2=0, rtl='unchanged', masters_repinned=['ot_s81_hc_ctfn', 'ot_s81_hc_ctfs_nt',
                       'ot_s81_hc_ctfl_nt'], unchanged=['ot_s81_hc_ctfxs_nt'])
    extra = dict(rule='S-NORM candidate 2026-10-15: one fd/fv bit order for producer + all consumers (see report.json)')
    write('ot_s81_hc_ctfn', pn, extra)
    write('ot_s81_hc_ctfs_nt', ps, extra)
    write('ot_s81_hc_ctfl_nt', pl, extra)
    (OUT / 'report.json').write_text(json.dumps(rep, indent=1) + '\n')
    print(json.dumps({k: v for k, v in rep.items() if k != 'ctfl_nt'}, indent=1))
    print('ctfl', {k: v for k, v in rep['ctfl_nt'].items() if k != 'moved'})


if __name__ == '__main__':
    main()
