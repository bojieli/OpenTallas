#!/usr/bin/env python3
"""hbm-phys-1010 [sfu] 2026-10-10: a PROPOSED R25GQ pin plan of hfd_sfu (slot 2016.144 x 1095.12, SW instance R0),
for the folded tiled quarter (tools/hbm_hub_quarter_gen.py --quarter sfu --tiled --half-width --fold 3).

R25GQ has no die nets for hfd_sfu yet (results/arch/r25gq_refloorplan_20261010/README: pins come with the network
build), so hbm_die_views.py --variant r25gq ports is empty.  This keeps the r24p port SET (names, widths, directions)
and places it by the R25GQ neighbours: SU is SOUTH of the slot (hb_su_SW top 10,434.96, gap 216 um) -> f_su / t_su on
the S face (M5, 0.192-um pitch, centred); HC is WEST (hb_hc_SW x 8,794.7..10,827.6, overlapping the slot's rows) ->
f_hc / t_hc on the W face (M4, 0.192-um pitch, centred at the tile band); one clock pin ck and rst on the W face.
NOT included: the R25GQ option-A wide VM lane group A (vm_grpA_sfu / vm_grpA_hc, 17,792 b each) -- no port contract
exists for it yet.
    hbm_sfu_r25gq_ports.py --r24p <r24p ports.json> --out <dir>   (writes <dir>/hfd_sfu/ports.json + io_place.tcl)
"""
import argparse, json
from pathlib import Path

W, H = 2016.144, 1095.12
M5X0, M4Y0, TP = 0.012, 0.012, 0.048


def snap(v, off):
    return round(off + round((v - off) / TP) * TP, 4)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--r24p', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--band-y', type=float, default=40.0, help='y of the chain heads / port band (S rows)')
    a = ap.parse_args()
    src = json.loads(Path(a.r24p).read_text())
    P = {}
    # S face: f_su then t_su, M5 vertical pins, 0.192 pitch, centred on the slot
    n = sum(src['ports'][p]['bits'] for p in ('f_su', 't_su'))
    x0 = snap(W / 2 - n * 0.192 / 2, M5X0)
    k = 0
    for p in ('f_su', 't_su'):
        v = dict(src['ports'][p]); pins = []
        for b in range(v['bits']):
            xc = round(x0 + 0.192 * k, 4); k += 1
            pins.append([f'{p}[{b}]', 'M5', round(xc - 0.012, 4), 0.0, round(xc + 0.012, 4), 0.192])
        v.update(layer='M5', pins=pins, face='S'); P[p] = v
    # W face: f_hc then t_hc, M4 horizontal pins, 0.192 pitch, centred at mid height
    n = sum(src['ports'][p]['bits'] for p in ('f_hc', 't_hc'))
    y0 = snap(H / 2 - n * 0.192 / 2, M4Y0)
    k = 0
    for p in ('f_hc', 't_hc'):
        v = dict(src['ports'][p]); pins = []
        for b in range(v['bits']):
            yc = round(y0 + 0.192 * k, 4); k += 1
            pins.append([f'{p}[{b}]', 'M4', 0.0, round(yc - 0.012, 4), 0.192, round(yc + 0.012, 4)])
        v.update(layer='M4', pins=pins, face='W'); P[p] = v
    for p, y in (('ck', snap(a.band_y, M4Y0)), ('rst', snap(a.band_y + 1.92, M4Y0))):
        P[p] = dict(bits=1, layer='M4', pins=[[f'{p}[0]', 'M4', 0.0, round(y - 0.012, 4), 0.192, round(y + 0.012, 4)]],
                    face='W', dir_segments=[[0, 1, 'in']], direction='input')
    rec = dict(master='hfd_sfu', kind='sfu', w_um=W, h_um=H, obs_top=7, instances=4,
               orients=['R0', 'MY', 'MX', 'R180'], inst_names=['hb_sfu_SW', 'hb_sfu_SE', 'hb_sfu_NW', 'hb_sfu_NE'],
               band_xy=[W / 2, a.band_y],
               note='PROPOSED R25GQ pin plan (tools/hbm_sfu_r25gq_ports.py): r24p port set, SU on S, HC on W; '
                    'vm_grpA (17,792 b) not included (no contract)', ports=P)
    d = Path(a.out) / 'hfd_sfu'
    d.mkdir(parents=True, exist_ok=True)
    (d / 'ports.json').write_text(json.dumps(rec, indent=1) + '\n')
    L = ['# hfd_sfu: PROPOSED R25GQ pin plan (tools/hbm_sfu_r25gq_ports.py)']
    for p, v in P.items():
        for nm, ly, xa, ya, xb, yb in v['pins']:
            L.append(f'place_pin -pin_name {{{nm}}} -layer {ly} -location {{{(xa + xb) / 2:.4f} {(ya + yb) / 2:.4f}}} '
                     f'-pin_size {{{xb - xa:.4f} {yb - ya:.4f}}}')
    (d / 'io_place.tcl').write_text('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()
