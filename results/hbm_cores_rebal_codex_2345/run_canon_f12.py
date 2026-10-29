#!/usr/bin/env python3
"""Opt-in same-cycle f12 arithmetic profile for the existing C24 canonical lane kit.
Usage: run_canon_f12.py WT FIXES <gen_core_kit_hbm arguments>.
The original file profile remains the default everywhere else.
"""
import json,sys,subprocess
from pathlib import Path
wt,fix=map(Path,sys.argv[1:3]);args=sys.argv[3:]
sys.path.insert(0,str(wt/'physical/die_plan/hbm_arch_cores'))
import gen_core_kit_hbm as G
m=args[args.index('--view')+1].split('@')[0]
member={'ot_hbm_su_static_pgslice_lg__lanes__canon_cf1e77':'ot_hbm_su_static_pgslice_lg__lanes0_3__587.52x933.12','ot_hbm_su_static_pgslice_lg__lanes_plain__canon_663526':'ot_hbm_su_static_pgslice_lg__lanes_plain0_3__440.64x457.92'}
r=dict(G.load_recipes()[member[m]])
old='rtl/hdc/ot_hdc_fastfp_lat.sv';new='rtl/hdc/ot_hdc_fastfp_lat_c12.sv';f12='rtl/hdc/ot_hdc_fp32_f12.sv';add6='rtl/hdc/v41x/ot_dsrom_su_add6.sv'
assert r['files'].count(old)==1
r['files']=[new if f==old else f for f in r['files']]
for f in [f12,add6]:
 if f not in r['files']:r['files'].append(f)
sha=subprocess.check_output(['git','-C',str(wt),'rev-parse','HEAD'],text=True).strip()
r['files_at']=dict(r.get('files_at',{}))
for f in [new,f12,add6]:r['files_at'][f]=sha
r['alias_of']=member[m]
r['alias_note']='C24 canonical lane with same-cycle c12/f12 arithmetic profile; MLAT5/ALAT4/WCOPY1 unchanged'
sys.argv=['gen_core_kit_hbm.py']+args+['--recipe-key',m,'--wrapper',str(fix/'canon_wrappers'/f'{m}.sv')]
G.main(recipe_overrides={m:r})
