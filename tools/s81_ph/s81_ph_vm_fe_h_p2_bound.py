#!/usr/bin/env python3
"""claude s81-grpA r3 (2026-10-14): die P2 measurement for the VM FE parent: E-W necessary cut bound with the 10 landing lanes
moved OUT of the FE slot (5 W + 5 E), single drain fld vs a two-level drain (one pre-mux per side), at the v16 (695.52) and v18
(889.92) FE heights.  Uses the B8 bound model (s81_ph_vm_fe_h_ew_bound.py) unchanged; only the lane positions / premux differ."""
import importlib.util, json, sys
import numpy as np
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sp = importlib.util.spec_from_file_location('ew', ROOT / 'tools/s81_ph/s81_ph_vm_fe_h_ew_bound.py')
ew = importlib.util.module_from_spec(sp); sp.loader.exec_module(ew)
out = []
for Hh in (695.52, 889.92):
    ew.H = Hh
    for tag, premux in (('P2 single drain', None), ('P2 two-level drain (pre-mux at each edge)', 'edge')):
        best = None
        for fld in np.arange(120, 1410, 27.0):
            for fcn in (560.0, 806.0, 980.0):
                for fcc in (300.0, 560.0, 1100.0):
                    for fcw in (300.0, 980.0, 1200.0):
                        cen = {'fld': float(fld), 'fcn': fcn, 'fcc': fcc, 'fcw': fcw}
                        # lanes outside the slot: W lanes face x=0 (mirrored: face at x0+LW = 0), E lanes face x=W (x0 = W)
                        lanes = [(-ew.LW, True)] * 5 + [(ew.W, False)] * 5
                        pm = [0.0] * 5 + [ew.W] * 5 if premux else None
                        cr = [(cen['fld'] - 86.4, cen['fld'] + 86.4, 69.12, 'leaf'), (cen['fcn'] - 120, cen['fcn'] + 120, 51.84, 'leaf'),
                              (cen['fcc'] - 90.7, cen['fcc'] + 90.7, 112.32, 'leaf'), (cen['fcw'] - 75.6, cen['fcw'] + 75.6, 38.88, 'leaf')]
                        D = ew.demand(0.0, lanes, cen, premux=pm); tot = sum(D.values())
                        r = ew.base_rects(0.0) + cr + [(350.0, 1170.0, 64.8, 'leaf')]
                        S = ew.supply(r); ratio = tot / S; i = int(ratio.argmax())
                        if best is None or ratio[i] < best[0]:
                            best = (float(ratio[i]), float(ew.XS[i]), {k: int(v[i]) for k, v in D.items()}, int(S[i]), cen, int((ratio > 0.6).sum()))
        rec = {'height': Hh, 'case': tag, 'bound': round(best[0], 3), 'worst_x': best[1], 'demand': best[2], 'supply': best[3], 'centres': best[4], 'cuts_over_0p60': best[5]}
        print(json.dumps(rec)); out.append(rec)
    ew.H = Hh
    cen = {'fld': 760.0, 'fcn': 806.0, 'fcc': 560.0, 'fcw': 980.0}
    cr = [(cen['fld'] - 86.4, cen['fld'] + 86.4, 69.12, 'leaf'), (cen['fcn'] - 120, cen['fcn'] + 120, 51.84, 'leaf'),
          (cen['fcc'] - 90.7, cen['fcc'] + 90.7, 112.32, 'leaf'), (cen['fcw'] - 75.6, cen['fcw'] + 75.6, 38.88, 'leaf')]
    print('H', Hh, 'no-lane (returns from above fld):', round(ew.report('', 0.0, [], cen, cr, show=False)[0], 3))
frozen = []
for dh in (0.0, 194.4):
    for pmx in (False, True):
        r = ew.case(f'frozen structure (lanes in slot), height {695.52 + dh:.2f}' + (', two-level drain' if pmx else ''), pm=pmx, dh=dh)
        frozen.append({k: r[k] for k in ('case', 'height_um', 'bound', 'worst_cut_x', 'demand_bits', 'supply_tracks', 'cuts_over_0p60')})
(ROOT / 'results/arch/s81_vm_fe_h_p2_bound_1014.json').write_text(json.dumps({'schema': 'opentallas.s81_vm_fe_h.p2_bound.v1', 'agent': 'claude s81-grpA r3', 'tool': 'tools/s81_ph/s81_ph_vm_fe_h_p2_bound.py', 'limit': 0.60, 'cases': out, 'frozen_cases': frozen, 'reading': 'E-W NECESSARY condition (demand lower bound / supply upper bound, worst vertical cut, best fld/fcn/fcc/fcw centre on a grid) with the 10 landing lanes OUTSIDE the FE slot (5 on the W face, 5 on the E face) returning into fld; <= 0.60 is NOT a pass (pin access, reach, local windows not in it), > 0.60 = this structure cannot pass. Frozen structure (lanes inside the slot) best found 0.653 at 695.52 (s81_vm_fe_h_ew_bound_1013).'}, indent=1) + '\n')
