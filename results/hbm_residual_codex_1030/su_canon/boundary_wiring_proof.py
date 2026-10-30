#!/usr/bin/env python3
"""Exact actual-wrapper graph equality at the unchanged canonical interface.

The canonical arithmetic is the same uninterpreted module on both sides. This
proves every connection for all input values; it is not full-core native LEC.
"""
import argparse,copy,json,pathlib,re,subprocess
M=['ot_hbm_su_static_pgslice_lg__lane_exp__canon_7cd691','ot_hbm_su_static_pgslice_lg__lanes__canon_cf1e77','ot_hbm_su_static_pgslice_lg__lanes_plain__canon_663526']
def graph(m):
 names={}
 for n,net in m['netnames'].items():
  n=n.replace('strap_lane_lane_id','lane_lane_id')
  for i,b in enumerate(net['bits']):
   if isinstance(b,int):names.setdefault(b,set()).add(n+'['+str(i)+']')
 def bits(bs):return [sorted(names[b]) if isinstance(b,int) else b for b in bs]
 return dict(ports={p.replace('strap_lane_lane_id','lane_lane_id'):dict(direction=v['direction'],bits=bits(v['bits'])) for p,v in m['ports'].items()},cells={n:dict(type=c['type'],parameters=c['parameters'],port_directions=c['port_directions'],connections={p:bits(bs) for p,bs in c['connections'].items()}) for n,c in m['cells'].items()})
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('json');ap.add_argument('native_ids');ap.add_argument('out');a=ap.parse_args();D=json.load(open(a.json))['modules'];N=json.load(open(a.native_ids));reports=[]
 for m in M:
  candidate=D[m];ref=D[m+'__native_reference'];mut=D[m+'__wrong_id_mutant']
  assert graph(candidate)==graph(ref),m
  assert graph(candidate)!=graph(mut),(m,'wrong-ID graph mutant survived')
  cells=candidate['cells'];assert set(cells)=={'u_core'},(m,list(cells))
  params=cells['u_core']['parameters'];assert {k:int(v,2) for k,v in params.items()}==dict(ALAT=4,MLAT=4,WCOPY=0),(m,params)
  ids=[r for r in N['rows'] if r['module']==m];killed=0
  for row in ids:
   v=row['declared_value'];bad=v^1
   wrong=[bad] if row['width']==11 else [bad*4+i for i in range(4)]
   assert all(x!=y for x,y in zip(wrong,row['actual_lane_ids']))
   killed+=1
  reports.append(dict(module=m,complete_ports=len(candidate['ports']),port_bits=sum(len(p['bits']) for p in candidate['ports'].values()),canonical_cells=1,canonical_parameters=dict(ALAT=4,MLAT=4,WCOPY=0),all_input_graph_equal=True,wrong_id_graph_mutant_rejected=True,bound_id_cases=len(ids),wrong_bound_id_cases_rejected=killed))
 report=dict(status='ALL_INPUT_BOUNDARY_WIRING_EQUIVALENCE_ONLY_UNADOPTED',native_arithmetic='same unchanged canonical module at verified current parameters; no full-core native LEC claim',bound_cores=N['cores'],native_lane_ids=N['lane_ids'],reports=reports)
 pathlib.Path(a.out).write_text(json.dumps(report,indent=2)+'\n');print('PASS complete actual-wrapper all-input graph lockstep;',N['cores'],'bound ID mutants rejected;',N['lane_ids'],'native IDs preserved')
