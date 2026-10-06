#!/usr/bin/env python3
"""Prepare existing released inputs for the actual NS2 parent; no build/run.

Run on the compute host with the retained stage directory. Sparse readmemh
images preserve selected MEM_WORDS=2097152 and the real zero initializer.
Separate die prefixes are mandatory; a common plusarg aliases two providers.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

PIN = '2b12e330d841ae5f9affb3776ff638dcb1135487'
RETAINED = {
 'x.mem': ('afa68c72c5a4233b2dba671efdbd41b647c24cf07f83865524eb1b63ed283566',20480,32),
 'w.mem': ('93e4e41f7cb05544c846b3316c0866659ac28c7e64a9820ec491f7b0f82a3f52',5120,32),
 'cfg.mem': ('b88aa9d6b0933b929cd9481dffe8b471ee4d0ca6e5df2012e8250186f79679b0',6,32),
 'ey.mem': ('c1dc401770017fad13fdf96bde3f305baadb17b139e30334f7c6c0adcedfca47',5120,32),
 'eqc.mem': ('279e90327e21465622d703455303efb78dd4525cb4756fa9e41d6412177a68de',160,256),
 'eqe.mem': ('a9a5537e0d27665ac84ff25aa758b6833955a386d9cefa14aad0da6d6e1fc394',160,16),
 'eqy.mem': ('2ec27a9bd55debace006c7134037a22b4c47ae2ee2f252fd3172aebb29eac00b',160,512),
}

def prepare(source, output, sfu_vectors=None):
    values = {}
    for name, (expected, count, width) in RETAINED.items():
        data = (source/name).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError(f'retained source hash mismatch: {name}')
        words = data.decode('ascii').split()
        if len(words) != count or any(len(w) != width//4 for w in words):
            raise ValueError(f'retained shape mismatch: {name}')
        values[name] = [int(w,16) for w in words]
    sfu = None
    if sfu_vectors is not None:
        pins = {'sfu_req.mem':'ee4368a489f47aff06d2989932e3ed484317d7111cdab22d3cab99881fb6fd98',
                'sfu_exp.mem':'6bdb97af9088f04dd8b1db1bd56d6c39d6c9a747f7153aea3ab83cf2d3f1172b'}
        cases = {}
        for name, expected in pins.items():
            data = (sfu_vectors/name).read_bytes()
            if hashlib.sha256(data).hexdigest() != expected:
                raise ValueError(f'retained SFU source hash mismatch: {name}')
            words=data.decode('ascii').split()
            if len(words)!=10 or any(len(w)!=521 for w in words):
                raise ValueError(f'retained SFU2083/2081 shape mismatch: {name}')
            cases[name]=int(words[1],16)
        req, exp=cases['sfu_req.mem'],cases['sfu_exp.mem']
        changed=sum(((req>>(32*i))&0xffffffff)!=((exp>>(32*i))&0xffffffff) for i in range(64))
        if req>>2048&7!=1 or req>>2051!=0xc5000001 or exp>>2048&1 or exp>>2049!=0xc5000001 or changed!=64:
            raise ValueError('SFU continuation must select actual nonidentity CASE1')
        sfu={'case':1,'fn':1,'tag':0xc5000001,'changed_lanes':changed,
             'source_byte_base':0xa0000,'source_byte_limit':0xa0100,
             'native_output_base':64,'native_output_span':64,'source_sha256':pins}
    # First validate all retained sources; then create a fresh immutable attempt.
    output.mkdir(parents=True, exist_ok=False)
    (output/'gold').mkdir()
    for name in RETAINED:
        shutil.copyfile(source/name,output/'gold'/name)
    if sfu is not None:
        for name in sfu['source_sha256']:
            shutil.copyfile(sfu_vectors/name,output/'gold'/name)
    source_words = values['x.mem']+values['w.mem']
    rows = [{}, {}]
    for word, value in enumerate(source_words):
        address = word*4
        slice_index = (address >> 7) & 1
        local = ((address >> 8) << 7) | (address & 127)
        sector, lane = local >> 5, address & 31
        if sector >= 2097152:
            raise ValueError('actual selected provider aliases source address')
        rows[slice_index][sector] = rows[slice_index].get(sector,0) | (value << (lane*8))
    if sfu is not None:
        req=cases['sfu_req.mem']
        for word in range(64):
            address=0xa0000+word*4
            slice_index=(address>>7)&1
            local=((address>>8)<<7)|(address&127)
            sector,lane=local>>5,address&31
            rows[slice_index][sector]=rows[slice_index].get(sector,0)|(((req>>(word*32))&0xffffffff)<<(lane*8))
    for die in range(2):
        for partition in range(2):
            image = rows[partition] if die == 0 else {0:0}
            path = output/f'die{die}_p{partition}.hex'
            with path.open('x') as f:
                for sector, value in sorted(image.items()):
                    f.write(f'@{sector:x}\n{value:064x}\n')
    # Independently decode every written source word through the actual NS2 map.
    for word, expected in enumerate(source_words):
        byte = word*4
        partition=(byte>>7)&1
        sector=(((byte>>8)<<7)|(byte&127))>>5
        actual=(rows[partition][sector] >> ((byte&31)*8)) & 0xffffffff
        if actual != expected:
            raise ValueError(f'provider image mapping failed at WORD{word}')
    files = {p.name:hashlib.sha256(p.read_bytes()).hexdigest()
             for p in output.glob('die*_p*.hex')}
    manifest = {
      'stage':'L20.attn.hc_pre_norm', 'initial_parent_pin':PIN,
      'parent_enrollment_source_repair_required':True,
      'ND':2,'NSM':2,'NS':2,'NPC':2,'MEM_WORDS':2097152,
      'provider_cp_word_aperture':[0,25600], 'xbase':0,'gain_base':20480,
      'native_output_base':3584,'native_output_span':12800,
      'quant_base_parent_derived':8704,'last_word':16383,
      'source_sha256':{name:v[0] for name,v in RETAINED.items()},
      'images_sha256':files,'input_mapping_words_checked':len(source_words),
      'runtime_verdict':None,'full_token_qualified':False,'physical_qualified':False,
      'SFU_execution_covered':False,'formatter_execution_covered':False,
      'SFU_continuation_prepared':sfu,
    }
    (output/'fixture_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest

if __name__ == '__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--retained-stage',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--sfu-vectors',type=Path,help='optional authentic existing enabled_r1/vectors; prepares CASE1 only')
    args=ap.parse_args()
    result=prepare(args.retained_stage,args.output,args.sfu_vectors)
    print(json.dumps({'prepared':str(args.output),'input_mapping_words_checked':result['input_mapping_words_checked'],'runtime_verdict':None}))
