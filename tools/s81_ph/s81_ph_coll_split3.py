#!/usr/bin/env python3
"""redesign-ds 2026-10-09: pin plans + slab composition of the THREE-TILE collective core column
(rtl/dsrom_sys/s81_ph/coll/dsfd_coll_split.sv): dsfd_coll_cb (bottom, VM side + lanes 0 / 4), dsfd_coll_ce (middle,
engine + lanes 1, 2, 5, 6), dsfd_coll_ct (top, lanes 3 / 7), stacked S -> N in the core column between the W and E
lane columns (lane tiles unchanged: their core-face pins stay at y = k * LH + Y_CORE in the slab).

    s81_ph_coll_split3.py [--lane-width 345.6] [--core-width 680.4] [--vm-pin-step 4] [--contract contract_split3]

Conventions as tools/s81_ph/s81_ph_coll_tiles.py (M4 horizontal / M5 vertical, offset 0.012, pitch 0.048, pins
0.024 x 0.192).  Seams: the cb N face and the ce S face carry the same buses at the same x (abutting pins); likewise
ce N / ct S.  Clock pins (generator rule, redesign-ds, tools/s81_ph/ck_pin_rule.py): the middle third of a LONG face: cb on its S face
(slab edge, free tracks between the VM pins) and ct on its N face (slab edge) at x = CW/2, ce (square) at W-face
mid-height between its two lane groups.  Writes physical/s81_ph_views/ports/<contract>/<tile>/{ports.json, io_place.tcl, ports.svh} for the lane tile
and the three core tiles, and physical/s81_ph_views/collective/composition_split3.json."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/s81_ph'))
import s81_ph_coll_tiles as T  # noqa: E402

P = T.P
LH, Y_CORE, Y_DIE = T.LH, T.Y_CORE, T.Y_DIE
HB, HE, HT = 340.2, 680.4, 340.2          # cb / ce / ct heights (sum 1360.8 = the core column)


def lane_group(pl, pre, face, y0, k=None, n=1):
    """the lane <-> core interface of one lane, in the lane tile's order; k = index into buses packed n lanes wide"""
    spec = [('lo_v', 1, 'output'), ('lo_r', 1, 'input'), ('lo_d', 553, 'output'), ('li_v', 1, 'input'),
            ('li_r', 1, 'output'), ('li_d', 553, 'input'), ('flt', 3, 'input')]
    y = y0
    for p, b, d in spec:
        if k is None:
            y = pl.bus(pre + p, b, d, face, 'M4', y)
        else:
            y = pl.bus(pre + p, b * n, d, face, 'M4', y, lo=b * k, n=b)
    return y


def ck_pins(pl, face, layer, target):
    """ck / rs on the free tracks nearest the face's target coordinate (clock-pin rule: middle of a long face)"""
    for p in ('ck', 'rs'):
        for dt in range(0, 400):
            for sgn in (1, -1):
                c = target + sgn * dt * P
                t = round((c - T.OFF) / P)
                if (face, layer, t) not in pl.used and (face, layer, t - 1) not in pl.used and (face, layer, t + 1) not in pl.used:
                    pl.bus(p, 1, 'input', face, layer, c)
                    break
            else:
                continue
            break
        target += 4.8


def seam(pl, face, buses, start, step, flip):
    """buses = [(port, bits, direction as seen from the SOUTH tile)]; flip = this plan is the NORTH tile"""
    x = start
    for p, b, d in buses:
        dd = d if not flip else ('input' if d == 'output' else 'output')
        lo = 1 if p == 'bw_d' else 0          # bw_d is [2099:1] in the RTL (packer word without its valid bit)
        x = pl.bus(p, b, dd, face, 'M5', x, step=step, lo=lo, n=b)
    return x


SEAM_BE = [('fvm_u', 592, 'output'), ('flt_u', 6, 'output'),
           ('lo0_v', 1, 'input'), ('lo0_r', 1, 'output'), ('lo0_d', 553, 'input'),
           ('li0_v', 1, 'output'), ('li0_r', 1, 'input'), ('li0_d', 553, 'output'),
           ('lo4_v', 1, 'input'), ('lo4_r', 1, 'output'), ('lo4_d', 553, 'input'),
           ('li4_v', 1, 'output'), ('li4_r', 1, 'input'), ('li4_d', 553, 'output'),
           ('bw_v', 1, 'input'), ('bw_d', 2099, 'input'), ('bw_cr', 1, 'output'), ('bw_flt', 1, 'output')]
SEAM_ET = [('lo3_v', 1, 'output'), ('lo3_r', 1, 'input'), ('lo3_d', 553, 'output'),
           ('li3_v', 1, 'input'), ('li3_r', 1, 'output'), ('li3_d', 553, 'input'),
           ('lo7_v', 1, 'output'), ('lo7_r', 1, 'input'), ('lo7_d', 553, 'output'),
           ('li7_v', 1, 'input'), ('li7_r', 1, 'output'), ('li7_d', 553, 'input'),
           ('flt_d', 6, 'input')]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--lane-width', type=float, default=345.6)
    ap.add_argument('--core-width', type=float, default=680.4)
    ap.add_argument('--vm-pin-step', type=int, default=4)
    ap.add_argument('--contract', default='contract_split3')
    a = ap.parse_args()
    LW, CW = a.lane_width, a.core_width
    T.CONTRACT = a.contract
    SW = T.r4(2 * LW + CW + 0.192)
    comp = []
    # lane tile (W master, E column = W mirrored MY), same pin plan as s81_ph_coll_tiles at this width
    pl = T.Plan('dsfd_coll_lane_w', LW, LH)
    y = pl.bus('rx', 515, 'input', 'W', 'M4', Y_DIE)
    y = pl.bus('tx', 512, 'output', 'W', 'M4', y)
    pl.bus('tf', 1, 'output', 'W', 'M4', y)
    T.lane_core_group(pl, 'E', Y_CORE)
    for i, p in enumerate(('ck', 'rs', 'chb')):
        pl.bus(p, 1, 'input', 'N', 'M5', LW / 2 + 4.8 * (i - 1))
    pl.emit('collective lane tile (as tools/s81_ph/s81_ph_coll_tiles.py), for the three-tile core column')
    for k in range(8):
        e = k >= 4
        x0 = SW - LW if e else 0.0
        comp.append(dict(inst=f'g_lane[{k}].g_{"e" if e else "w"}.u_l', master='dsfd_coll_lane_w', xy=[T.r4(x0), T.r4((k % 4) * LH)],
                         orient='MY' if e else 'R0', lane=['W0', 'W1', 'W2', 'W3', 'E0', 'E1', 'E2', 'E3'][k], ch_b=int(k not in (0, 4))))
    vstep = a.vm_pin_step
    # bottom tile
    pb = T.Plan('dsfd_coll_cb', CW, HB)
    lane_group(pb, 'w', 'W', Y_CORE)
    lane_group(pb, 'e', 'E', Y_CORE)
    x = pb.bus('f_vm', 592, 'input', 'S', 'M5', 4.8, step=vstep)
    x = pb.bus('ts', 3, 'input', 'S', 'M5', x, step=vstep)
    x = pb.bus('t_vm', 2100, 'output', 'S', 'M5', x, step=vstep)
    assert x < CW - 1, x
    xs = seam(pb, 'N', SEAM_BE, 4.8, 2, flip=False)
    assert xs < CW - 1, xs
    ck_pins(pb, 'S', 'M5', CW / 2)        # long face (slab S edge), middle; between the VM pins' free tracks
    pb.emit('three-tile collective core, BOTTOM tile: VM interface (S), output queue, lanes 0 (W) / 4 (E) relays, seam to dsfd_coll_ce (N)')
    # middle tile
    pe = T.Plan('dsfd_coll_ce', CW, HE)
    for l in range(2):
        lane_group(pe, 'w', 'W', l * LH + Y_CORE, k=l, n=2)
        lane_group(pe, 'e', 'E', l * LH + Y_CORE, k=l, n=2)
    seam(pe, 'S', SEAM_BE, 4.8, 2, flip=True)
    xt = seam(pe, 'N', SEAM_ET, 4.8, 4, flip=False)
    assert xt < CW - 1, xt
    pe.bus('ck', 1, 'input', 'W', 'M4', HE / 2); pe.bus('rs', 1, 'input', 'W', 'M4', HE / 2 + 4.8)
    pe.emit('three-tile collective core, MIDDLE tile: engine + 24 FIFO SRAMs, input queues, packer; lanes 1, 2 (W) / 5, 6 (E); seams S (cb) / N (ct)')
    # top tile
    pt = T.Plan('dsfd_coll_ct', CW, HT)
    lane_group(pt, 'w', 'W', Y_CORE)
    lane_group(pt, 'e', 'E', Y_CORE)
    seam(pt, 'S', SEAM_ET, 4.8, 4, flip=True)
    ck_pins(pt, 'N', 'M5', CW / 2)        # long face (slab N edge), middle
    pt.emit('three-tile collective core, TOP tile: lanes 3 (W) / 7 (E) relays, seam to dsfd_coll_ce (S)')
    comp += [dict(inst='u_cb', master='dsfd_coll_cb', xy=[LW, 0.0], orient='R0'),
             dict(inst='u_ce', master='dsfd_coll_ce', xy=[LW, HB], orient='R0'),
             dict(inst='u_ct', master='dsfd_coll_ct', xy=[LW, HB + HE], orient='R0')]
    rec = dict(schema='opentallas.s81_ph.composition.v1', slab='dsfd_sp_collective', slab_um=[SW, T.SH], core_um=[CW, HB + HE + HT],
               variant='split3', vm_pin_step=vstep, core_rtl_defines=['OT_S81PH_COLL_SPLIT', 'OT_S81PH_COLL_QPIPE'],
               lane_rtl_defines=['OT_S81PH_GBX_FMT1', 'OT_S81PH_EP_PIPE2'], reuse_east_w_my=True,
               source='rtl/dsrom_sys/s81_ph/dsfd_sp_collective.sv +define+OT_S81PH_COLL_SPLIT (rtl/dsrom_sys/s81_ph/coll/dsfd_coll_split.sv); '
                      'bench rtl/dsrom_sys/s81_ph/coll/run_coll_bench.sh',
               instances=comp,
               nets=dict(seams='u_cb N <-> u_ce S and u_ce N <-> u_ct S: same-named pins at the same x (abutting, 0-um gap)',
                         lanes='lane k core-face pins <-> the core tile holding lane k (0 / 4: u_cb, 1 2 5 6: u_ce, 3 / 7: u_ct) at slab y = (k % 4) * LH + Y_CORE',
                         clocks='pll_stream -> ck of every lane tile and of u_cb / u_ce / u_ct (die clock tree; core tiles take ck on the W face near mid-height)'),
               cost='lanes 0 / 3 / 4 / 7 +2 cycles each way, f_vm +2, packer -> t_vm +2; slab width +%.1f um vs the 540-um p4 core' % (CW - 540.0))
    out = ROOT / 'physical/s81_ph_views/collective/composition_split3.json'
    out.write_text(json.dumps(rec, indent=1) + '\n')
    print('ok', a.contract, 'slab', SW, 'x', T.SH, 'seam B/E end x', round(xs, 3), 'seam E/T end x', round(xt, 3))


if __name__ == '__main__':
    main()
