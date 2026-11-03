#!/usr/bin/env python3
"""Prepare actual phase106 BF operand inputs; never launch a simulator or qualify epochs."""
from pathlib import Path
import argparse,hashlib,json,re
import numpy as np

KEYS=['pq_calendar_action','pq_calendar_time','pq_phase0','pq_stream0','pq_stream1','pq_stream2','pq_stream3']

def prepare(base,fixture,vector,out,selector):
    if out.exists():raise ValueError('fresh output required')
    files=json.loads((fixture/'files.json').read_text());meta=json.loads((fixture/'meta.json').read_text())
    vm=json.loads((vector/'meta.json').read_text());name='ops/attn.normalize.unrope.bin';spec=files[name]
    raw=(fixture/name).read_bytes();sha=hashlib.sha256(raw).hexdigest()
    if sha!=spec['sha256']:raise ValueError('checkpoint operand hash mismatch')
    values=np.frombuffer(raw,dtype=np.dtype(spec['dtype'])).reshape(-1);K=vm['K'];groups=values.size//K
    ranges=meta['tp_split']['wo_a_rows'];rank=meta['rank'];rpg=ranges[-1][1]//groups
    group_set={(ranges[rank][0]+x['src'][1])//rpg for x in vm['rows'].values()}
    if vm['op']!='attn.wo_a' or vm['field_phase']!=106 or len(group_set)!=1:raise ValueError('wrong native profile class')
    group=group_set.pop();src=values.reshape(groups,K)[group];bits=src.view(np.uint32)
    retained=np.array([int(x,16) for x in (vector/'vm.hex').read_text().splitlines()],dtype=np.uint32)
    lo,hi=vm['kseg']
    if not np.array_equal(bits[lo:hi],retained):raise ValueError('actual operand differs from native measured vector')
    if not np.isfinite(src).all():raise ValueError('unexpected nonfinite actual operand')
    bf=((bits.astype(np.uint64)+0x7fff+((bits.astype(np.uint64)>>16)&1))>>16).astype(np.uint16)
    lines=(base/'producer.txt').read_text().splitlines(keepends=True)
    ev=[tuple([int(x.split()[0]),int(x.split()[1]),int(x.split()[2],16)]) for x in lines]
    changes={};indices=[];wrong_words=0
    ring_events=[(i,x) for i,x in enumerate(ev) if x[1]==2]
    for ri,(i,(t,k,v)) in enumerate(ring_events):
        if not ((v>>276)&1):continue
        positions=ring_events[ri:ri+4]
        chunk=[x for _,x in positions]
        if len(chunk)!=4 or any(z[1]!=2 or z[0]!=t+n for n,z in enumerate(chunk)):raise ValueError('fragment cadence')
        packet=sum((z[2]&((1<<276)-1))<<(276*n) for n,z in enumerate(chunk))
        kind=(packet>>1)&7
        if kind!=2:continue
        index=(packet>>13)&127;indices.append(index)
        payload=sum(int(x)<<(16*n) for n,x in enumerate(bf[index*64:index*64+64]))
        old=(packet>>21)&((1<<1024)-1)
        wrong_words+=sum(((old>>(16*n))&65535)!=int(bf[index*64+n]) for n in range(64))
        updated=(packet&~(((1<<1024)-1)<<21))|(payload<<21)
        for n,z in enumerate(chunk):
            new=((updated>>(276*n))&((1<<276)-1))|(z[2]&(1<<276))
            changes[positions[n][0]]=f'{z[0]} {z[1]} {new:x}\n'
    if sorted(indices)!=list(range(64)):raise ValueError('expected actual4096-value BF group')
    out.mkdir(parents=True)
    for p in base.iterdir():
        if p.is_file() and p.name!='producer.txt':(out/p.name).symlink_to(p.resolve())
    for key in KEYS:
        p=base/(key+'.viamap.hex')
        if not p.is_file():raise ValueError('missing private source programme image '+str(p))
        (out/(selector+'.'+key+'.viamap.hex')).symlink_to(p.resolve())
    new_lines=[changes.get(i,l) for i,l in enumerate(lines)]
    (out/'producer.txt').write_text(''.join(new_lines));(out/'wrong_norm_operand_producer.txt').write_text(''.join(lines))
    (out/'actual_BF_operand_fp32.hex').write_text(''.join(f'{int(x):08x}\n' for x in bits))
    (out/'actual_BF_operand_bf16.hex').write_text(''.join(f'{int(x):04x}\n' for x in bf))
    gold=[dict(row=int(k),source_row=v['src'][1],segment=0,fp32_bits=f'{v["vals"][0]:08x}',full_accumulated_fp32_bits=f'{v["acc"]:08x}',full_accumulated_bf16_bits=f'{v["bf16"]:04x}') for k,v in vm['rows'].items()]
    d=dict(status='PREPARED_ACTUAL_BF_OPERAND_AND_SELECTED_XS_IMAGES_NOT_RUN',base=str(base),out=str(out),source=str(fixture/name),source_sha256=sha,source_shape=spec['shape'],source_note=spec.get('note'),source_group=group,source_group_count=groups,K=K,phase=106,measured_kseg=[lo,hi],first1024_FP32_words_equal_retained_native_vector=True,BF16_rule='FP32 round-to-nearest-even, integer bits+0x7fff+LSB, finite checkpoint',BF_gather_indices=indices,BF_payload_fragments_changed=len(changes),Q_fragments_and_all_control_GO_CFG_calendar_dates_changed=False,wrong_norm_source_BF16_words=wrong_words,selected_XS_selector=selector,selected_XS_aliases=7,native_BF_partial_gold=gold,arithmetic_consumer_executed=False,same_binary_executed=False,full_mission_programme_qualified=False,fresh_source_epoch_qualified=False,native_provider_qualified=False,physical_clock_sampling_qualified=False)
    (out/'BF_source_preparation.json').write_text(json.dumps(d,indent=2)+'\n')
    return d

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ['base','fixture','vector','out']:p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--selector',required=True);a=p.parse_args()
    print(json.dumps(prepare(a.base,a.fixture,a.vector,a.out,a.selector),indent=2))
