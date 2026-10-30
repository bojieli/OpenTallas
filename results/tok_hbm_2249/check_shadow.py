"""Canonical all-six-row word versions versus epoched native N3 phases.

Actual HGI DMA executes every prefetch, early publication and retirement.
Source arithmetic fields remain identical; unchanged operators are represented
by unique output-word versions, not replacement numerical approximations.
"""
import argparse,copy,json,sys
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[2];p=Path('/srv/opentallas-scratch/claude/codex-hbm-token-0830/vm_capacity/tools')
sys.path[:0]=[str(root/'tools/hbm_next'),str(p/'hbm_next'),str(p),'/home/ubuntu/OpenTallas/tools']
import isa_rows as IR,image_check as IC,vm_value_phase as V,vm_phase_shadow as S
from hgi_sim import machine as M,records as RC
rr=IC.decode_all(Path('/srv/opentallas-scratch/claude/codex-hbm-token-0830/vm_capacity/a122.hgi1r').read_bytes())
ap=argparse.ArgumentParser();ap.add_argument('--shadow',type=Path,default=Path(__file__).parent/'shadow');ap.add_argument('--values',type=Path,default=Path(__file__).parent/'values');args=ap.parse_args()
packet=json.loads((args.shadow/'shadow.json').read_text())
values=json.loads((args.values/'values.json').read_text())
FIRST=min(r['source_record']for p in packet['phases']for r in p['records']if r['kind']=='body');LAST=max(r['source_record']for p in packet['phases']for r in p['records']if r['kind']=='body')
ALL=(1<<len(RC.UNITS))-1


def seed():
    words=((np.arange(1<<19,dtype=np.uint64)*np.uint64(2654435761))^np.uint64(0x9e3779b9)).astype(np.uint32)
    words[::257]=np.uint32(0x7fc12345);words[::509]=np.uint32(0xffffffff)
    return words


def payload(index,slot,k,size):
    tag=np.uint32(((index*2654435761)^(slot<<20)^(ord(k)<<16))&0xffffffff)
    return np.arange(size,dtype=np.uint32)+tag



def source_payload(r,index,slot,k,size):
    if(r.unit,r.op)==('DMA','LOAD'):
        a=r.desc['A']
        if a.space=='HBM'and a.fmt in('FP32','U32')and a.m==1 and a.n==size:
            return((np.arange(size,dtype=np.uint64)+np.uint64(a.base//4))*np.uint64(2654435761)^np.uint64(0x9e3779b9)).astype(np.uint32)
        # Other source DMA formats remain the unchanged original operator. Its
        # output version is stable for an identical source descriptor.
        import hashlib
        tag=int.from_bytes(hashlib.sha256(repr(vars(a)).encode()).digest()[:4],'little')
        return np.arange(size,dtype=np.uint32)+np.uint32(tag)
    return payload(index,slot,k,size)

def canonical():
    memory=seed();reads={};epochs={}
    for index in range(FIRST,LAST+1):
        for slot,r in IR.expand(rr[index][1],rr[index][2]):
            for dep in packet['source_epochs']['dependencies']:
                if dep['before_source_record']==index and dep['consumer_slot']==slot:
                    a=dep['source_sector'];epochs[dep['hbm_range'][0]]=memory[a:a+8].copy()
            wo=IR.written_operands(r)
            x=rr[index][2]
            if r.unit=='ATT'and x and x.rsel:reads[(index,slot,'__rtab')]=memory[x.rtab:x.rtab+32*IR.PLAN_WORDS].copy()
            for k,d in r.desc.items():
                if d.space=='VM'and k not in wo:
                    a,b=V.engine_span(r,k);reads[(index,slot,k)]=memory[a:b].copy()
            for k in wo:
                if k in r.desc and r.desc[k].space=='VM':
                    a,b=V.engine_span(r,k);memory[a:b]=source_payload(r,index,slot,k,b-a)
    return memory,reads,epochs


FINAL,READS,EPOCHS=canonical()


def replay(raws):
    words=seed();hbm=M.Hbm();a,b=packet['phases'][0]['input_snapshot'];hbm.add(a,words.copy(),'entry_epoch')
    for ph in packet['phases']:
        oa,ob=ph['output_bank'];hbm.add(oa,np.zeros(ob-oa,np.uint8),f'phase{ph["slot0"]}_output')
    ea,eb=packet['source_epochs']['producer_epoch_range'];hbm.add(ea,np.zeros(eb-ea,np.uint8),'producer_epochs')
    constants={}
    for index in range(FIRST,LAST+1):
        r=rr[index][1]
        if(r.unit,r.op)==('DMA','LOAD'):
            a=r.desc['A']
            if a.space=='HBM'and a.fmt in('FP32','U32')and a.m==1 and not a.base>>37:
                constants[a.base]=source_payload(r,index,0,'O',a.n)
    for addr,data in sorted(constants.items()):hbm.add(addr,data,f'source_constant_{addr}')
    die=M.Die(0,hbm);machine=M.Machine([die]);reads=0;stores=0;epochs=0
    for ph in packet['phases']:
        die.vm[:]=np.uint32(0xdeadbeef)
        decoded=IC.decode_all(raws[ph['slot0']]);assert len(decoded)==len(ph['records'])
        for meta,(_,r,x,_)in zip(ph['records'],decoded):
            assert r.wait==ALL,'missing serial unit barrier'
            if meta['kind']!='body':
                assert x is None;machine.cur=r
                if r.op=='LOAD':M.u_dma_load(machine,r,0)
                elif r.op=='STORE':
                    M.u_dma_store(machine,r,0);stores+=r.desc['A'].n
                    if meta['kind']=='epoch_store':epochs+=1
                else:M.u_dma_fence(machine,r,0)
                continue
            index=meta['source_record'];source_rows=dict(IR.expand(rr[index][1],rr[index][2]))
            if r.unit=='ATT'and rr[index][2].rsel:
                assert x and x.rsel and x.n==rr[index][2].n and x.slot0==rr[index][2].slot0,'attention plan lanes scalarized'
            for slot,q in IR.expand(r,x):
                source=source_rows[slot];check=copy.deepcopy(q);check.wait=source.wait
                for k in check.desc:check.desc[k].base=source.desc[k].base
                assert vars(check)==vars(source),'source arithmetic fields differ'
                wo=IR.written_operands(source)
                if source.unit=='ATT'and x and x.rsel:
                    table=die.vm[x.rtab:x.rtab+32*IR.PLAN_WORDS]
                    assert np.array_equal(READS[(index,slot,'__rtab')],table),'implicit attention plan version differs'
                    reads+=len(table)
                for k,d in source.desc.items():
                    if d.space!='VM':continue
                    lo,hi=V.engine_span(source,k);u,v=V.engine_span(q,k)
                    assert 0<=u<v<=262144
                    if k not in wo:
                        assert np.array_equal(READS[(index,slot,k)],die.vm[u:v]),f'canonical source epoch mismatch{index}/{slot}/{k}'
                        reads+=hi-lo
                if(q.unit,q.op)==('DMA','LOAD')and q.desc['A'].base in constants:
                    machine.cur=q;M.u_dma_load(machine,q,0);continue
                for k in wo:
                    if k not in source.desc or source.desc[k].space!='VM':continue
                    lo,hi=V.engine_span(source,k);u,v=V.engine_span(q,k);die.vm[u:v]=source_payload(source,index,slot,k,hi-lo)
    for addr,expected_epoch in EPOCHS.items():
        assert np.array_equal(hbm.view(addr,32).view(np.uint32),expected_epoch),'canonical producer epoch differs'
    for selected in packet['source_epochs']['final_output_sectors']:
        a,b=selected['source_words'];lo,hi=selected['hbm_range']
        assert np.array_equal(hbm.view(lo,hi-lo).view(np.uint32),FINAL[a:b]),'canonical final boundary differs'
    assert np.array_equal(hbm.view(packet['phases'][0]['input_snapshot'][0],len(words)*4).view(np.uint32),words),'entry epoch overwritten'
    return reads,stores,epochs


raws={p['slot0']:(args.shadow/p['fragment']).read_bytes()for p in packet['phases']}
checked,stored,epochs=replay(raws);controls=[]
for group in (0,3):
    ph=next(p for p in packet['phases']if p['slot0']==group)
    for kind in('wrong_load','partial_store','missing_barrier','wrong_retirement'):
        decoded=IC.decode_all(raws[group]);wanted='store'if kind in('partial_store','wrong_retirement')else'load'
        target=next(i for i,m in enumerate(ph['records'])if m['kind']==wanted and(kind!='wrong_retirement'or any(f['phase']==group and max(m['source_words'][0],f['source_words'][0])<min(m['source_words'][1],f['source_words'][1])for f in packet['source_epochs']['final_output_sectors'])));r,x=decoded[target][1:3]
        if kind=='wrong_load':r.desc['A'].base+=4
        elif kind=='partial_store':r.desc['O'].n-=1;r.desc['A'].n-=1
        elif kind=='missing_barrier':r.wait=0
        else:r.desc['O'].base+=32
        bad=raws.copy();bad[group]=b''.join(IR.encode(r,x)for _,r,x,_ in decoded)
        try:replay(bad)
        except(AssertionError,ValueError,M.Fault):controls.append(f'{group}:{kind}')
        else:raise AssertionError(kind+' escaped')
ph=packet['phases'][0];decoded=IC.decode_all(raws[0])
candidates=[i for i,m in enumerate(ph['records'])if m['kind']=='epoch_store'and any(max(m['source_words'][0],f['source_words'][0])<min(m['source_words'][1],f['source_words'][1])for f in packet['source_epochs']['final_output_sectors'])]
if candidates:
    decoded[candidates[0]][1].desc['A'].base+=8
    bad=raws.copy();bad[0]=b''.join(IR.encode(r,x)for _,r,x,_ in decoded)
    try:replay(bad)
    except(AssertionError,ValueError,M.Fault):controls.append('wrong_producer_epoch')
    else:raise AssertionError('producer epoch corruption escaped')
attention_phases=[ph for ph in packet['phases']if any(m['kind']=='body'and rr[m['source_record']][1].unit=='ATT'for m in ph['records'])]
if attention_phases:
    ph=attention_phases[0];decoded=IC.decode_all(raws[ph['slot0']]);target=next(i for i,(_,r,x,_)in enumerate(decoded)if r.unit=='ATT'and r.op=='PV');decoded[target]=(decoded[target][0],decoded[target][1],None,decoded[target][3])
    bad=raws.copy();bad[ph['slot0']]=b''.join(IR.encode(r,x)for _,r,x,_ in decoded)
    try:replay(bad)
    except(AssertionError,ValueError,M.Fault):controls.append('attention_plan_scalarization')
    else:raise AssertionError('attention plan scalarization escaped')
try:
    ph=values['phases'][0];raw=(args.values/ph['fragment']).read_bytes();S.compile_phase(ph,raw,0xF000000000,4*(1<<19),0,IR,RC)
except ValueError:controls.append('illegal_stripe_code7')
else:raise AssertionError('illegal old scratch stripe escaped')
print(json.dumps(dict(native_records=sum(p['native_records']for p in packet['phases']),canonical_read_words=checked,retired_words=stored,early_epoch_sectors=epochs,transfer_bytes=sum(p['transferred_bytes']for p in packet['phases']),final_boundary_words=sum(s['source_words'][1]-s['source_words'][0]for s in packet['source_epochs']['final_output_sectors']),controls=controls)))
