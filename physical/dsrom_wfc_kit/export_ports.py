#!/usr/bin/env python3
"""Die-pin views of the WFC kit slab masters (dsfd_wfc_stg on layer1kit, dsfd_wfc_src on layer1srckit) from the
S81 recipes (tools/s81/s81_dies_recipe.py), in the s81_ph_views ports format (ports.json / io_place.tcl / ports.svh)
under physical/s81_ph_views/ports/<recipe>/<master>/ -- the pin contract the kit route (route_view.sh) honours."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'tools/s81'), str(ROOT / 'tools/s81_ph')]
import s81_dies_recipe as RC
import s81_ph_views as V
import dsrom_s81_fulldie as G
for rec_name, master in (('layer1kit', 'dsfd_wfc_stg'), ('layer1srckit', 'dsfd_wfc_src')):
    m = RC.build(RC.recipes()[rec_name]['opts'])
    rec = V.records(G, m, rec_name, str(ROOT / 'tools/dsrom_s81_fulldie.py'), [master])[master]
    rec['recipe'] = rec_name
    d = ROOT / 'physical/s81_ph_views/ports' / rec_name / master
    d.mkdir(parents=True, exist_ok=True)
    (d / 'ports.json').write_text(json.dumps(rec, indent=0) + '\n')
    (d / 'io_place.tcl').write_text(V.io_tcl(rec))
    (d / 'ports.svh').write_text(V.svh(rec))
    print(rec_name, master, rec['w_um'], rec['h_um'], {p: (v['direction'], v['bits'], v['face']) for p, v in rec['ports'].items()})
