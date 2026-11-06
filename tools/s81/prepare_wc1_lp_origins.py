#!/usr/bin/env python3
"""Prepare owned, opt-in LP origin parameters from a pinned wc1 reset receipt."""
from pathlib import Path
import argparse, hashlib, json, re
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--receipt',type=Path,required=True)
ap.add_argument('--source-root',type=Path,required=True)
ap.add_argument('--capability-root',type=Path,required=True)
ap.add_argument('--output',type=Path,required=True)
a=ap.parse_args()
if a.output.exists():raise SystemExit('Output must be new; preserve previous proposals')
receipt=json.loads(a.receipt.read_text());assert receipt['D']==4 and receipt['K']==2
shared=['rtl/common/landed_parent/ot_pl_land.sv','rtl/common/landed_parent/ot_pl_land_reset_forest.sv','rtl/dsrom_sys/s81_dv/slice/mu72/ot_s81_mu72_land.sv','physical/die_plan/s81/bind/source_modules/portfix178/ot_s81_mu72_lnland.sv']
sha=lambda b:hashlib.sha256(b).hexdigest()
prepared=[];readset=[];count=0
for row in receipt['rows']:
 checked={}
 for original,digest in row['source_sha256'].items():
  src=a.source_root/Path(original).name;b=src.read_bytes()
  assert sha(b)==digest,('receipt source changed',src)
  checked[original]=(src,b);readset.append(dict(source=str(src),receipt_path=original,sha256=digest))
 lp=[(p,b) for p,b in checked.values() if '_LP__' in p.name];assert len(lp)==1
 src,b=lp[0];s=b.decode();params=[]
 for lane in row['lanes']:
  wr,rd=lane['writer_reset_edge'],lane['reader_reset_edge']
  kn,nk=(rd-wr)%8,(wr-rd)%8
  assert (kn,nk)==(lane['KN_bias'],lane['NK_bias'])
  pattern=r'(\bot_s81_mu72_lnland(?:_nst)?\s*#\()([^\n]*)(\)\s+'+re.escape(lane['instance'])+r'\s*\()'
  def replace(m):
   assert 'EPOCH_BIAS' not in m[2], 'already parameterized'
   return m[1]+m[2]+f', .KN_EPOCH_BIAS({kn}), .NK_EPOCH_BIAS({nk})'+m[3]
  s,n=re.subn(pattern,replace,s);assert n==1,(src,lane['instance'],n)
  params.append(dict(instance=lane['instance'],KN_EPOCH_BIAS=kn,NK_EPOCH_BIAS=nk,writer_reset_edge=wr,reader_reset_edge=rd));count+=1
 prepared.append((Path('parents')/src.name,s.encode(),dict(station=row['station'],module=src.stem,source=str(src),candidate='parents/'+src.name,parameters=params,sha256=sha(s.encode()))))
assert count==14 and len(prepared)==4
caps=[]
for rel in shared:
 b=(a.capability_root/rel).read_bytes();caps.append((Path('capability')/rel,b))
 # Required parameter definitions must be present in copied capability.
 if rel.endswith('ot_pl_land.sv'):assert b'EPOCH_BIAS' in b
 if rel.endswith('ot_s81_mu72_lnland.sv'):assert b'KN_EPOCH_BIAS' in b and b'NK_EPOCH_BIAS' in b
a.output.mkdir(parents=True)
for rel,b,*_ in prepared+caps:
 p=a.output/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
manifest=dict(scope='Opt-in activewc1 source proposal; no activation, current runtime or physical release',source_binder_commit=None,source_receipt_sha256=sha(a.receipt.read_bytes()),capability_source_commit='204f8dac0c9',pin_cycles_added=0,clock_ps=833,reader_local_age_unchanged=True,physical_release_adopted=False,instance_count=count,source_readset=readset,parents=[x[2] for x in prepared],capability=[dict(candidate=str(p),sha256=sha(b)) for p,b in caps])
(a.output/'proposal.json').write_text(json.dumps(manifest,indent=2)+'\n')
(a.output/'receipt.json').write_bytes(a.receipt.read_bytes())
print(json.dumps(manifest,indent=2))
