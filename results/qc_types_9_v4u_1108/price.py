#!/usr/bin/env python3
"""Price the proposal with the actual binder, retaining exact crossing K deltas."""
import argparse,json,sys
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
for n in ('base','candidate','sidecar','tools','out'):p.add_argument('--'+n,type=Path,required=True)
a=p.parse_args();sys.path.insert(0,str(a.tools));import count_align_bind as CAB
old=json.loads(a.base.read_text());new=json.loads(a.candidate.read_text());ca=json.loads(a.sidecar.read_text())['count_aligned']
x=CAB.strap_ties(ca,old);y=CAB.strap_ties(ca,new)
ptype={v['name']:v['type'] for v in old['partitions']};ports={v['id']:v for v in old['ports']};changed=[];seen=set()
for pid,c in ca['ports'].items():
 b=ports[pid];src=b['src'];dst=b['dst'];before=CAB.writer_start_depth(old,ptype[src['part']],src['bus']);after=CAB.writer_start_depth(new,ptype[src['part']],src['bus'])
 if before==after:continue
 if ptype[src['part']]!='sle_fw_v3':raise ValueError('unrelated writer changed')
 strap='strap_ca_k_'+dst['bus'];width=y['types'][ptype[dst['part']]]['straps'][strap];ov=x['instances'][dst['part']]['values'][strap];nv=y['instances'][dst['part']]['values'][strap]
 if (nv-ov)%(1<<width)!=(after-before)%(1<<width):raise ValueError('K mismatch')
 changed.append(dict(port=pid,src=src,dst=dst,old_W=before,new_W=after,K_delta=after-before,old_strap=ov,new_strap=nv,width=width));seen.add(src['bus'])
expected=set(new['partition_types']['sle_fw_v3']['clock']['landing_writer_start']['branches'])
if seen!=expected:raise ValueError(f'branch coverage missing {expected-seen}; extra {seen-expected}')
a.out.write_text(json.dumps(dict(schema='codex.qc_fw_start_price/1',verdict='PASS',crossings=changed,changed_crossings=len(changed),covered_buses=sorted(seen),rule='K_new=K_logical+W-R+WREG; only W changes; no payload cycles'),indent=1)+'\n')
print('PASS binder pricing',len(changed),'crossings',len(seen),'W branches')
