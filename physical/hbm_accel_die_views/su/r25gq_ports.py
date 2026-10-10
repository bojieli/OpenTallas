#!/usr/bin/env python3
"""[su] hbm-phys-1010: provisional R25GQ hfd_su port contract (lead decision 10-10: route before the R25GQ die net build).

The R25GPHT4 wake contract's port list and widths, unchanged, at the R25GQ slot (2016.144 x 2808 um, tools/
hbm_accel_die_fp.py preset r25gq).  Faces follow the R25GQ adjacency of hb_su_SW (R0): the spine (router / quant /
hgi_vm / cmdproc / coll, the VM lane-group bus and the hub ports) is EAST, hfd_sfu now abuts NORTH (it was W in
R25GPHT4), the SM rows stay SOUTH, the attention / clock / wake ports stay WEST.  Per face the ports keep their
R25GPHT4 order; every pin is on the 0.048-um track grid at a 0.192-um pitch (the R25GPHT4 spacing), each port
contiguous, the face's ports spread with equal gaps.  When the die net build moves a pin, the quarter is re-routed.
  r25gq_ports.py <r25gpht4 ports.json> <out dir>   -> <out>/ports.json, <out>/io_place.tcl
"""
import json, sys
from pathlib import Path

W, H, PITCH, G, DEPTH, THICK = 2016.144, 2808.0, 0.192, 0.048, 0.192, 0.024
FACE = {'f_sfu': 'N', 't_sfu': 'N'}          # R25GQ: hfd_sfu directly north of the SU slot
EDGE = 20.0                                   # keep 20 um of each face corner free


def snap(v):
    return round(round(v / G) * G, 3)


def main(src, out):
    p = json.loads(Path(src).read_text())
    ports = p['ports']
    for n, f in FACE.items():
        ports[n]['face'], ports[n]['layer'] = f, 'M5'
    face = {}
    for n, v in ports.items():
        old = v['pins']
        along = (sum(q[3] + q[5] for q in old) if v['face'] in 'EW' else sum(q[2] + q[4] for q in old)) / (2 * len(old))
        face.setdefault(v['face'], []).append((v['face'] in 'NS' and n in FACE and -1 or along, n))
    for f, lst in face.items():
        lst.sort()
        L = (H if f in 'EW' else W) - 2 * EDGE
        need = sum(ports[n]['bits'] for _, n in lst) * PITCH
        assert need <= L, (f, need, L)
        gap = (L - need) / (len(lst) + 1)
        pos = EDGE
        for _, n in lst:
            pos += gap
            pins = []
            for b in range(ports[n]['bits']):
                c = snap(pos + b * PITCH)
                nm = f'{n}[{b}]'
                if f == 'W':
                    pins.append([nm, 'M4', 0.0, c, DEPTH, round(c + THICK, 3)])
                elif f == 'E':
                    pins.append([nm, 'M4', round(W - DEPTH, 3), c, W, round(c + THICK, 3)])
                elif f == 'S':
                    pins.append([nm, 'M5', c, 0.0, round(c + THICK, 3), DEPTH])
                else:
                    pins.append([nm, 'M5', c, round(H - DEPTH, 3), round(c + THICK, 3), H])
            ports[n]['pins'] = pins
            pos += ports[n]['bits'] * PITCH
    p.update(w_um=W, h_um=H, note='R25GQ provisional: R25GPHT4 ports at the R25GQ slot, faces from R25GQ adjacency '
             '(physical/hbm_accel_die_views/su/r25gq_ports.py); re-route when the die net build moves pins')
    o = Path(out)
    o.mkdir(parents=True, exist_ok=True)
    (o / 'ports.json').write_text(json.dumps(p, indent=1))
    tcl = ['# hfd_su R25GQ provisional die pins (physical/hbm_accel_die_views/su/r25gq_ports.py)']
    for n in sorted(ports):
        for nm, ly, x0, y0, x1, y1 in ports[n]['pins']:
            tcl.append(f'place_pin -pin_name {{{nm}}} -layer {ly} -location {{{(x0 + x1) / 2:.4f} {(y0 + y1) / 2:.4f}}} '
                       f'-pin_size {{{x1 - x0:.4f} {y1 - y0:.4f}}}')
    (o / 'io_place.tcl').write_text('\n'.join(tcl) + '\n')
    print({f: [n for _, n in l] for f, l in face.items()})


if __name__ == '__main__':
    main(*sys.argv[1:])
