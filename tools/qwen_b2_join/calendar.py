#!/usr/bin/env python3
"""Compiler proof for six real BANDF2 producers and native NB6 static result ports.

Includes actual decoder operations and source-specific route padding. Without a
six-path source-bound route profile it reports component calendar only and
refuses native qualification. PC11 uses the separate native59 service.
"""
import argparse,hashlib,json,sys
from pathlib import Path
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tools/qwen_vmwb'))
import wb_calendar as w

def nh_of(split):
 if not 7<=split<=11:raise ValueError('unsupported b2 split')
 return {7:4,8:2,9:1,10:3,11:1}[split]

def group(split,h,j):
 nh=nh_of(split)
 if j>=nh:return None
 if split<=9:return h*(1<<(9-split))+j
 return j if h==0 else None

def compile_op(f,lag=True,route=None):
 ns=nh_of(f['split']);stride=max(f['ts'],8);period=max(8*ns,stride)
 rw={};ed={};end={};caps={}
 offsets=[0]*6
 if route is not None:
  if set(route)!=set(str(i)for i in range(6)):raise ValueError('six actual source route ages required')
  records=[route[str(i)]for i in range(6)]
  for rec in records:
   for key in ('tag_to_capture_edges','tag_to_issue_edges','train_fanout_edges','rb_to_vm_edges'):
    if type(rec.get(key))is not int or rec[key]<0:raise ValueError('missing actual route edge '+key)
  te=[rec['tag_to_capture_edges']-rec['tag_to_issue_edges']-rec['train_fanout_edges']for rec in records]
  if len(set(te))!=1 or te[0]<2:raise ValueError('issuer alignment needs explicit path padding')
  offsets=[rec['tag_to_capture_edges']+rec['rb_to_vm_edges']for rec in records]
 for k in range(8*f['tiles']):
  caps[k]=(k//8)*stride+k%8
  for h in range(6):
   for j in range(ns):
    key=k,h,j;g=group(f['split'],h,j)
    edge=2+(h*ns if lag else 0)+(k//8)*period+(k%8)*ns+j+offsets[h]
    ed[key]=edge
    if g is not None and f['oen']:
     rw[key]=(f['obase']+(k//8)*f['ots']*(3072>>f['split'])+(k%8)*f['ojs']+g*f['ots'])&0xfffff
  end[k]=ed[k,5,ns-1]
 bad=w.conflicts(f,ed,rw)
 for k,cap in caps.items():
  if min(ed[k,h,0]-offsets[h] for h in range(6))<cap+2:bad.append(('emit before capture',k))
  if any(ed[key]>end[k]for key in rw if key[0]<=k):bad.append(('premature end',k))
 # Logical row multisets must exactly match the released layout at every burst.
 old=w.rows(f)
 for k in caps:
  if sorted(v for key,v in old.items()if key[0]==k)!=sorted(v for key,v in rw.items()if key[0]==k):bad.append(('row permutation mismatch',k))
 return dict(slot_count=ns,period=period,real_rows=len(rw),faults=bad,last_end=max(end.values())+2,
             native_route_qualified=False,route_scope='provided route ages need actual physical/source proof'if route else'component only: no die route ages',
             calendar={'.'.join(map(str,key)):value for key,value in ed.items()},rows={'.'.join(map(str,key)):value for key,value in rw.items()})

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--route-profile');a=p.parse_args()
 dec=json.loads(w.DECISION.read_text())['link_handoff']['ops'];program=w.read_program(w.PCS,dec);records={};okay=True
 route=json.loads(Path(a.route_profile).read_text())if a.route_profile else None
 for pc,f in program.items():
  if f['wsrc']:records[pc]={'route':'native59_service_to_vm_ar','b2_serializer_is_production_route':False};continue
  rec=compile_op(f,route=route);old,oldend,_=w.calendar(f,0)
  rec['old3parallel_end']=oldend+2;rec['delta_component_cycles']=rec['last_end']-oldend-2
  rec['first_capture_after_go_historical']=dec[pc]['capture_cycles_after_go'][0]
  okay &=not rec['faults'];records[pc]=rec
 # Broken calendar must collide on actual shipped bank traffic.
 mutants={pc:bool(compile_op(f,lag=False)['faults'])for pc,f in program.items()if not f['wsrc']}
 if not all(mutants.values()):raise ValueError('bank-calendar mutant survived')
 sources=['rtl/qwen_split/qfd_res_train_half_b2.sv','rtl/qwen_split/qfd_res_train_issue_b2.sv','rtl/qwen_sys/vm_nox_20261014/qfd_sp_vector_memory_b2.sv']
 result=dict(status='COMPONENT_CALENDAR_PASS'if okay else'FAIL',native_qualification=False,sources={x:hashlib.sha256((R/x).read_bytes()).hexdigest()for x in sources},ops=records,mutants=mutants,limits=['Actual port row dump not yet cross-checked','Die relays/clock phases/all other VM writers absent until source-bound route profile','No full-layer or token throughput claim'])
 Path(a.out).write_text(json.dumps(result,indent=2)+'\n');print(result['status'],{pc:r.get('delta_component_cycles')for pc,r in records.items()});return 0 if okay else 1
if __name__=='__main__':sys.exit(main())
