#!/usr/bin/env python3
"""Restore an earlier actual past-KV prefix by undoing only later KV writes.

Input-only byte transformation: no numerical operator, model, current X,
expected target, draft token or inference. Original caches remain immutable.
Source-derived destination addresses and a canonical L0 byte control bind the
operation. This is not a target-output oracle or feature-history substitute.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()

def require(test,message):
    if not test:raise ValueError(message)

def destinations(program,lay,pos):
    import numpy as np
    import hdc_program as P
    dyn=P.dyn_values(lay,0,pos);addresses=[]
    for f in program:
        if f['unit']!=P.I.UNIT_SU or f['dst']!=P.I.DST_KV:continue
        require(f['su_d_nin']==0,'dynamic KV writer length unsupported')
        require(f['d_d'] in (P.I.DYN_KWRITE,P.I.DYN_VWRITE),'non-position KV writer unsupported')
        o,i=np.meshgrid(np.arange(f['su_nout']),np.arange(f['su_nin']),indexing='ij')
        addresses.extend((f['d_base']+dyn[f['d_d']]+o*f['d_so']+i*f['d_si']).reshape(-1).tolist())
    actual=np.array(sorted(set(addresses)),dtype=np.int64)
    expected=np.array(sorted(lay.k_elem(0,h,pos,d) for h in range(lay.KV) for d in range(lay.HD))+
                      sorted(lay.v_elem(0,h,pos,d) for h in range(lay.KV) for d in range(lay.HD)),dtype=np.int64)
    require(np.array_equal(actual,expected),'literal KV writes differ from shape-only source address contract')
    require(len(addresses)==len(actual),'overlapping KV destination writes unsupported')
    return actual

def prepare(a):
    for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'
    for k,v in dict(QWEN_O4_TP='4',QWEN_O4_GROUPS='6144',HDC_SU_WIDTH='1024',HDC_KV_FMT='fp8').items():os.environ[k]=v
    import numpy as np
    import hdc_qwen_fullshape_program_w12 as FP
    import hdc_qwen_fullshape_isa_w12 as I
    require(not a.output.exists(),'fresh prefix output required')
    require(sha(a.tokens)==a.tokens_sha256,'actual prompt changed')
    tokens=[int(t) for t in a.tokens.read_text().split()]
    original=a.cache/'oracle.json';old=json.loads(original.read_text())
    require(old['layers']==36 and old['tp']==4 and old['groups']==6144 and old['kv_format']=='fp8','matching full36 TP4 source required')
    require(0<a.position<a.source_position<=8192 and tokens[a.position]==a.token,'actual pending extent/token differs')
    require(old['tokens_used'][:a.position]==tokens[:a.position],'actual past token prefix differs')
    frame=old['per_position'][str(a.source_position)]
    control=a.l0_cache/'oracle.json';l0=json.loads(control.read_text())['per_position'][str(a.position)]
    require(l0['token']==a.token,'canonical L0 pending token differs')
    source_pins={str(original.resolve()):sha(original),str(a.tokens.resolve()):a.tokens_sha256,str(control.resolve()):sha(control)}
    compiled=[]
    # Check every literal destination before producing any bytes.
    for layer in range(36):
        for rank in range(4):
            directory=a.source_images/f'L{layer}-d{rank}'
            manifest=directory/f'layer{layer}_rom.json';m=json.loads(manifest.read_text())
            require(m['layer']==layer and m['die']==rank and m['tp']==4,'source layer/rank differs')
            require(m['checkpoint_revision']=='b968826d9c46dd6066d109eabc6255188de91218','released checkpoint differs')
            program_path=directory/'program.hex'
            require(sha(program_path)==m['image_sha256']['program.hex'],'source program pin differs')
            source_pins[str(program_path.resolve())]=sha(program_path);source_pins[str(manifest.resolve())]=sha(manifest)
            lay=FP.LayerZero(None,rank,m['matrix_layout'])
            require(lay.KV==2 and lay.HD==128 and 2*lay.kv_v0==4194304,'native KV shape differs')
            program=[I.decode_instruction(int(w,16)) for w in program_path.read_text().split()]
            addresses=np.concatenate([destinations(program,lay,p) for p in range(a.position,a.source_position)])
            require(len(np.unique(addresses))==len(addresses),'later KV writes alias one another')
            npy=a.cache/f'P{a.source_position}'/'kv_pre'/f'L{layer}_die{rank}.npy'
            require(sha(npy)==frame['kv_pre_sha256'][f'L{layer}_die{rank}'],'actual retained prior KV changed')
            compiled.append((layer,rank,npy,addresses))
    a.output.mkdir();history=a.output/'history';history.mkdir();npy_dir=a.output/f'P{a.position}'/'kv_pre';npy_dir.mkdir(parents=True)
    bindings={};new_hashes={};erased={}
    for layer,rank,npy,addresses in compiled:
        key=f'L{layer}_die{rank}';data=np.load(npy,allow_pickle=False)
        require(data.dtype==np.dtype('<u4') and data.shape==(4194304,),'decoded raw32 KV layout differs')
        data[addresses]=0 # source DieMachine starts all not-yet-written KV as +0.
        if layer==0:
            canonical=a.l0_cache/f'P{a.position}'/'kv_pre'/(key+'.npy')
            require(sha(canonical)==l0['kv_pre_sha256'][key],'canonical L0 input changed')
            require(np.array_equal(data,np.load(canonical,allow_pickle=False)),'derived past prefix differs from actual canonical L0 bytes')
            source_pins[str(canonical.resolve())]=sha(canonical)
        derived=npy_dir/(key+'.npy');np.save(derived,data,allow_pickle=False)
        raw=history/(key+'.bin');data.tofile(raw)
        new_hashes[key]=sha(derived);erased[key]=len(addresses)
        bindings[key]=dict(raw=str(raw.resolve()),raw_sha256=sha(raw),source=str(derived.resolve()),source_sha256=new_hashes[key])
    # Honest input-provider record; no ISA-golden/head/output status is asserted.
    provider=dict(schema='opentallas.qwen-prior-kv-prefix.v1',status='derived_actual_prior_kv_prefix',tp=4,groups=6144,kv_format='fp8',layers=36,
        source_position=a.source_position,position=a.position,source_oracle_sha256=sha(original),input_sha256=source_pins,
        per_position={str(a.position):dict(token=a.token,kv_pre_sha256=new_hashes)},discarded_later_writer_addresses=erased,
        source_sha256={name:sha(ROOT/name) for name in ('tools/qwen_rom_past_kv_prefix.py','tools/hdc_program.py',
            'tools/hdc_qwen_fullshape_program_w12.py','tools/hdc_qwen_fullshape_isa_w12.py','tools/qwen_o4_layer0_oracle_w12.py')},
        scope='Past KV input bytes only; source-address suffix removal, exact canonical L0 control; no current X/head/feature output or inference')
    provider_path=a.output/'oracle.json';provider_path.write_text(json.dumps(provider,indent=2)+'\n')
    record=dict(schema='opentallas.qwen-rom-full36-inputs.v1',position=a.position,token=a.token,
        oracle=dict(root=str(a.output.resolve()),sha256=sha(provider_path)),history=bindings,history_directory=str(history.resolve()),
        input_sha256=source_pins,scope=provider['scope'])
    (a.output/'inputs.json').write_text(json.dumps(record,indent=2)+'\n')
    rows=[]
    for layer in range(36):
        directories=[a.decoder_images/f'L{layer}-d{rank}' for rank in range(4)]
        require(all((p/'program.hex').is_file() for p in directories),'actual owner VPOS image missing')
        rows.append(' '.join([f'L{layer}',*map(lambda p:str(p.resolve()),directories),'0']))
    (a.output/'decoder_stages.txt').write_text('\n'.join(rows)+'\n')
    return dict(status='actual_prior_kv_prefix_ready',inputs=str((a.output/'inputs.json').resolve()),
                decoder_stage_list=str((a.output/'decoder_stages.txt').resolve()),bindings=len(bindings),canonical_L0_bit_exact=True)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('cache','tokens','source-images','decoder-images','l0-cache','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--tokens-sha256',required=True);p.add_argument('--source-position',type=int,default=8191)
    p.add_argument('--position',type=int,default=8187);p.add_argument('--token',type=int,default=15)
    print(json.dumps(prepare(p.parse_args())),flush=True)

if __name__=='__main__':main()
