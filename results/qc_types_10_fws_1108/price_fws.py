#!/usr/bin/env python3
"""Price the FWS proposal with the actual binder strap ties (copy of results/qc_types_9_v4u_1108/price.py; only the
expected changed-branch set is the two new S branches, because the 14 v4u branches keep W=3)."""
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
expected={'cws0_o','x_st_a_fe_o'}
if seen!=expected:raise ValueError(f'branch coverage missing {expected-seen}; extra {seen-expected}')
# every other strap value of every instance is unchanged
diff=[(q,k) for q,v in y['instances'].items() for k,val in v['values'].items() if x['instances'].get(q,{}).get('values',{}).get(k)!=val]
moved={(c['dst']['part'],'strap_ca_k_'+c['dst']['bus']) for c in changed}
if set(diff)!=moved:raise ValueError(f'unexpected strap changes {sorted(set(diff)-moved)}')
a.out.write_text(json.dumps(dict(schema='qc_types_10.fws_price/1',verdict='PASS',crossings=changed,changed_crossings=len(changed),covered_buses=sorted(seen),other_strap_values_identical=True,rule='K_new=K_logical+W-R+WREG; only W changes; no payload cycles'),indent=1)+'\n')
print('PASS binder pricing',len(changed),'crossings',len(seen),'W branches; all other strap values identical')
