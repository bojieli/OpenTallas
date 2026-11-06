#!/usr/bin/env python3
"""Recover only the integer tap-key serialization bug into a fresh capsule."""
import argparse,copy,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import bound_reset_contract as B

def recover(bound,out):
 import reset_tree  # Require the matched emitter dependency before writing a capsule.
 bound=Path(bound);out=Path(out)
 meta=bound.with_suffix('.reset_tree.json');original=meta.read_bytes();r=json.loads(original)
 if r.get('schema')!=B.SCHEMA or r.get('bound_module')!=bound.stem:
  raise ValueError('not the actual emitted source receipt')
 if r.get('bound_rtl_sha256')!=hashlib.sha256(bound.read_bytes()).hexdigest():
  raise ValueError('captured RTL identity changed')
 tree=copy.deepcopy(r['tree'])
 for key in ('tap_depth','tap_roles'):
  if key in tree:
   v=tree[key]
   if not isinstance(v,dict) or any(not isinstance(k,str) or not k.isdecimal() or str(int(k))!=k for k in v):
    raise ValueError('not canonical integer tap-map keys')
   tree[key]={int(k):v for k,v in v.items()}
 legacy=hashlib.sha256(json.dumps(tree,sort_keys=True,separators=(',',':')).encode()).hexdigest()
 if legacy!=r.get('tree_sha256') or B.digest(tree)==legacy:
  raise ValueError('receipt is not exactly the legacy integer-key serialization defect')
 if out.exists():raise ValueError('output must be a new capsule directory')
 out.mkdir(parents=True);new=out/bound.name;new.write_bytes(bound.read_bytes())
 provenance=dict(schema='opentallas.bound_reset_json_recovery.v1',original_receipt_sha256=hashlib.sha256(original).hexdigest(),original_tree_sha256=legacy,original_bound_rtl_sha256=r['bound_rtl_sha256'],original_provenance=r.get('provenance'),scope='Only JSON tap-key identity normalization; exact captured tree and RTL preserved')
 B.emitted(new,r['plan_type'],tree,provenance)
 if new.with_suffix('.reset_tree.tcl').read_bytes()!=bound.with_suffix('.reset_tree.tcl').read_bytes():
  raise ValueError('re-emitted placement Tcl differs from actual original emission')
 result=B.source(new,r['plan_type'],out,Path(__file__).resolve().parents[2])
 (out/'recovery.json').write_text(json.dumps(dict(provenance,new_tree_sha256=result['tree_sha256'],rtl_unchanged=True,placement_tcl_unchanged=True),indent=1)+'\n')
 return result

if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--bound',required=True);a.add_argument('--out',required=True);v=a.parse_args();r=recover(v.bound,v.out);print(json.dumps(dict(plan_type=r['plan_type'],tree_sha256=r['tree_sha256'],scope='same captured reset graph and RTL')))
