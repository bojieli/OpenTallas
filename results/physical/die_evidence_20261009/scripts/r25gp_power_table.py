#!/usr/bin/env python3
"""Tabulate the R25GP die's assumed power by kind and by master (tools/hbm_accel_die_fp.py die_power / inst_power)."""
import json, sys
from collections import defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'tools'))
import hbm_accel_die_fp as F
v = F.variant_arg('r25gp')
m = F.build(v, network_probe=bool(v and v.get('sm_physical_grid')))
rows = defaultdict(lambda: dict(n=0, area_mm2=0.0, w=0.0, kind=None, dens=None, w_um=None, h_um=None, names=[]))
for it in m['insts']:
    r = rows[it.master]
    r['n'] += 1; r['kind'] = it.kind
    r['area_mm2'] += (it.w + F.SHAVE) * (it.h + F.SHAVE) / 1e6
    r['w'] += F.inst_power(it)
    r['dens'] = F.DENS_OVR.get(it.name, F.DENS.get(it.kind, 0.0)) if it.kind not in ('phy', 'link', 'serdes_slab', 'host_slab') else 0.0
    r['w_um'], r['h_um'] = it.w, it.h
    if len(r['names']) < 3: r['names'].append(it.name)
out = dict(die=dict(mm2=m.get('die_mm2'), n_insts=len(m['insts'])), shave_um=F.SHAVE, power=F.die_power(m),
           by_master={k: dict(r, area_mm2=round(r['area_mm2'], 4), w=round(r['w'], 3)) for k, r in
                      sorted(rows.items(), key=lambda kv: -kv[1]['w'])})
json.dump(out, open(sys.argv[1], 'w'), indent=1)
for k, r in out['by_master'].items():
    print(f"{k:48s} {r['kind']:10s} n={r['n']:4d} {r['w_um']:9.2f}x{r['h_um']:9.2f} A={r['area_mm2']:8.3f} d={r['dens']} W={r['w']:.2f}")
print(out['power']['peak_in_phase_w'])
