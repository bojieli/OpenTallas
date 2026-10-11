#!/usr/bin/env python3
"""Contract pin plan of dsfd_coll_mtp_lane, the collective slab's dedicated MTP lane adapter (mtp-colllane-1011, 2026-10-10;
RTL rtl/dsrom_sys/s81_ph/coll/dsfd_coll_mtp_lane.sv).

Placement in the slab (physical/s81_ph_views/collective/composition_split3cr_mtpl.json): a new top row of the slab, the
MTP lane tile u_ml (dsfd_coll_lane_w, contract_split3 outline 345.6 x 340.2, R0, die pins rx / tx / tf on its W face =
the slab's W edge, as lanes W0..W3) and this adapter u_ma abutting its E face, same outline.
  W face  lo_* / li_* / f_lflt at EXACTLY the y of the lane tile's E-face lo / li / flt pins (abutment, M4)
  N face  the slab's N edge: the sequencer bus from the hub chain (f_tv / f_td / t_tg / f_sv / f_sd / t_sg / f_acc,
          generator buses mtp -> collective 648 and collective -> mtp 2) on the W half, and the received streams to this
          die's consumers (t_rtv / t_rtd / f_rtg / t_rsv / t_rsd / f_rsg / t_racc) on the E half; M5, pitch 3 tracks
  S face  ck / rs (the slab's stream clock / reset, as the other tiles)
Logic (yosys-free estimate): 2 x 20-deep receivers (512 + 77 b), 64 x 512 token buffer, 16 x 77 seed buffer, 8 + 2 x 553
landing, credit / arbiter state: ~52k flops, ~35k um2 cells -> ~30 % of the 117.6k um2 outline (rule <= 55-60 %).

    python3 tools/s81_ph/s81_ph_mtp_lane_plan.py  -> physical/s81_ph_views/ports/contract/dsfd_coll_mtp_lane/{ports.json,
                                                    io_place.tcl, ports.svh}, physical/s81_ph_views/specs/dsfd_coll_mtp_lane.json
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/s81_ph'))
import s81_ph_tiles_plan as TP  # noqa: E402

MASTER = 'dsfd_coll_mtp_lane'
W, H = 345.6, 340.2
FLIT, SW, AW = 512, 77, 57
LANE = ROOT / 'physical/s81_ph_views/ports/contract_split3/dsfd_coll_lane_w/ports.json'
SPEC = dict(master=MASTER, w_um=W, h_um=H, domain='stream_1p2',
            note='dedicated MTP lane adapter: W = the MTP lane tile (abutting, lo/li credit seams + lane faults), '
                 'N = sequencer bus in (W half) + received streams out (E half), M5, S = clock / reset',
            ports=[['f_tv', 1, 'input', 'N', 'M5', 1, 0.01], ['f_td', FLIT, 'input', 'N', 'M5', 3, 0.12],
                   ['t_tg', 1, 'output', 'N', 'M5', 1, 0.235],
                   ['f_sv', 1, 'input', 'N', 'M5', 1, 0.24], ['f_sd', SW, 'input', 'N', 'M5', 3, 0.265],
                   ['t_sg', 1, 'output', 'N', 'M5', 1, 0.29], ['f_acc', AW, 'input', 'N', 'M5', 3, 0.315],
                   ['t_rtv', 1, 'output', 'N', 'M5', 1, 0.50], ['t_rtd', FLIT, 'output', 'N', 'M5', 3, 0.61],
                   ['f_rtg', 1, 'input', 'N', 'M5', 1, 0.725],
                   ['t_rsv', 1, 'output', 'N', 'M5', 1, 0.73], ['t_rsd', SW, 'output', 'N', 'M5', 3, 0.755],
                   ['f_rsg', 1, 'input', 'N', 'M5', 1, 0.78], ['t_racc', AW, 'output', 'N', 'M5', 3, 0.805],
                   ['ck', 1, 'input', 'S', 'M5', 1, 0.48], ['rs', 1, 'input', 'S', 'M5', 1, 0.50]])
# W face: mirror of the lane tile's E face (lane port -> adapter port, adapter direction)
ABUT = (('lo_v', 'lo_v', 'output'), ('lo_r', 'lo_r', 'input'), ('lo_d', 'lo_d', 'output'),
        ('li_v', 'li_v', 'input'), ('li_r', 'li_r', 'output'), ('li_d', 'li_d', 'input'), ('flt', 'f_lflt', 'input'))


# P2 variant masters (draft die A): same outline and W-face abutment, die-side ports on the N face
P2SPECS = [dict(master='dsfd_coll_p2_lane_pa', w_um=W, h_um=H, domain='stream_1p2',
                note='P2 primary-lane adapter: W = the W4 lane tile (abutting), N = dsfd_coll_p2_ep (row out of it, start into it) '
                     '+ the P2 core events, S = clock / reset',
                ports=[['x_v', 1, 'input', 'N', 'M5', 1, 0.01], ['x_d', 594, 'input', 'N', 'M5', 3, 0.15],
                       ['x_r', 1, 'output', 'N', 'M5', 1, 0.30], ['x_ev', 3, 'input', 'N', 'M5', 2, 0.32],
                       ['r_v', 1, 'output', 'N', 'M5', 1, 0.50], ['r_d', 101, 'output', 'N', 'M5', 3, 0.55],
                       ['r_r', 1, 'input', 'N', 'M5', 1, 0.60], ['r_ev', 1, 'output', 'N', 'M5', 1, 0.62],
                       ['t_flt', 1, 'output', 'N', 'M5', 1, 0.64],
                       ['ck', 1, 'input', 'S', 'M5', 1, 0.48], ['rs', 1, 'input', 'S', 'M5', 1, 0.50]]),
           dict(master='dsfd_coll_p2_lane_ba', w_um=W, h_um=H, domain='stream_1p2', orients=['MY'],
                note='P2 die-B-lane adapter (placed MY beside the mirrored E4 lane tile): W (local) = the lane tile, '
                     'N = lane-1 words to dsfd_coll_p2_ep, S = clock / reset',
                ports=[['r_v', 1, 'output', 'N', 'M5', 1, 0.01], ['r_d', 604, 'output', 'N', 'M5', 3, 0.15],
                       ['r_r', 1, 'input', 'N', 'M5', 1, 0.30], ['t_flt', 1, 'output', 'N', 'M5', 1, 0.32],
                       ['ck', 1, 'input', 'S', 'M5', 1, 0.48], ['rs', 1, 'input', 'S', 'M5', 1, 0.50]])]


def emit(spec):
    ports = TP.plan(spec)
    lane = json.loads(LANE.read_text())
    for lp, ap, d in ABUT:
        src = lane['ports'][lp]
        pins = [[nm.replace(lp, ap, 1), ly, 0.0, y0, round(x1 - x0, 4), y1] for nm, ly, x0, y0, x1, y1 in src['pins']]
        ports[ap] = dict(bits=src['bits'], layer=src['layer'], pins=pins, direction=d, face='W')
    sp = dict(spec, ports=spec['ports'] + [[ap, lane['ports'][lp]['bits'], d, 'W', 'M4', 'lane E-face y'] for lp, ap, d in ABUT])
    rec = TP.write(spec['master'], W, H, spec['domain'], ports, sp)
    rec['generator'] = dict(file='tools/s81_ph/s81_ph_mtp_lane_plan.py', lane_contract=str(LANE.relative_to(ROOT)))
    d = ROOT / 'physical/s81_ph_views/ports/contract' / spec['master']
    (d / 'ports.json').write_text(json.dumps(rec, indent=0) + '\n')
    (d / 'io_place.tcl').write_text((d / 'io_place.tcl').read_text().replace('tools/s81_ph/s81_ph_tiles_plan.py',
                                                                             'tools/s81_ph/s81_ph_mtp_lane_plan.py'))
    print(spec['master'], sum(len(p['pins']) for p in ports.values()))


def main():
    for sp in P2SPECS:
        emit(sp)
    ports = TP.plan(SPEC)
    lane = json.loads(LANE.read_text())
    assert abs(lane['h_um'] - H) < 1e-6, lane['h_um']
    for lp, ap, d in ABUT:
        src = lane['ports'][lp]
        pins = []
        for nm, ly, x0, y0, x1, y1 in src['pins']:
            assert abs(x1 - lane['w_um']) < 1e-6, (lp, x1)              # the lane's E face
            pins.append([nm.replace(lp, ap, 1), ly, 0.0, y0, round(x1 - x0, 4), y1])
        ports[ap] = dict(bits=src['bits'], layer=src['layer'], pins=pins, direction=d, face='W')
    spec = dict(SPEC, ports=SPEC['ports'] + [[ap, lane['ports'][lp]['bits'], d, 'W', 'M4', 'lane E-face y']
                                              for lp, ap, d in ABUT])
    rec = TP.write(MASTER, W, H, SPEC['domain'], ports, spec)
    rec['generator'] = dict(file='tools/s81_ph/s81_ph_mtp_lane_plan.py', lane_contract=str(LANE.relative_to(ROOT)))
    d = ROOT / 'physical/s81_ph_views/ports/contract' / MASTER
    (d / 'ports.json').write_text(json.dumps(rec, indent=0) + '\n')
    (d / 'io_place.tcl').write_text((d / 'io_place.tcl').read_text().replace('tools/s81_ph/s81_ph_tiles_plan.py',
                                                                             'tools/s81_ph/s81_ph_mtp_lane_plan.py'))
    print(json.dumps(dict(master=MASTER, w=W, h=H, pins=sum(len(p['pins']) for p in ports.values())), indent=1))


if __name__ == '__main__':
    main()
