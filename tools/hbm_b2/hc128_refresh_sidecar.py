#!/usr/bin/env python3
"""Refresh ONLY the HC (bank128/subtree32) entries of a plan's core_conns sidecar.

Takes the direction-aware output of hc128_core_conns.py and replaces, per partition
type, the core_conns entries of the HC hard cores (keys under the HC parent instance).
Every non-HC entry is kept byte-for-byte; those references are NOT qualified here.
Writes the refreshed sidecar plus a receipt with removed/added targets per core port.
"""
import argparse,json,hashlib
from pathlib import Path
HC=('ot_hbm_hc_bank128','ot_hbm_hc_subtree32')
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--plan',required=True,type=Path);ap.add_argument('--base-conns',required=True,type=Path)
ap.add_argument('--directed',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);ap.add_argument('--receipt',required=True,type=Path)
a=ap.parse_args()
plan=json.loads(a.plan.read_text());base=json.loads(a.base_conns.read_text());new=json.loads(a.directed.read_text())
out=json.loads(json.dumps(base));rec=dict(plan_sha256=hashlib.sha256(a.plan.read_bytes()).hexdigest(),base_sha256=hashlib.sha256(a.base_conns.read_bytes()).hexdigest(),directed_sha256=hashlib.sha256(a.directed.read_bytes()).hexdigest(),types={})
for tn,t in plan['partition_types'].items():
 cores=[c['inst'] for c in t.get('hard_cores',[]) if c['module'].startswith(HC)]
 if not cores:continue
 old=base.get(tn,{});nw=new[tn];cs=set(cores)
 assert set(k for k in old if k in cs)==cs==set(k for k in nw if k in cs),tn
 removed=added=0;ports_dropped=[];c2c_after=0
 for inst in cores:
  o=old[inst];n=nw[inst]
  for pn in o:
   if pn not in n:ports_dropped.append(inst+'.'+pn)
  for pn in set(o)|set(n):
   so=set(o.get(pn,()));sn=set(n.get(pn,()));removed+=len(so-sn);added+=len(sn-so)
   c2c_after+=sum(1 for x in sn if x.startswith('core:'))
  out[tn][inst]=n
 nonhc=sorted(k for k in old if k not in cs)
 rec['types'][tn]=dict(hc_cores=len(cores),targets_removed=removed,targets_added=added,ports_dropped=ports_dropped,core_to_core_targets_after=c2c_after,nonhc_entries_kept=len(nonhc))
a.out.write_text(json.dumps(out,indent=1)+'\n')
rec['out_sha256']=hashlib.sha256(a.out.read_bytes()).hexdigest()
nonhc_total=sum(len(v) for tn,v in out.items())-sum(r['hc_cores'] for r in rec['types'].values())
rec['nonhc_entries_total_unqualified']=nonhc_total
a.receipt.write_text(json.dumps(rec,indent=1)+'\n');print(json.dumps(rec['types']));print('nonhc entries kept (not qualified):',nonhc_total)
