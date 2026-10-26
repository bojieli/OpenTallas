#!/usr/bin/env python3
"""Restore the exact 2740-bit NW index input cohort on a separate lane; never borrow TKM1171 wires."""
import argparse,copy,json,shutil,sys,re,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE));sys.path.insert(0,str(HERE.parents[2]/'tools/die_plan'));sys.path.insert(0,str(HERE.parents[2]))
import schema as S,check as C,cores_b2 as CB
FIELDS=[('u_hb_idx__ctl','cr',274,'hb_vms_SW.cr',274),('u_hb_argmax','cr',274,'hb_vms_SW.cr',0),('u_hb_idx__ctl','index_rq',136,'hb_idx__op_SW.vm_rq',0),('u_hb_idx__ctl','vm_rr',2056,'vmb_SW{bank}.rr4',0)]
def apply(plan):
 t=plan['partition_types'];assert 'q_b112_nw'not in t
 t['q_b112_nw']=copy.deepcopy(t['q_b112']);next(p for p in plan['partitions'] if p['name']=='NW_b112')['type']='q_b112_nw'
 for tn,b,d in [('q_hub_nw','L156_o','out'),('root','L156_i','in'),('q_b112_nw','L156x1_i','in'),('q_b112_nw','L156x1_o','out')]:t[tn]['buses'].append(dict(name=b,dir=d,width=2740,kind='data'))
 t['q_b112_nw']['ft_slots'].append(dict(name='L156x1',in_face='S',out_face='E',width=2740,stations=6))
 plan['ports'] += [dict(id='L156_0',src=dict(part='NW_hub',bus='L156_o'),dst=dict(part='NW_b112',bus='L156x1_i'),width=2740,kind='data',face='N',layers=['M7','M5'],window_um=[12441.6,12931.2]),dict(id='L156_1',src=dict(part='NW_b112',bus='L156x1_o'),dst=dict(part='root',bus='L156_i'),width=2740,kind='data',face='E',layers=['M6','M4'],window_um=[8862.72,9352.32])]
 plan['lanes'].append(dict(id='L156',ports=['L156_0','L156_1'],note='Exact existing NW index replies: cr548/index_rq136/vm_rr2056; separate from TKM L74'))
 P=S.Plan(plan);slot=t['q_b112_nw']['ft_slots'][-1];_,regs,_=C.lane_geometry(P,'L156');slot['regs_um']=[list(p) for p in regs[1:-1]]
 plan['latency']['lanes']['L156']=S.Plan(plan).lane_latency('L156')
 return dict(lane='L156',width=2740,pin_window_um=489.6,pins_per_um=2740/489.6,initial_cycles=plan['latency']['lanes']['L156'],selected_TKM_L74_unchanged=True,source_548_gap='Current NW master has no cr; native SW-client VMS master/profile and real548pins required before binding')
def typed_map(trace):
 out=[];at=0
 for core,port,width,src,lo in FIELDS:
  key=core[2:]+'.'+port;rows=trace[key]['rows'];assert len(rows)==width
  for k,row in enumerate(rows):
   want=(src.format(bank=k//257)+'['+str(k%257)+']') if 'bank'in src else src+'['+str(lo+k)+']'
   if row['dir']!='in' or row['partner']!=want:raise ValueError((key,k,row,want))
   out.append(dict(lane_bit=at+k,root_inst=core,root_port=port,root_bit=k,asbuilt_source=want,asbuilt_stages=row['st']))
  at+=width
 assert at==2740
 return out
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--src',required=True);a.add_argument('--out',required=True);a.add_argument('--trace',required=True);a.add_argument('--pack',action='store_true');x=a.parse_args();src,out=Path(x.src),Path(x.out)
 if out.exists():raise ValueError('fresh output required')
 out.mkdir(parents=True)
 for p in src.iterdir():
  if p.name.startswith(('gates','g0')) or p.name in ('die_plan.json',)or p.suffix in('.log','.exit'):continue
  if p.is_dir():shutil.copytree(p,out/p.name,symlinks=True)
  else:shutil.copy2(p,out/p.name,follow_symlinks=True)
 plan=json.load(open(src/'die_plan.json'));report=apply(plan);report['bit_map']=typed_map(json.load(open(x.trace)))
 report['source_plan_sha256']=hashlib.sha256((src/'die_plan.json').read_bytes()).hexdigest()
 if x.pack:
  import ft_sites
  from tools.die_trial.legal_sites import RowAllocator
  try:report['packing'],_=ft_sites.place(plan,RowAllocator,types=['q_b112_nw'],reach_um=405,margin=.9,max_radius_um=40,avoid_core_routes=True)
  except Exception as e:report['packing_failure']=str(e)
 R=C.Report();report['station_sites']=C.check_station_sites(S.Plan(plan),R);report['findings']=R.items
 report['status']='CANDIDATE_UNBOUND_548_NATIVE_SOURCE_AND_ENDPOINT_STATIONS_PENDING'
 (out/'die_plan.json').write_text(json.dumps(plan,indent=1)+'\n');(out/'idx_lane_report.json').write_text(json.dumps(report,indent=1)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='bit_map'},indent=1))
