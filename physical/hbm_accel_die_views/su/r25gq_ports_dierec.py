#!/usr/bin/env python3
"""[su] R25GQ hfd_su port contract from the die record (ports_r25gqn/hfd_su, tools/hbm_die_views.py --variant r25gqn):
every die pin at its die-record position (t_su / f_coll 620 with del_obase, the full-width lgW client tap from the
abutting station bank hb_stn_lgW_su: lead 10-10, SU = lgW client slot 0), PLUS the quarter-local straps of the provisional contract (qid E, cg_en W) at free
spots of their faces.
  r25gq_ports_dierec.py <die ports.json> <old contract ports.json> <out dir>"""
import json, re, sys
from pathlib import Path

die, old, out = sys.argv[1:4]
d = json.loads(Path(die).read_text())
o = json.loads(Path(old).read_text())
ports = dict(d['ports'])     # incl. the lgW client tap (f_lgW_rdn / f_lgW_wdn in, t_lgW_rup / t_lgW_wup out: the station bank abuts the E face)
W, H = d['w_um'], d['h_um']
for name in ('qid', 'cg_en'):
    v = dict(o['ports'][name])
    f = v['face']
    used = sorted(((p[3] + p[5]) / 2 if f in 'EW' else (p[2] + p[4]) / 2) for q in ports.values() if q['face'] == f for p in q['pins'])
    lim = H if f in 'EW' else W
    # the largest free gap on the face, its centre
    pts = [20.0] + used + [lim - 20.0]
    a, b = max(zip(pts, pts[1:]), key=lambda t: t[1] - t[0])
    c = round(round(((a + b) / 2) / 0.048) * 0.048 + 0.012, 3)
    pins = []
    for i in range(v['bits']):
        pc = round(c + 0.192 * i, 3)
        if f == 'E':
            pins.append([f'{name}[{i}]', 'M4', round(W - 0.192, 3), round(pc - 0.012, 3), W, round(pc + 0.012, 3)])
        elif f == 'W':
            pins.append([f'{name}[{i}]', 'M4', 0.0, round(pc - 0.012, 3), 0.192, round(pc + 0.012, 3)])
        else:
            raise SystemExit(f'strap face {f}')
    v.update(pins=pins, layer='M4')
    ports[name] = v
rec = dict(d, ports=ports, note='R25GQ hfd_su contract from the r25gqn die record (r25gq_ports_dierec.py): incl. the '
           'lgW client tap; qid / cg_en quarter straps added')
Path(out).mkdir(parents=True, exist_ok=True)
(Path(out) / 'ports.json').write_text(json.dumps(rec, indent=0) + '\n')
L = ['# hfd_su R25GQ contract from the r25gqn die record (r25gq_ports_dierec.py)']
for p in sorted(ports):
    for nm, ly, x0, y0, x1, y1 in ports[p]['pins']:
        L.append(f'place_pin -pin_name {{{nm}}} -layer {ly} -location {{{(x0 + x1) / 2:.4f} {(y0 + y1) / 2:.4f}}} '
                 f'-pin_size {{{x1 - x0:.4f} {y1 - y0:.4f}}}')
(Path(out) / 'io_place.tcl').write_text('\n'.join(L) + '\n')
print(json.dumps({k: (v['bits'], v['face']) for k, v in ports.items() if not k.startswith('ck')}))
