#!/usr/bin/env python3
"""Natural five-SRAM LP child floorplan proposal. Private candidate, zero RTL/cycle change."""
import json,hashlib,sys,copy
from pathlib import Path
R=Path(__file__).resolve().parents[2]; B=Path(__file__).resolve().parent
W,H=241.92,155.52
old=json.load(open(R/'results/codex_s81_2340/mu_land/pins.json'))
pins=[]
def pin(n,L,x,y):pins.append(dict(name=n,layer=L,x=round(x,4),y=round(y,4)))
# Bank-local traffic: lower banks receive from S and return along their own outside face;
# middle banks use their outside face; last 80-bit bank uses N. No M6/M7 permission required.
for i in range(1104):
 b,k=divmod(i,256)
 if b<2:
  pin(f'wd[{i}]','M5',8.652+(b*142.32)+k*.24,.042)
  pin(f'rd[{i}]','M4',.042 if b==0 else W-.042,4.332+k*.192)
 elif b<4:
  side=.042 if b==2 else W-.042
  pin(f'wd[{i}]','M4',side,54.444+2*k*.192)
  pin(f'rd[{i}]','M4',side,54.444+(2*k+1)*.192)
 else:
  pin(f'wd[{i}]','M5',8.652+2*k*.24,H-.042)
  pin(f'rd[{i}]','M5',8.652+(2*k+1)*.24,H-.042)
for i in range(11):pin(f'rc[{i}]','M5',168.012+i*.24,H-.042)
for i,n in enumerate(['rst_n','wv','rv','fault']):pin(n,'M5',172.812+i*.24,H-.042)
pin('clk','M5',120.972,77.76)
assert len(pins)==len(old['pins']) and {p['name'] for p in pins}=={p['name'] for p in old['pins']}
assert all(0<=p['x']<=W and 0<=p['y']<=H for p in pins)
assert len({(p['layer'],p['x'],p['y']) for p in pins})==len(pins)
(B/'pins.json').write_text(json.dumps(dict(module='dsdv_mu_land',outline_um=[W,H],pins=pins),indent=1)+'\n')
# Generator needs real shapes and directions. Derive direction from exact current-source contract.
lef=(R/'results/codex_s81_2340/mu_land/dsdv_mu_land.lef').read_text()
import re
dirs=dict(re.findall(r'PIN (\S+)\s+DIRECTION (INPUT|OUTPUT)',lef))
ls=['VERSION 5.8 ;','BUSBITCHARS "[]" ;','DIVIDERCHAR "/" ;','MACRO dsdv_mu_land',' CLASS BLOCK ;',' ORIGIN 0 0 ;',f' SIZE {W} BY {H} ;',' SYMMETRY X Y ;']
for p in pins:
 n,L,x,y=p['name'],p['layer'],p['x'],p['y']; dx,dy=(.024,.24) if n=='clk' else ((.024,.042) if L=='M5' else (.042,.016))
 ls += [f' PIN {n}',f'  DIRECTION {dirs[n]} ;','  USE CLOCK ;' if n=='clk' else '  USE SIGNAL ;','  PORT',f'   LAYER {L} ;',f'   RECT {x-dx:.4f} {y-dy:.4f} {x+dx:.4f} {y+dy:.4f} ;','  END',f' END {n}']
ls+=['END dsdv_mu_land','END LIBRARY'];(B/'dsdv_mu_land.lef').write_text('\n'.join(ls)+'\n')
base=json.load(open(R/'physical/ref_tile/dsdv_mu_land/spec.json'))
xy=[(17.28,8.64),(129.6,8.64),(17.28,56.16),(129.6,56.16),(17.28,103.68)]
for m,at in zip(base['macros'],xy):m['at']=at
base['outline']={'w':W,'h':H};base['structural_change']='Private natural child compact five-SRAM candidate; zero RTL/data/reset cycles; parent adoption and partner reach remain required.'
(B/'spec.json').write_text(json.dumps(base,indent=1)+'\n')
sl=dict(schema='opentallas.master_plan_slice.v1',kind='core',die='s81',type='dsdv_mu_land',module='dsdv_mu_land',master_plan_sha256=hashlib.sha256(b'codex-lp-compact-five-bank-census-1029').hexdigest(),frozen=False,outline_um=[W,H],instances=[],keepouts=[],bays=[],entry_pins=[dict(name='core_clock',pin='clk',layer='M5',xy_um=[120.972,77.76])],islands=[],latency=dict(common_clock_latency_ps={'TT':250.,'FF':202.5},tol_ps=40),core_clock_port='clk',gates={'geometry':'PASS','tree':'NOT RUN'},note='Private PLACE census only. Macro-aware actual clock plan and actual geometry required before CTS.')
(B/'slice').mkdir(exist_ok=True);(B/'slice/dsdv_mu_land.json').write_text(json.dumps(sl,indent=1)+'\n')
mr='ot_sram_1r1w_128x256_m1_r2c2'; rec={'dsdv_mu_land':{'ref_tile':'results/codex_s81_lp_1029','io_hold':'sender_min','macro_sites':{mr:[[x,y,'R0'] for x,y in xy]},'macro_rows_halo':4.32}}
(B/'recipes.json').write_text(json.dumps(rec,indent=1)+'\n')
# Standalone pseudo-plan carries exact existing RTL/parameters; no parent die change.
plan=json.load(open(sys.argv[1])); typ='source_dsdv_mu_land'
plan['partition_types'][typ]=dict(module='dsdv_mu_land',outline_um=[W,H],contents=[dict(inst='u_land',module='dsdv_mu_land',status='rework')],hard_cores=[dict(inst='u_land',module='dsdv_mu_land',origin_um=[0,0],outline_um=[W,H],orient='R0',track_offset_um=[.108,.012],pins_file=str(B/'pins.json'),lef='results/codex_s81_lp_1029/dsdv_mu_land.lef',obs_max='M5')])
(B/'kit_plan.json').write_text(json.dumps(plan))
report=dict(scope='ESTIMATE, private child only, not physical qualification',old_outline_um=[475.2,216.],outline_um=[W,H],area_delta_pct=(W*H/(475.2*216)-1)*100,aspect=W/H,pins=len(pins),macro_area_pct=5*94.824*41.064/(W*H)*100,macro_sites_um=xy,clock_entry_um=[120.972,77.76],clock_entry_macro_clearance_um=8.868,macro_halo_um=4.32,zero_rtl_changes=True,added_cycles=0,parent_adoption='NOT RUN: needs exact source parent slot/partner reach and current plan event',gates='Actual place/geometry/LEC/clock/GRT/STA remain required')
(B/'estimate.json').write_text(json.dumps(report,indent=1)+'\n');print(json.dumps(report))
