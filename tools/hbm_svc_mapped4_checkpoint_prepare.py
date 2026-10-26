#!/usr/bin/env python3
"""Prepare actual source/allocator guarded inputs for mapped-four-PC RTL replay."""
import argparse
import json
from pathlib import Path
from hbm_svc_packed136_image import digest,install


def prepare(payload_manifest,programme_manifest,allocation_root,out):
    payload_manifest,programme_manifest,allocation_root,out=map(Path,(payload_manifest,programme_manifest,allocation_root,out))
    p=json.loads(payload_manifest.read_text());prog=json.loads(programme_manifest.read_text())
    if p['schema']!='opentallas.actual-checkpoint-sm-payload.v1' or prog['schema']!='opentallas.checkpoint-sm-static-programme.v1':raise ValueError('actual released source and native programme schemas required')
    if prog['payload_manifest_sha256']!=digest(payload_manifest):raise ValueError('actual programme/payload provenance mismatch')
    plans={x['sm']:x for x in prog['plans']}
    out.mkdir(parents=True,exist_ok=False);active=[];idle=[]
    for op in p['ops']:
        sm=op['sm'];plan=plans[sm]
        if bool(op['active'])!=bool(plan['active']):raise ValueError('actual programme active mask mismatch')
        if not op['active']:idle.append(sm);continue
        allocation=allocation_root/f'sm{sm:02d}.json';a=json.loads(allocation.read_text())
        if p['rank'] not in a.get('usable_ranks',[p['rank']]):raise ValueError('rank reservation prohibited')
        source=payload_manifest.parent/op['file']
        if digest(source)!=op['sha256'] or plan['source_sha256']!=op['sha256'] or plan['real_packets']!=op['lines']:raise ValueError('actual op/programme source mismatch')
        d=out/f'sm{sm:02d}';r=install(source,op['sha256'],op['lines'],allocation,d)
        physical=(d/'physical.hex').read_text().splitlines();back=[];expected=[]
        for i in range(r['sectors']):
            address=int(physical[2*i][1:],16)
            back.append(f'@{address%65536:08x}\n{physical[2*i+1]}\n');expected.append(physical[2*i+1]+'\n')
        (d/'backing.hex').write_text(''.join(back));(d/'sectors.hex').write_text(''.join(expected))
        (d/'records.hex').write_bytes(source.read_bytes())
        config=dict(sm=sm,rank=p['rank'],stack=a['stack'],pcs=a['pcs'],row_base=a['row_base'],rows=op['lines'],sectors=r['sectors'],tag_base=plan['tag_base'],payload_source_sha256=op['sha256'],allocation_sha256=digest(allocation),programme_plan=plan)
        (d/'config.json').write_text(json.dumps(config,indent=2)+'\n');active.append(config)
    receipt=dict(schema='opentallas.actual-packed136-mapped4-prepared.v1',rank=p['rank'],payload_manifest_sha256=digest(payload_manifest),programme_manifest_sha256=digest(programme_manifest),allocation_book_sha256=digest(allocation_root/'book.json'),active=active,idle_SMs=idle,real_records=sum(x['rows'] for x in active),real_sectors=sum(x['sectors'] for x in active),scope='Actual released checkpoint input image and hardware programme source binding; hardware installation/final decode not qualified')
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for x in ('payload-manifest','programme-manifest','allocation-root','out'):p.add_argument('--'+x,required=True)
    a=p.parse_args();r=prepare(a.payload_manifest,a.programme_manifest,a.allocation_root,a.out);print(json.dumps({k:r[k] for k in ('rank','real_records','real_sectors','idle_SMs')}))
