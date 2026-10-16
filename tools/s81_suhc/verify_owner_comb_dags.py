#!/usr/bin/env python3
"""Check real cloned combinational cell dependency DAGs, without packed-net aliases.

Native modules and sequential cells are boundaries; this does not inspect their
internal logic and cannot qualify native functional/physical execution.
"""
import argparse,collections,hashlib,json
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--design',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();raw=a.design.read_bytes();d=json.loads(raw);owners=[];total=0
 for n,m in d['modules'].items():
  if not n.startswith('ot_s81_su_hard_owner_'):continue
  comb={k:c for k,c in m['cells'].items() if c['type'].startswith('$') and c['type'] not in ('$dff','$adff')}
  if not comb:continue
  drives={b:k for k,c in comb.items() for p,bs in c['connections'].items() if c['port_directions'][p]=='output' for b in bs if isinstance(b,int)}
  deps={k:{drives[b] for p,bs in c['connections'].items() if c['port_directions'][p]=='input' for b in bs if b in drives} for k,c in comb.items()}
  todo=set(deps);depth={}
  while todo:
   ready=[k for k in todo if deps[k]<=depth.keys()]
   assert ready,('actual combinational cycle',n,sorted(todo))
   for k in ready:depth[k]=1+max((depth[x] for x in deps[k]),default=0)
   todo.difference_update(ready)
  total+=len(comb);owners.append(dict(module=n,cells=len(comb),max_cell_depth=max(depth.values())))
 r=dict(status='PASS',scope='Source bit/cell DAG check of cloned parent combinational logic only; native internals not checked; no functional/physical qualification',comb_cells=total,owners_with_comb=len(owners),max_depth=max(x['max_cell_depth'] for x in owners),source_sha256=hashlib.sha256(raw).hexdigest(),owners=owners)
 a.out.write_text(json.dumps(r,indent=1)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='owners'}))
if __name__=='__main__':main()
