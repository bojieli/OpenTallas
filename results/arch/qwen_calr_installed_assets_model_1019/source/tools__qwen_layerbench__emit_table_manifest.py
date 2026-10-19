#!/usr/bin/env python3
"""Recover all36 static table payloads from the pinned TP4 prepared images.

TP8 die0 is the exact row subset already established by dv_layer_fixture.
Prepared artifact hashes are verified before use. This does not substitute
for source-checkpoint verification, native loader execution, or token tests.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

LOWERER_PINS={
 'dv_lower.py':'6703f03fb928907bad952babcf05890c41b5096ea81f81dbab7f4c01a6c800c5',
 'dv_lower_vec.py':'3f01c9a9a217e7ab53de2dce6320f7e2cb29d86c977d53e67714065ecfc5bfff',
 'dv_lower_mat.py':'c35eb8c15aa15c00af8a3e97b28740c11797a1cf049c4ede3317b45923ed81bd'}


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--lowering-root',type=Path,required=True)
    ap.add_argument('--prepared',type=Path,required=True)
    ap.add_argument('--native-images',type=Path,required=True)
    ap.add_argument('--checkpoint-lock',type=Path,required=True)
    ap.add_argument('--compact-btab',action='store_true')
    ap.add_argument('--global-boundary-program',type=Path)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    for name,digest in LOWERER_PINS.items():
        if sha(a.lowering_root/'tools/qwen_layerbench'/name)!=digest:
            raise ValueError('uncommitted lowerer revision: '+name)
    if any(not(a.native_images/f'L{n}/die0').is_dir() for n in (0,1)):
        raise ValueError('both pinned native L0 and L1 images required')
    sys.path.insert(0,str(a.lowering_root/'tools'))
    sys.path.insert(0,str(a.lowering_root/'tools/qwen_layerbench'))
    import dv_lower as D
    import dv_lower_vec as V
    import dv_lower_mat as M
    import programme_store as PS
    from table_user_programme import relocate
    prep_path=a.prepared/'prep.json';prep=json.loads(prep_path.read_text())
    selected=[e for e in prep['images'] if e['kind']=='layer' and e['die']==0]
    if sorted(e['layer'] for e in selected)!=list(range(36)):raise ValueError('all36 prepared layers required')
    own=D.ownership();vm=V.vm_map_vec(own);cr=V.crom_map(own)
    high=max(r['base']+r['size'] for r in vm.values())
    if high>4096:raise ValueError('local DV data exceed production per-user window')
    lw=V.lower_vec('resid');template=lw['prog_stream']
    gb=None;contract=None
    if a.global_boundary_program:
        import global_boundary as gb
        if sha(Path(gb.__file__))!='76397ead01f5dec8b2823545b7d6bd07ced514d93b3207c8642064418b471028':
            raise ValueError('global boundary adapter differs from native-qualified source')
        contract=gb.layer_contract(a.global_boundary_program)
    progs={};proof=[];word_proof=[]
    for s in range(12):
        progs[s]=[]
        for u in range(4):
            records=[]
            for record in template[s]:
                pay=int(record['payload'],16);pair=[]
                for i in range(2):
                    word=(pay>>(512*i))&((1<<512)-1)
                    rewritten,p=relocate(word,u,high)
                    if gb:rewritten=gb.rewrite_x(rewritten,u,contract)
                    word_proof.append(dict(slice=s,user=u,pair=record['eaddr'],half=i,
                        original=f'{word:0115x}',relocated=f'{rewritten:0115x}'))
                    proof.extend(dict(slice=s,user=u,pair=record['eaddr'],half=i,**x) for x in p)
                    pair.append(rewritten)
                records.append(dict(addr=record['eaddr'],payload_hex=f'{pair[0]|pair[1]<<512:0256x}'))
            progs[s].append(records)
    certificate=dict(schema='opentallas.qwen.dv-local-user-address-proof.v1',vm=vm,
        vm_high_water=high,vm_stride=4096,crom_element_stride=2048,pidx_stride=128,
        btab_user_bases=[0,272,344,416] if a.compact_btab else [0,128,256,384],
        btab_shared_head_region=[72,272] if a.compact_btab else None,
        scope='All lowered local DV operand loops only; global ME/head bridge, ROOT config and stream identities OPEN',
        proof=proof,word_proof=word_proof)
    if gb:
        certificate['global_x_contract']=contract
        certificate['global_boundary_source_sha256']=sha(Path(gb.__file__))
        certificate['scope']='Local DV operands and aligned decode SU-X identities; ME/XPF install, ROOT/head and lifetime joins OPEN'
    a.out.mkdir(parents=True,exist_ok=True)
    cert_path=a.out/'user_relocation_certificate.json'
    cert_path.write_text(json.dumps(certificate,indent=1)+'\n')
    lock=a.checkpoint_lock
    manifest=dict(schema='opentallas.qwen.mu-table-input.v1',
        qualification='All36 prepared static payloads; checkpoint revalidation and native execution OPEN',
        parameters=dict(NU=4,PIDX_STRIDE=128,CROM_ROW_STRIDE=128,BTAB_WORD_STRIDE=128),
        source=dict(lowering_commit='4e718c0107e99f869c95db0ecedcca8711577dff',
            checkpoint_sha256=sha(lock),checkpoint_revision=json.loads(lock.read_text())['revision'],
            checkpoint_provenance='Expected checkpoint lock; prepared NPZ source chain, not a fresh checkpoint comparison',
            prepared_manifest_sha256=sha(prep_path),user_relocation_certificate_sha256=sha(cert_path),
            generation_tools={name:sha(Path(__file__).parent/name) for name in
                ('emit_table_manifest.py','table_user_programme.py','programme_store.py')},
            lowerers={k:sha(a.lowering_root/'tools/qwen_layerbench'/k) for k in ('dv_lower.py','dv_lower_vec.py','dv_lower_mat.py')}),
        stages=[],receipts=[])
    if a.compact_btab:
        manifest['parameters'].pop('BTAB_WORD_STRIDE')
        manifest['parameters']['BTAB_WORD_BASES']=[0,272,344,416]
    if gb:
        manifest['source']['global_boundary_commit']='fe49023bd'
        manifest['source']['generation_tools']['global_boundary.py']=sha(Path(gb.__file__))
        manifest['source']['global_x_contract']=contract
    qrows=np.r_[0:512,1024:1152,1280:1408]
    for e in sorted(selected,key=lambda x:x['layer']):
        n=e['layer'];src=a.prepared/e['npz']
        if sha(src)!=e['npz_sha256']:raise ValueError(f'prepared payload hash mismatch L{n}')
        with np.load(src) as p:
            crom=p['crom']; qn=crom[4096:4224,0];kn=crom[5120:5248,0]
            ps1=crom[-8192:-4096,0];ps2=crom[-4096:,0]
            scales=dict(qkv=p['scales_qkv'][qrows],gu=p['scales_gu'][:3072],
                        o=np.ones(4096,dtype=np.float32),down=np.ones(4096,dtype=np.float32))
            if scales['qkv'].shape!=(768,) or scales['gu'].shape!=(3072,) or crom.shape[1]!=2:
                raise ValueError('prepared TP4 shape differs from exact subset contract')
            b=M.btab_stream(M.btab_layout(own),scales)
            c=V.crom_table(own,cr,dict(ps1=ps1,ps2=ps2,q_norm=qn,k_norm=kn))
            native=a.native_images/f'L{n}/die0'
            checks={}
            if native.is_dir():
                meta=json.loads((native/f'layer{n}_rom.json').read_text())
                if meta['checkpoint_revision']!=manifest['source']['checkpoint_revision'] or meta['tp']!=8:
                    raise ValueError('native source checkpoint/TP mismatch')
                lines=(native/'matrix_scale_bf16.hex').read_text().splitlines()
                for name in ('qkv','gu'):
                    row=next(x for x in meta['matrix_layout'] if x['name']==name)
                    bits=np.array([(int(lines[row['scale_base']+r//16],16)>>(16*(r%16)))&65535
                                   for r in range(row['rows'])],dtype=np.uint32)<<16
                    if not np.array_equal(bits,scales[name].view(np.uint32)):
                        raise ValueError(f'L{n} native {name} scale subset mismatch')
                    checks[name]=len(bits)
                nl=[int(x,16)&((1<<32)-1) for x in (native/'crom.hex').read_text().splitlines()]
                for name,base,data in (('ps1',meta['post_tp_scale_bases'][0],ps1),
                    ('ps2',meta['post_tp_scale_bases'][1],ps2),('q_norm',4096,qn),('k_norm',4608,kn)):
                    if not np.array_equal(np.array(nl[base:base+len(data)],dtype=np.uint32),data.view(np.uint32)):
                        raise ValueError(f'L{n} native {name} mismatch')
                    checks[name]=len(data)
            slices=[]
            for s in range(12):
                slices.append(dict(slice=s,prog_users=progs[s],
                    btab=[dict(addr=addr,payload_hex=f'{pay:0256x}') for addr,pay in b[s]],
                    crom=[dict(addr=addr,payload_hex=f'{pay:0256x}') for dst,addr,pay in c if dst in (s,15)]))
            manifest['stages'].append(dict(stage=n+1,slices=slices))
            manifest['receipts'].append(dict(layer=n,npz=e['npz'],npz_sha256=e['npz_sha256'],
                source_image_sha256=e['image_sha256'],native_checks=checks))
            print(f'L{n}: payload PASS native={checks}',flush=True)
    PS.logical_images(manifest)
    path=a.out/'table_manifest.json';path.write_text(json.dumps(manifest,separators=(',',':'))+'\n')
    print('ALL36_STATIC_TABLE_MANIFEST_PASS',sha(path),flush=True)


if __name__=='__main__':main()
