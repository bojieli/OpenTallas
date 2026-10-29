#!/usr/bin/env python3
"""Generate exactly one current-C25 fullcanon5/4/WCOPY1 candidate kit. No shared default is modified."""
import sys,json,subprocess
from pathlib import Path
W,R,P,OUT=map(Path,sys.argv[1:5]);M='ot_hbm_su_static_pgslice_lg__lanes__canon_cf1e77'
sys.path.insert(0,str(W/'physical/die_plan/hbm_arch_cores'));sys.path.insert(0,str(W/'tools/die_plan'))
import gen_core_kit_hbm as G,master_plan as MP
# Use the same source-listed family recipe, with the existing f12 arithmetic profile at explicit5/4 cycles.
rec=dict(G.load_recipes()['ot_hbm_su_static_pgslice_lg__lanes0_3__587.52x933.12'])
old='rtl/hdc/ot_hdc_fastfp_lat.sv';assert rec['files'].count(old)==1
rec['files']=['rtl/hdc/ot_hdc_fastfp_lat_c12.sv' if f==old else f for f in rec['files']]
for f in ['rtl/hdc/ot_hdc_fp32_f12.sv','rtl/hdc/v41x/ot_dsrom_su_add6.sv']:
 if f not in rec['files']:rec['files'].append(f)
sha=subprocess.check_output(['git','-C',str(W),'rev-parse','HEAD'],text=True).strip();rec['source_commit']=sha;rec['read_at_commit']=True
rec['alias_of']='ot_hbm_su_static_pgslice_lg__lanes0_3__587.52x933.12';rec['alias_note']='Current C25 fullcanon5/4/WCOPY1 candidate, same24 source-listed SRAMs, scalar same-tap clock aliases'
# Planned read_data register banks are existing RTL state, no new data edge. Append their explicit geometry guides.
orig=G.relay_reg_guide_spec;eg=json.load(open(R/'estimate.json'));reads=json.load(open(R/'read_guides.json'))
def guided(*a,**kw):
 out=orig(*a,**kw)
 assert out==eg['write_relays'],'write guide geometry changed from reviewed estimate'
 return out+reads
G.relay_reg_guide_spec=guided
# Public view and slice generators read only this shadow candidate, never the die owner's live plan.
OUT.mkdir(parents=True,exist_ok=True);V=OUT/'views.json';S=OUT/'slices';K=OUT/'kits'
subprocess.run([sys.executable,str(W/'physical/die_plan/hbm_arch_cores/views_b2r2.py'),'--plan',str(P/'die_plan.json'),'--out',str(V)],check=True)
subprocess.run([sys.executable,str(W/'results/die_hbm_kits_1027/mk_c20.py'),str(P),str(V),str(S),str(K),str(W),M,'--islands-only','--ft-pin-dx-um','1.08'],check=True)
sl=json.load(open(S/f'{M}.json'));ds=eg['drivers'];assert len(sl['pushdown']['islands'])==len(ds)
for i,d in enumerate(sl['pushdown']['islands']):
 # The root entry is taken from exact current clock_entries380.136/362.88, rather than the old report centre.
 dr=list(ds[i]['driver_rect_um'])
 if i==0:
  cx,cy=d['centre_um'];dr=[round(cx-1.08,3),round(cy-1.08,3),round(cx+1.08,3),round(cy+1.08,3)]
 driver=d['driver'];span=driver.get('drive_len_um')
 if span is None:
  import re
  span=float(re.search(r'driven length ([0-9.]+) um',driver['basis']).group(1))
 dnew=MP.pushdown_island(i,d['rect_um'],d['centre_um'],d['role'],span,len(sl['pushdown']['islands'])-1 if i==0 else 0,pin_dx_um=1.08,driver_rect=dr)
 sl['pushdown']['islands'][i]=dnew
json.dump(sl,open(S/f'{M}.json','w'),indent=1)
v=next(v for v in json.load(open(V))['view_list'] if v['module']==M)
sys.argv=['gen_core_kit_hbm.py','--views',str(V),'--view',v['view'],'--out',str(K),'--master-slice',str(S),'--trial','--tag','_c25c_m5a4w1_f12','--recipe-key',M,'--wrapper',str(R/'wrappers'/f'{M}.sv'),'--macro-placement',str(R/'macros.json'),'--macro-inst-fmt','{k}','--macro-reg-guide','g_wcopy','--macro-reg-guide-um','10','--relay-reg-guide',str(R/'relay_guides.json')]
G.main(recipe_overrides={M:rec})
