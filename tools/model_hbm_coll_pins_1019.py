#!/usr/bin/env python3
"""Exact actual-bound macro identities, lead RC delta, area and track budget."""
from pathlib import Path
import sys,json,hashlib,subprocess
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import check_macro_track_alignment as C

def main():
 out=ROOT/'results/arch/hbm_coll_safephys_1019';out.mkdir(parents=True,exist_ok=True)
 names=['ot_sram_1r1w_128x256_m1_r2c2','ot_sram_1r1w_128x256_m1_r2c2_p192_mir','ot_sram_1r1w_32x128_m1','ot_sram_1r1w_32x128_m1_p192_rc'];r={}
 for n in names:
  p=ROOT/'physical/asap7_memory_macros'/n/(n+'.lef');m=C.parse_lef(p.read_text())[0];cnt={'W':0,'E':0}
  for pin in m['pins']:
   if pin['use'] in ['POWER','GROUND']:continue
   for layer,q in pin['rects']:
    if q[0]==0:cnt['W']+=1
    if q[2]==m['W']:cnt['E']+=1
  r[n]=dict(size_um=[m['W']/1000,m['H']/1000],area_um2=m['W']*m['H']/1e6,contacts=cnt,density_per_face_um={k:v/(m['H']/1000) for k,v in cnt.items()},R0=C.check_placement(m,'R0',43200,43200),R180=C.check_placement(m,'R180',43200,43200),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),pin_geometry=C.audit_macro(m,C.ASAP7_TRACKS_NM,C.ASAP7_LAYERS)['pin_checks'])
 old32='ot_sram_1r1w_32x128_m1_p192';new32=names[3];pre='physical/asap7_memory_macros/'+old32+'/'
 oldlef=subprocess.check_output(['git','show','7a2ff3761:'+pre+old32+'.lef'],cwd=ROOT,text=True)
 newlef=(ROOT/'physical/asap7_memory_macros'/new32/(new32+'.lef')).read_text()
 assert oldlef==newlef.replace(new32,old32),'Existing39.960physicalgeometry must remain identical apart from master identity'
 prior=json.loads(subprocess.check_output(['git','show','7a2ff3761:'+pre+old32+'.json'],cwd=ROOT,text=True));fresh=json.loads((ROOT/'physical/asap7_memory_macros'/new32/(new32+'.json')).read_text())
 delta={c:{k:fresh['timing'][c][k]-prior['timing'][c][k] for k in ['clk_to_q_ps','setup_ps','min_period_ps','min_pulse_ps','pin_cap_ff','clk_cap_ff','out_slew_intrinsic_ps','read_energy_fj','write_energy_fj','hold_ps']} for c in ['tt','ss','ff']}
 new=r[names[1]];old=r[names[0]];small=r[new32];oldsmall=r[names[2]]
 for x in [new,small]:
  assert max(x['density_per_face_um'].values())<=6
  assert x['R0']['layers']['M4']['offtrack']==0 and x['R180']['layers']['M4']['offtrack']==0
 v=dict(schema='opentallas.hbm_coll_pin_budget_1019.v1',release='VM_RT74/NLINK1and2/ROWS256 programmeissuer remains6x256x256+4x256x64',macro_census=r,delay_ring_macros={'128x256_p192_mir':2,'32x128_p192_rc':2},new_delay_macro_area_um2=2*new['area_um2']+2*small['area_um2'],original_bound_delay_macro_area_um2=2*old['area_um2']+2*oldsmall['area_um2'],per_leaf_area_delta_um2=2*(new['area_um2']+small['area_um2']-old['area_um2']-oldsmall['area_um2']),repair_contract='128x256 retains2spare rows/2spare columns, singleclock1R1W, same core+behavior+latency;32x128 retainszero repairspares',small_macro_provenance='7a2ff3761152362393140fa3122442935ca3d2ca physicalgeometry unchanged; oldp192 Liberty immutable; distinct_rc complete recalibration',small_macro_exact_extra_lead_um=fresh['area']['macro_height_um']-fresh['area']['core_height_um'],small_macro_timing_delta_vs_7a2=delta,lead_bound='Longest physical M4 contactlead fromcompact core:macroheight-coreheight; length-specific0.38RC+actualcalibrateddriverR*C, not arbitrary delay. No localterminaldriver/repeatedcore was previously modeled.',RTL_bound=True,data_edge_delta=0,compiler_claim='Complete calibrated analytical LEF/PG/contact/RC/Lib/behavioral abstract; no transistorGDS',still_open=['actualASAP7standardcellarea for3335/3433FF shapes','actualnewmacrobehavior+nativebinding','actualexternalpatch/via/PG/DRC escape','floorplan/slot fromactualarea,1band/lattice/reach/reset/clocks/nativeTTsetupFFhold','releaseparentv8 propagation after rootreview'],physical_qualified=False)
 (out/'pin_budget.json').write_text(json.dumps(v,indent=2)+'\n');print(json.dumps({k:v[k] for k in ['new_delay_macro_area_um2','original_bound_delay_macro_area_um2','per_leaf_area_delta_um2','small_macro_exact_extra_lead_um','small_macro_timing_delta_vs_7a2']}))
if __name__=='__main__':main()
