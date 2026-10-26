#!/usr/bin/env python3
"""Construct an explicitly unselected MODE3/syncfault parent geometry proposal. No P&R."""
import argparse,copy,json,pathlib,re
P=argparse.ArgumentParser();P.add_argument('--out',type=pathlib.Path,required=True);a=P.parse_args()
ROOT=pathlib.Path(__file__).resolve().parents[2];a.out.mkdir(parents=True,exist_ok=True)
W,H=457.92,1157.76;HALO=5.4
DIMS={'romleaf':[172.8,110.16],'lsl':[99.792,140.4],'node':[47.52,432.0]}
def kind(c): return 'romleaf' if 'romleaf' in c['view'] else ('node' if 'node' in c['view'] else 'lsl')
def overlaps(b,c):return min(b[2],c[2])>max(b[0],c[0])+1e-7 and min(b[3],c[3])>max(b[1],c[1])+1e-7
def box(c,halo=0):
 x,y=c['at'];w,h=DIMS[kind(c)];return [x-halo,y-halo,x+w+halo,y+h+halo]
def audit(spec,taps):
 out={'macro_overlaps':[],'halo_clearance_failures':[],'clock_taps_in_halos':[],'outside_outline':[]}
 cs=spec['children']
 for i,c in enumerate(cs):
  x,y,x1,y1=box(c)
  if min(x,y)<0 or x1>W or y1>H:out['outside_outline'].append(c['inst'])
  for d in cs[:i]:
   if overlaps(box(c),box(d)):out['macro_overlaps'].append([c['inst'],d['inst']])
   if overlaps(box(c,HALO),box(d,HALO)):out['halo_clearance_failures'].append([c['inst'],d['inst']])
 for t in taps:
  x,y=t['xy']
  for c in cs:
   b=box(c,HALO)
   if overlaps([x-.016,y-.384,x+.016,y+.384],b):out['clock_taps_in_halos'].append([t['name'],c['inst']])
 return out
plans={}
for k in ['nk','nl']:
 src=ROOT/f'tools/qwen_romleaf/a0core/specs/qfd_tile_{k}_a0cv8.json';s=json.loads(src.read_text());t=json.loads((ROOT/f'tools/qwen_romleaf/a0core/a0c8_{k}_taps.json').read_text())['taps'];before=audit(s,t)
 moves=[]
 for c in s['children']:
  if kind(c)=='lsl':
   c['view']='physical/ref_tile/qfd_tile_lsl_sync_fault/views/ot_qwen_tile_lsl_sync_fault'
   c['view_status']='PLANNED ABSENT; requires new SIGNED view, never use/rename FP1 library'
   if abs(c['at'][0]-200.448)<1e-6:
    old=c['at'].copy();c['at'][0]=211.248;moves.append({'inst':c['inst'],'from':old,'to':c['at'].copy(),'why':'10.8um = two5.4um halos between back-to-back LSL columns'})
 for tt in t:
  if (k=='nk' and tt['name']=='ck_t29') or (k=='nl' and tt['name']=='ck_t27'):
   old=tt['xy'].copy();tt['xy'][0]=441.0;moves.append({'pin':tt['name'],'from':old,'to':tt['xy'].copy(),'why':'outside right LSL halo, pin-box clearance0.102um'})
  x,y=tt['xy']
  if any(b[0]<=x<=b[2] and b[1]<=y<=b[3] for b in [box(c,HALO) for c in s['children']]):
   candidates=[]
   for c in s['children']:
    b=box(c,HALO)
    for xx in [b[0]-.24,b[2]+.24]:
     xx=round(xx/.016)*.016
     if 5.4<xx<W-5.4 and not any(bb[0]<=xx<=bb[2] and bb[1]<=y<=bb[3] for bb in [box(d,HALO) for d in s['children']]):candidates.append(xx)
   assert candidates,(k,tt)
   old=tt['xy'].copy();tt['xy'][0]=min(candidates,key=lambda xx:abs(xx-x));moves.append({'pin':tt['name'],'from':old,'to':tt['xy'].copy(),'why':'keep clock pin outside moved middle LSL halo; exact source sink radius still owed'})
  tt['status']='PLANNED template tap; actual ownership/load and child pin compensation NOT MEASURED'
 s['name']=f'qfd_tile_{k}_a0c_m3sync_proposal';s['top']=f'qfd_tile_{k}_a0c_m3sync';s['params']={'G4_ROOTS':1,'REGROOT_MODE':3};s['defines']=[v for v in s['defines'] if v!='OT_QWEN_LSL_FP1']+['OT_QWEN_LSL_SYNC_FAULT']
 # Emit only candidate-private source changes; canonical selected/FP1 sources remain byte-identical.
 private=a.out/'candidate_source';private.mkdir(exist_ok=True)
 top=(ROOT/f'rtl/physical/a0_core/qfd_tile_{k}_a0c.sv').read_text().replace(f'module qfd_tile_{k}_a0c #(',f'module qfd_tile_{k}_a0c_m3sync #(',1)
 (private/f'qfd_tile_{k}_a0c_m3sync.sv').write_text('// UNSELECTED proposal: source transformation only, no recovered physical view credit.\n'+top)
 body=(ROOT/'rtl/physical/a0_rc14_selected_2000/ot_qwen_w12_matvec_land32.sv').read_text()
 needle='`ifdef OT_QWEN_LSL_FP1\n                ot_qwen_tile_lsl_fp1'
 assert needle in body
 body=body.replace(needle,'`ifdef OT_QWEN_LSL_SYNC_FAULT\n                ot_qwen_tile_lsl_sync_fault\n`elsif OT_QWEN_LSL_FP1\n                ot_qwen_tile_lsl_fp1',1)
 (private/'ot_qwen_w12_matvec_land32.sv').write_text(body)
 bb=(ROOT/'rtl/physical/bb/ot_qwen_tile_lsl_fp1_bb.v').read_text().replace('ot_qwen_tile_lsl_fp1','ot_qwen_tile_lsl_sync_fault')
 (private/'ot_qwen_tile_lsl_sync_fault_bb.v').write_text('// UNSELECTED blackbox declaration for a NEW ABSENT master; not a renamed physical view.\n'+bb)
 rel=a.out.relative_to(ROOT).as_posix()
 outsrc=[]
 for source in s['sources']:
  if source.endswith(f'a0_core/qfd_tile_{k}_a0c.sv'):source=f'{rel}/candidate_source/qfd_tile_{k}_a0c_m3sync.sv'
  elif source.endswith('ot_qwen_tile_lsl_fp1_bb.v'):source=f'{rel}/candidate_source/ot_qwen_tile_lsl_sync_fault_bb.v'
  elif source.endswith('a0_rc15_selected_2000/ot_qwen_rom_tile_w12_land32.sv'):source=source.replace('a0_rc15_selected_2000','a0_rc14_selected_2000')
  elif source.endswith('a0_rc14_selected_2000/ot_qwen_w12_matvec_land32.sv'):source=f'{rel}/candidate_source/ot_qwen_w12_matvec_land32.sv'
  outsrc.append(source)
 s['sources']=outsrc
 # Materialize exact proposed tap coordinates in the private pin TCL, keeping all data pins unchanged.
 pins=(ROOT/s['io_tcl']).read_text()
 for tap in t:
  pattern=r'(place_pin -pin_name \{'+re.escape(tap['name'])+r'\} -layer M7 -location \{)[^}]+(\})'
  pins,n=re.subn(pattern,lambda m:m.group(1)+f"{tap['xy'][0]:.6f} {tap['xy'][1]:.6f}"+m.group(2),pins)
  assert n==1,(k,tap['name'],n)
 pinfile=private/f'{k}_pins.tcl';pinfile.write_text('# UNSELECTED MODE3/syncfault planned template pins; all data pins retained.\n'+pins)
 s['io_tcl']=f'{rel}/candidate_source/{k}_pins.tcl'
 s['route']['period_ps']=833;s['route']['hold_margin_ns']=0.015
 s['candidate_only']=True;s['status']='UNSELECTED: owner fault/boot contract, new child views and actual-source placement required'
 s['clock_contract_proposal']={'register_target_ps':{'TT':250,'FF':202.5},'setup_uncertainty_ps':60,'hold_uncertainty_ps':25,'related_pair_skew_gate_ps':80,'balance_window_ps':20,'internal_child_latency':'derive per corner from actual SIGNED source views; historical means are INFO only','signal_layer_cap':'M7','clock_layers':'M6-M7 under existing M7 block cap; reserve actual NDR tracks in combined congestion model','extra_clock_ports':'planned42NK/41NL; not the actual RR39/35 native bridge'}
 s['missing_views']=['ot_qwen_tile_lsl_sync_fault: new physical view absent','ROMleaf: historical TT/FF views require current source/reset/policy requalification; actual endpoint CK metadata needed','NK node: historical nb1 view requires current source/reset/policy and native per-corner clock qualification'] if k=='nk' else ['ot_qwen_tile_lsl_sync_fault: new physical view absent','ROMleaf: historical TT/FF views require current source/reset/policy requalification; actual endpoint CK metadata needed']
 s['readiness_blockers']=['OWNER fault+boot contract ruling','Synchronous wavefront reset delivery and native-pin cohort in actual source kit','New LSL TT/FF833 SIGNED view and exact per-bit LEF clock contract','Actual MODE3 placed per-bit reach/routing capacity; MODE9 R6 coordinates cannot supply it','Planned tap pins materialized + actual sink/load/radius assignment, both-corner GRT-RC compensation','Combined signal+clock GRT0 followed by exhaustive actual hard-child CPPR/STA']
 after=audit(s,t)
 assert all(not v for v in after.values()),after
 plan={'kind':k,'spec':s,'taps':t,'moves':moves,'before_audit':before,'after_audit':after,'corridor':{'x':[200.664,257.256],'y':[16.776,658.44],'width_um':56.592,'status':'RESERVED GEOMETRIC BUDGET ONLY. 1024bit MODE9 cut is historical, not current-MODE3 endpoint evidence. Capacity must deduct PG/NDR/vias/other buses. No added-cycle/route claim.'}}
 (a.out/f'{k}_plan.json').write_text(json.dumps(plan,indent=2)+'\n');plans[k]=plan
(a.out/'SUMMARY.json').write_text(json.dumps({k:{'before':v['before_audit'],'after':v['after_audit'],'moves':v['moves'],'missing_views':v['spec']['missing_views']} for k,v in plans.items()},indent=2)+'\n')
print(json.dumps({k:{'before_failures':sum(map(len,v['before_audit'].values())),'after_failures':sum(map(len,v['after_audit'].values())),'moves':len(v['moves'])} for k,v in plans.items()}))
