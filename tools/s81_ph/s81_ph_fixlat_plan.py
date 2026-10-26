#!/usr/bin/env python3
"""Contract pin plans of the MTP link ends that replace fixed-latency / plain-ready links (mtp-fixlat-1011, 2026-10-10).

RTL: rtl/dsrom_sys/mtp/dsfd_mtp_partner_ep.sv (dsfd_cap_mtp_ep, dsfd_vm_mtp_ep: the head-die sequencer's capture / VM
ends) and rtl/experimental/mtp_p2_ordered_20261009/dsfd_p2_lnk.sv (dsfd_p2_lnk at the P2 core's pins, dsfd_coll_p2_ep,
dsfd_vm_p2_ep).  Conventions as tools/s81_ph/s81_ph_mtp_plan.py (M4 W / E, M5 N / S, wide buses at pitch_tracks 4;
x on 10.8, y on 2.16).  Die side = the hub-bus pins, core side = the abutting slab core.  Outlines are pin-limited
except dsfd_p2_lnk (two 604-b lane receivers D 30 / 21 + start D 21: ~35k flops, ~17k um2 est -> 259.2 x 259.2).

    python3 tools/s81_ph/s81_ph_fixlat_plan.py  -> physical/s81_ph_views/ports/contract/<master>/{ports.json,io_place.tcl,
                                                   ports.svh}, physical/s81_ph_views/specs/<master>.json
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/s81_ph'))
import s81_ph_tiles_plan as TP  # noqa: E402

FLIT, UW, DW = 512, 10, 34
LW, SD, OW = 604, 101, 594
CK = [['ck', 1, 'input', 'S', 'M5', 1, 0.2], ['rst', 1, 'input', 'S', 'M5', 1, 0.4]]


def mirror(side, face):
    """the same group on the core side (c_*) and the die side (t_ / f_*)"""
    return [[n, b, d, face, 'M4', pt, fc] for n, b, d, pt, fc in side]


SPECS = [
    dict(master='dsfd_cap_mtp_ep', w_um=32.4, h_um=129.6, domain='stream_1p2',
         note='capture end of the sequencer RESULT link (ltx): W = capture core, E = die bus to dsfd_mtp_seq_rtt',
         ports=mirror([['c_rv', 1, 'input', 1, 0.03], ['c_rd', FLIT, 'input', 4, 0.5], ['c_rr', 1, 'output', 1, 0.95]], 'W') +
               mirror([['t_rv', 1, 'output', 1, 0.03], ['t_rd', FLIT, 'output', 4, 0.5], ['f_rg', 1, 'input', 1, 0.95]], 'E') + CK),
    dict(master='dsfd_vm_mtp_ep', w_um=43.2, h_um=43.2, domain='stream_1p2',
         note='VM end of the sequencer links: draft-head step receiver (lrx_rtt 11 / 11, D 26), rows-ready and '
              'draft-head result transmitters; W = VM core, E = die bus to dsfd_mtp_seq_rtt',
         ports=mirror([['c_hv', 1, 'output', 1, 0.05], ['c_hd', DW, 'output', 4, 0.2], ['c_hr', 1, 'input', 1, 0.33],
                       ['c_wv', 1, 'input', 1, 0.38], ['c_wd', UW, 'input', 4, 0.45], ['c_wr', 1, 'output', 1, 0.52],
                       ['c_qv', 1, 'input', 1, 0.57], ['c_qd', DW, 'input', 4, 0.72], ['c_qr', 1, 'output', 1, 0.9]], 'W') +
               mirror([['f_hv', 1, 'input', 1, 0.05], ['f_hd', DW, 'input', 4, 0.2], ['t_hg', 1, 'output', 1, 0.33],
                       ['t_wv', 1, 'output', 1, 0.38], ['t_wd', UW, 'output', 4, 0.45], ['f_wg', 1, 'input', 1, 0.52],
                       ['t_qv', 1, 'output', 1, 0.57], ['t_qd', DW, 'output', 4, 0.72], ['f_qg', 1, 'input', 1, 0.9]], 'E') + CK),
    dict(master='dsfd_vm_p2_ep', w_um=32.4, h_um=129.6, domain='stream_1p2',
         note='VM end of P2 lane 0 (ltx): W = VM core, E = die bus to the P2 slab',
         ports=mirror([['c_l0v', 1, 'input', 1, 0.02], ['c_l0d', LW, 'input', 4, 0.5], ['c_l0r', 1, 'output', 1, 0.97]], 'W') +
               mirror([['t_l0v', 1, 'output', 1, 0.02], ['t_l0d', LW, 'output', 4, 0.5], ['f_l0g', 1, 'input', 1, 0.97]], 'E') + CK),
    dict(master='dsfd_coll_p2_ep', w_um=64.8, h_um=302.4, domain='stream_1p2',
         note='collective end of the P2 links (lane 1 is sent by dsfd_coll_p2_lane_ba): start transmitter, result-row receiver (lrx_rtt 9 / 8, D 21) + abutting D4 valid/ready output; '
              'W = collective core, E = die bus to the P2 slab',
         ports=mirror([['c_sd', SD, 'input', 4, 0.47], ['c_sv', 1, 'input', 1, 0.505], ['c_sr', 1, 'output', 1, 0.51],
                       ['c_od', OW, 'output', 4, 0.76], ['c_ov', 1, 'output', 1, 0.97], ['c_or', 1, 'input', 1, 0.98]], 'W') +
               mirror([['t_sd', SD, 'output', 4, 0.47], ['t_sv', 1, 'output', 1, 0.505], ['f_sg', 1, 'input', 1, 0.51],
                       ['f_od', OW, 'input', 4, 0.76], ['f_ov', 1, 'input', 1, 0.97], ['t_og', 1, 'output', 1, 0.98]], 'E') + CK),
    dict(master='dsfd_p2_lnk', w_um=259.2, h_um=259.2, domain='stream_1p2',
         note='P2 link ends at the core pins: lane receivers lrx_rtt (lane 0 vm 12 / 14 D 30, lane 1 collective 8 / 9 '
              'D 21, OUTPUT_PIPE + transaction gate), start receiver (D 21), result-row transmitter.  W = die lanes, '
              'N = die start / result row, E = core lanes, S = core start / result row + clock',
         ports=[['f_l0v', 1, 'input', 'W', 'M4', 1, 0.005], ['f_l0d', LW, 'input', 'W', 'M4', 4, 0.24],
                ['t_l0g', 1, 'output', 'W', 'M4', 1, 0.48], ['f_l1v', 1, 'input', 'W', 'M4', 1, 0.485],
                ['f_l1d', LW, 'input', 'W', 'M4', 4, 0.715], ['t_l1g', 1, 'output', 'W', 'M4', 1, 0.97],
                ['f_sv', 1, 'input', 'N', 'M5', 1, 0.01], ['f_sd', SD, 'input', 'N', 'M5', 4, 0.06],
                ['t_sg', 1, 'output', 'N', 'M5', 1, 0.105], ['t_ov', 1, 'output', 'N', 'M5', 1, 0.12],
                ['t_od', OW, 'output', 'N', 'M5', 4, 0.4], ['f_og', 1, 'input', 'N', 'M5', 1, 0.65],
                ['c_in_v', 2, 'output', 'E', 'M4', 2, 0.02], ['c_in_d', 2 * LW, 'output', 'E', 'M4', 4, 0.5],
                ['c_in_r', 2, 'input', 'E', 'M4', 2, 0.975],
                ['ck', 1, 'input', 'S', 'M5', 1, 0.01], ['rst', 1, 'input', 'S', 'M5', 1, 0.02],
                ['c_start_v', 1, 'output', 'S', 'M5', 1, 0.03], ['c_start_d', SD, 'output', 'S', 'M5', 4, 0.08],
                ['c_start_r', 1, 'input', 'S', 'M5', 1, 0.125], ['c_out_v', 1, 'input', 'S', 'M5', 1, 0.14],
                ['c_out_d', OW, 'input', 'S', 'M5', 4, 0.45], ['c_out_r', 1, 'output', 'S', 'M5', 1, 0.7]]),
]


def main():
    summ = {}
    for spec in SPECS:
        ports = TP.plan(spec)
        rec = TP.write(spec['master'], spec['w_um'], spec['h_um'], spec['domain'], ports, spec)
        rec['generator'] = dict(file='tools/s81_ph/s81_ph_fixlat_plan.py')
        d = ROOT / 'physical/s81_ph_views/ports/contract' / spec['master']
        (d / 'ports.json').write_text(json.dumps(rec, indent=0) + '\n')
        (d / 'io_place.tcl').write_text((d / 'io_place.tcl').read_text().replace('tools/s81_ph/s81_ph_tiles_plan.py',
                                                                                 'tools/s81_ph/s81_ph_fixlat_plan.py'))
        summ[spec['master']] = dict(w=spec['w_um'], h=spec['h_um'], pins=sum(len(p['pins']) for p in ports.values()))
    print(json.dumps(summ, indent=1))


if __name__ == '__main__':
    main()
