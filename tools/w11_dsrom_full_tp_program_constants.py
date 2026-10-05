#!/usr/bin/env python3
"""All40+head source-pinned software CROM writer; no physical allocation."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import w11_dsrom_full_tp_program_contract as C


def sha(raw):return hashlib.sha256(raw).hexdigest()

def bind_head_norm(instructions,manifest,rank,image_dir):
    """Relocate only head norm CROM operands to a verified produced image."""
    import copy
    import hdc_isa_v41 as I
    record=manifest['rank_images'][rank]
    raw=(Path(image_dir)/record['image']).read_bytes()
    if sha(raw)!=record['image_sha256']:raise ValueError('produced CROM imageSHA mismatch')
    entry=record['constants']['norm.weight']
    if entry['word_count']!=5120 or entry['end_word_exclusive']>record['capacity_words']:
        raise ValueError('finalnorm extent invalid')
    result=copy.deepcopy(instructions);patched=0
    for op in result:
        if op.get('unit')==I.UNIT_SU and op.get('c_src')==I.SRC_CLO:
            if op.get('su_nin')!=5120 or op.get('c_base',0)!=0:raise ValueError('unexpected headnorm template')
            op['c_base']=entry['base_word'];patched+=1
    if patched!=1:raise ValueError('headnorm template binding must be unique')
    return result


def convert(raw,dtype,name,rank):
    """Bit-preserving golden widening, followed by explicit HC/rank layout."""
    if dtype=='BF16':
        if len(raw)%2:raise ValueError('odd BF16 source')
        bits=np.frombuffer(raw,dtype='<u2').astype('<u4')<<16
    elif dtype=='F32':
        if len(raw)%4:raise ValueError('misaligned FP32 source')
        bits=np.frombuffer(raw,dtype='<u4').copy()
    else:raise ValueError('unsupported source dtype')
    if name.endswith(('hc_attn_scale','hc_ffn_scale')):
        if dtype!='F32' or len(bits)!=3:raise ValueError('HC scale requires3FP32')
        bits=np.repeat(bits,[4,4,16])
    if name.endswith('.attn_sink'):
        if len(bits)!=64:raise ValueError('sink requires64FP32')
        bits=bits[rank*16:(rank+1)*16]
    words=np.zeros((len(bits),2),dtype='<u4');words[:,0]=bits
    return words.tobytes()


def write_images(source_manifest,out,capacity_words,*,recipe_pin=C.MAIN_BINDING_PIN):
    source_manifest=Path(source_manifest);out=Path(out)
    rawman=source_manifest.read_bytes();man=json.loads(rawman)
    if not man.get('checkpoint'):raise ValueError('checkpoint provenance missing')
    recipes,recipe_ref=C.read(recipe_pin,C.MAIN_BINDING)
    required={k:v for k,v in recipes['recipes'].items() if v.get('output_word_bits')==64}
    names=sorted(k for k in required if k!='norm.weight')+['norm.weight']
    if len(required)!=409:raise ValueError('incomplete all40+head recipe coverage')
    prepared={}
    # Validate everything before writing any destination files.
    for name in names:
        spec=required[name];entry=man['tensors'].get(name)
        if entry is None:raise ValueError('missing '+name)
        path=Path(entry['path']);path=path if path.is_absolute() else source_manifest.parent/path
        raw=path.read_bytes()
        if sha(raw)!=entry['sha256']:raise ValueError('sourceSHA mismatch '+name)
        if entry['dtype']!=spec['stored_dtype'] or entry['shape']!=spec['stored_shape']:
            raise ValueError('source shape/dtype mismatch '+name)
        expected=int(np.prod(entry['shape']))*(2 if entry['dtype']=='BF16' else 4)
        if len(raw)!=expected:raise ValueError('source byte extent mismatch '+name)
        prepared[name]=(raw,entry)
    if not isinstance(capacity_words,int) or capacity_words<=0 or capacity_words>2**30:
        raise ValueError('capacity outside A30')
    rank_records=[];outputs=[]
    for rank in range(4):
        parts=[];entries={};base=0
        for name in names:
            raw,entry=prepared[name];packed=convert(raw,entry['dtype'],name,rank);count=len(packed)//8
            if count!=required[name]['output_words_per_reference_view']:raise ValueError('recipe extent mismatch '+name)
            if base+count>capacity_words:raise ValueError('CROM capacity exceeded')
            entries[name]={'base_word':base,'word_count':count,'end_word_exclusive':base+count,
                'source':entry,'source_sha256':sha(raw),'output_slice_sha256':sha(packed),
                'format':'FP32_lo_plus_zero_hi','rank':rank}
            parts.append(packed);base+=count
        image=b''.join(parts);filename=f'rank{rank}.crom.bin'
        outputs.append((filename,image))
        rank_records.append({'rank':rank,'image':filename,'image_sha256':sha(image),'image_bytes':len(image),
            'used_words':base,'capacity_words':capacity_words,'constants':entries,
            'finalnorm_base_word':entries['norm.weight']['base_word'],'physical_home':None})
    if out.exists() and any(out.iterdir()):raise ValueError('refuse overwrite existing evidence/output')
    out.mkdir(parents=True,exist_ok=True)
    for filename,image in outputs:
        with (out/filename).open('xb') as f:f.write(image)
    result={'schema':'opentallas.w11.full40-head-crom-images.v1','checkpoint':man['checkpoint'],
        'source_manifest':str(source_manifest),'source_manifest_sha256':sha(rawman),
        'writer_sha256':sha(Path(__file__).read_bytes()),'recipe_source':recipe_ref,
        'rank_images':rank_records,'software_image_binding':True,'physical_allocation':False,
        'hardware_admission':False,'ISA_execution_pass':False,'jobs_launched':0}
    with (out/'manifest.json').open('x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--source-manifest',required=True,type=Path)
    p.add_argument('--out',required=True,type=Path);p.add_argument('--capacity-words',required=True,type=int)
    a=p.parse_args();r=write_images(a.source_manifest,a.out,a.capacity_words)
    print(json.dumps({'manifest':str(a.out/'manifest.json'),'used_words_per_rank':[x['used_words'] for x in r['rank_images']]}))
if __name__=='__main__':main()
