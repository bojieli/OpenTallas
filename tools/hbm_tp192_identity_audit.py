#!/usr/bin/env python3
"""Exact context ownership / 20-bit global-ordinal inventory for the TP192 A2P source.
This checks ownership, not arithmetic, physical timing, or end-to-end throughput.
The scheduled RTL bench checks the instantiated arithmetic, selector, payloads and edges.
"""
from __future__ import annotations
import argparse,collections,gzip,hashlib,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
def ownership(tp:int,nq:int,mut:int=0):
 ctx=1<<20;counts=[];seen=bytearray(ctx);duplicates=outside=0
 stride=96 if mut==1 else tp
 for rank in range(tp):
  nk=min(nq*2736,(ctx//(8*tp))*8+min(8,max(0,ctx%(8*tp)-8*rank)));counts.append(nk)
  hw_rank=rank&127 if mut==2 else rank
  for k in range(nk):
   # Independent ownership = cyclic TP-way allocation of eight-key blocks.
   expected=((k//8)*tp+rank)*8+k%8
   # Decomposition performed by the actual score RTL's first_ord / engine / lane fields.
   q,kq=divmod(k,2736);beat,lane=divmod(kq,16);e,l=divmod(lane,4)
   actual=8*stride*(q*342)+8*hw_rank+16*stride*beat+(e//2)*8*stride+(e%2)*4+l
   if actual!=expected:outside+=1
   if actual>=ctx:outside+=1;continue
   if seen[actual]:duplicates+=1
   seen[actual]=1
 return dict(tp=tp,nq=nq,keys=sum(counts),per_rank_counts=dict(collections.Counter(counts)),
             missing=seen.count(0),duplicates=duplicates,ordinal_mismatches=outside,counts=counts,
             maximum_local_keys=max(counts),minimum_local_keys=min(counts),verdict='PASS' if not outside and not duplicates and not seen.count(0) else 'FAIL')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args()
 results={str(tp):ownership(tp,nq) for tp,nq in ((96,4),(192,2))}
 mutants={str(m):ownership(192,2,m) for m in (1,2)}
 assert all(x['verdict']=='PASS' and x['keys']==1<<20 for x in results.values())
 assert all(x['verdict']=='FAIL' and x['duplicates']>0 for x in mutants.values())
 files=['rtl/hbm_accel/index/ot_hbm_idx_score_static.sv','rtl/hbm_accel/index/ot_hbm_idx_parent_static.sv',
        'rtl/hbm_accel/index/ot_hbm_idx_client_static_sw.sv','rtl/hbm_accel/index/ot_hbm_idx_scheduled_static.sv',
        'physical/hbm_generic/argmax18/rtl/ot_hgi_argmax18_m.sv','physical/hbm_generic/argmax18/rtl/ot_hgi_argmax18_value_m.sv',
        'rtl/hbm_accel/generic/ot_hbm_argmax_static.sv','rtl/hbm_accel/generic/ot_hbm_argmax_static_sw_vm.sv',
        'tools/hbm_die_v15/full_die_v16.py','tools/hbm_coll_static/g96_calendar.py']
 d=dict(schema='opentallas.hbm.tp192.identity-audit.v1',results=results,mutants=mutants,
        source_sha256={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files},
        preservation=dict(full_context_keys=1<<20,old=dict(dies=96,SM_per_die=32,stacks_per_die=4,total_SM=3072,total_stacks=384),
                          a2p=dict(dies=192,SM_per_die=16,stacks_per_die=2,total_SM=3072,total_stacks=384)),
        open_gates=['Real scheduled IDX/ARGMAX RTL bench verdicts are required separately.',
                    'COLL g96 compiler still requires actual192-rank/five-rail routegraph and schedule/price.',
                    'Native closures/actual placement reset geometry and end-to-end192-die performance remain unqualified.'])
 pathlib.Path(a.out).parent.mkdir(parents=True,exist_ok=True);pathlib.Path(a.out).write_text(json.dumps(d,indent=2)+'\n')
 print('TP192_IDENTITY_AUDIT PASS context=1048576 ranks=192 counts=128x5464+64x5456 stride/rank mutants rejected')
if __name__=='__main__':main()
