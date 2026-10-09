#!/usr/bin/env python3
"""Minimum linker/ownership gate; generated words are fixtures, not arithmetic."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from dshbm_mtp_kernel_enroll import KINDS, SHAPE, link

def gate(root,isa):
    root=Path(root);root.mkdir(parents=True,exist_ok=False)
    isa=Path(isa).resolve()
    def receipt(p):return dict(path=str(p.resolve()),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    marker=root/'fixture_provenance.txt';marker.write_text('Synthetic linker fixture; not checkpoint or numerical proof.\n')
    kernels={}
    for i,k in enumerate(KINDS):
        payload=[]
        for sm in range(32):
            p=root/f'{k}_{sm}.hex'
            # Unequal lengths prove full-replica padding; owned local branch1.
            words=[0x3000000000000001,0x3200000000000000]+[0]*(sm%3)
            p.write_text(''.join(f'{w:016x}\n' for w in words))
            payload.append(dict(sm=sm,**receipt(p)))
        kernels[k]=payload
    m=dict(schema='opentallas.dshbm.mtp.unlinked_sram64.v1',shape=SHAPE,
        arithmetic_contract='chunk8',word_bits=64,imw=14,
        compiler_sources=[receipt(marker)],checkpoint_sources=[receipt(marker)],
        isa=receipt(isa),kernels=kernels)
    def run(name,data):
        p=root/(name+'.json');p.write_text(json.dumps(data));return link(p,root/name)
    r=run('positive',m)
    assert r['installable'] and r['imem_words']==44
    events=json.loads((root/'positive/install_events.json').read_text())
    assert all(x['install_pc']==((i*4)<<32)|(i*4) for i,x in enumerate(events))
    for sm in range(32):
        words=[int(x,16) for x in (root/f'positive/prog_s{sm}.hex').read_text().split()]
        assert len(words)==44 and all(words[4*i]&0xffffffff==4*i+1 for i in range(11))
    incomplete=copy.deepcopy(m);del incomplete['kernels']['layer']
    ri=run('missing_layer',incomplete)
    assert not ri['installable'] and ri['missing_kernels']==['layer']
    assert json.loads((root/'missing_layer/install_events.json').read_text())==[]
    mutants={}
    for name,edit in (
        ('reduced_hidden',lambda x:x['shape'].update(hidden=160)),
        ('token16_truncation',lambda x:x['shape'].update(token_bits=16)),
        ('missing_SM',lambda x:x['kernels']['head'].pop()),
        ('duplicated_SM',lambda x:x['kernels']['seed'][1].update(sm=0)),
        ('payload_mutation',lambda x:x['kernels']['markov'][0].update(sha256='0'*64))):
        bad=copy.deepcopy(m);edit(bad)
        try:run(name,bad)
        except ValueError as e:mutants[name]=str(e)
        else:raise AssertionError('mutant accepted: '+name)
    result=dict(status='PASS',scope='source-linker fixture gate only; no production images or arithmetic',
        actual_SM_replicas=32,kernels=11,linked_words=44,
        positive_cases=2,negative_cases=mutants,numerical_qualified=False,
        source_sha256={str(Path(__file__)):receipt(Path(__file__))['sha256'],
            str(Path(__file__).with_name('dshbm_mtp_kernel_enroll.py')):receipt(Path(__file__).with_name('dshbm_mtp_kernel_enroll.py'))['sha256'],
            str(isa):receipt(isa)['sha256']})
    (root/'verdict.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--isa',required=True)
    a=p.parse_args();print(json.dumps(gate(a.out,a.isa)))
