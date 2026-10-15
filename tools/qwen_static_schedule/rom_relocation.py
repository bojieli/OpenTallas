#!/usr/bin/env python3
"""Bind resident TP8 ROM addresses to ALL actual released stage programs.

Reads immutable metadata and encoded programs, not checkpoint tensors. Scale
payload-byte equality and per-instance macro IDs belong to the native memory
builder. This consumer proves that compiler addresses select their exact
stage-local allocation in that resident layout, including physical padding.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import hdc_isa as ISA


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def stage_bases(stage):
    if not 1<=stage<=37:raise ValueError('ROM stage must be actual layer1..36 or head37')
    return ((18432,29376,1600,1200) if stage==37 else ((stage-1)*512,(stage-1)*816,512,816))


def relocate(stage, fields):
    f=dict(fields)
    if f['me_wsrc']:return f
    cb,sb,cn,sn=stage_bases(stage)
    if not 0<=f['me_wbase']<cn or not 0<=f['me_wcs']<sn:raise ValueError('actual local command base exceeds resident allocation')
    f['me_wbase']+=cb;f['me_wcs']+=sb
    return f


def check_program(path, stage, layout, *, source=None):
    cb,sb,cn,sn=stage_bases(stage)
    program=[]
    for pc,text in enumerate(path.read_text().split()):
        f=ISA.decode(int(text,16))
        if f['unit']!=1 or f['me_wsrc']:continue
        if f['me_d_k'] or f['me_d_nout'] or f['me_d_tiles'] or f['me_d_wbase']:
            raise ValueError('ROM descriptor has unresolved runtime geometry')
        s=1<<f['me_split']
        if not s or 3072%s:raise ValueError('actual TP8 split must divide3072')
        # Exact physical ROM allocation, not ceil(nout/16): retain final-round padding.
        scale_span=f['me_tiles']*(3072//s)*8
        code_offsets=[r*f['me_ts']+k*f['me_ks']+(j>>f['me_jsh'])*f['me_js'] for r in range(f['me_tiles']) for k in range(f['me_k']) for j in range(8)]
        code_lo=f['me_wbase']+min(code_offsets)
        code_hi=f['me_wbase']+max(code_offsets)+1
        scale_lo=f['me_wcs'];scale_hi=scale_lo+scale_span
        if not 0<=code_lo<code_hi<=cn or not 0<=scale_lo<scale_hi<=sn:raise ValueError('native ROM request leaves actual stage allocation')
        if stage<37:
            matches=[m for m in layout if m['base']==f['me_wbase'] and m['scale_base']==f['me_wcs']]
            if len(matches)!=1:raise ValueError('native local code/scale pair does not name one actual released matrix')
            m=matches[0]
            if (code_lo,code_hi,scale_lo,scale_hi)!=(m['base'],m['end'],m['scale_base'],m['scale_end']):raise ValueError('native command request bounds differ from emitted matrix allocation')
            name=m['name']
        else:name='lm_head'
        g=relocate(stage,f)
        program.append(dict(pc=pc,matrix=name,word=text.zfill(256),local_code=[code_lo,code_hi],local_scale=[scale_lo,scale_hi],resident_code=[cb+code_lo,cb+code_hi],resident_scale=[sb+scale_lo,sb+scale_hi],local_wbase=f['me_wbase'],local_wcs=f['me_wcs'],resident_wbase=g['me_wbase'],resident_wcs=g['me_wcs']))
    if not program:raise ValueError('actual stage has no native ROM operations')
    return dict(stage=stage,program_sha256=sha(path),metadata_sha256=sha(source) if source else None,rom_operations=program)


def build(banks):
    result=[]
    pins={}
    for rank in range(8):
        for layer in range(36):
            meta=banks/f'images/layer{layer}/die{rank}/layer{layer}_rom.json'
            r=json.loads(meta.read_text())
            if (r['tp'],r['die'],r['layer'],r['matrix_words'],r['scale_rom_words'])!=(8,rank,layer,512,816):raise ValueError('actual released image differs from TP8 resident shape')
            path=banks/f'fused_images/layer{layer}/die{rank}/program.hex'
            record=check_program(path,layer+1,r['matrix_layout'],source=meta)
            record.update(rank=rank,scale_image_sha256=r['image_sha256']['matrix_scale_bf16.hex'],code_image_sha256=r['image_sha256']['matrix_int8.hex'] if 'matrix_int8.hex'in r['image_sha256'] else r['image_sha256'])
            result.append(record)
            pins[str(meta.relative_to(banks))]=sha(meta);pins[str(path.relative_to(banks))]=sha(path)
        meta=banks/f'head_images/rank{rank}/head_rom.json';r=json.loads(meta.read_text())
        if (r['tp'],r['die'],r['code_words'],r['scale_words'])!=(8,rank,1600,1200):raise ValueError('actual head shape mismatch')
        path=banks/f'token_source_plan/head_program_rank{rank}.hex'
        record=check_program(path,37,[r['geometry']],source=meta)
        record.update(rank=rank,scale_image_sha256=r['image_sha256']['matrix_scale_bf16.hex'])
        result.append(record);pins[str(meta.relative_to(banks))]=sha(meta);pins[str(path.relative_to(banks))]=sha(path)
    return dict(schema='opentallas.qwen-tp8-native-rom-relocation.v1',status='ACTUAL_PROGRAM_ADDRESS_JOIN_PASS',programs=result,source_image_pins=pins,source_sha256={'tools/hdc_isa.py':sha(Path(ISA.__file__)),'tools/qwen_static_schedule/rom_relocation.py':sha(Path(__file__))},stage_bases=[dict(stage=s,code=stage_bases(s)[0],scale=stage_bases(s)[1])for s in range(1,38)],claim='All296 actual emitted layer/head program address bounds and resident relocations. Released payload byte equality, macro identity and native physical/whole-token execution remain separate memory/integration proofs.')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--banks',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    result=build(a.banks);a.out.write_text(json.dumps(result,indent=2)+'\n');print(result['status'],len(result['programs']))

if __name__=='__main__':main()
