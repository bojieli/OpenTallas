#!/usr/bin/env python3
"""Enroll native SU CROM: retained L0 I6 or released L20 per-node constants."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import tempfile
import time

from dsrom_checkpoint import Checkpoint, DEFAULT_CHECKPOINT, SNAPSHOT

ROOT=Path(__file__).resolve().parents[1]
MODEL='results/uarch/dsrom_sun256_native_prefix_20261004/model.json'
TENSOR='layers.0.attn_norm.weight'


def sha(data):return hashlib.sha256(data).hexdigest()


def parse_crom(raw):
    words={};address=0
    for line in raw.decode('ascii').splitlines():
        for token in line.split('//',1)[0].split():
            if token.startswith('@'):
                address=int(token[1:],16)
                if not 0<=address<1<<19:raise ValueError('CROM address19')
            else:
                if len(token)>16 or address in words or not 0<=address<1<<19:
                    raise ValueError('CROM width/duplicate/address')
                word=int(token,16)
                if not 0<=word<1<<64:raise ValueError('CROM unsigned word64')
                words[address]=word;address+=1
    return words


def qualify_gamma(words,raw,dtype,external):
    width={'BF16':2,'F32':4}.get(dtype)
    if width is None or len(raw)%width:
        raise ValueError('raw gamma dtype/width')
    count=len(raw)//width
    expected={(1,i) for i in range(count)}
    if len(external)!=count or set(map(tuple,external))!=expected:
        raise ValueError('external source gamma coverage/source1 mapping')
    for i in range(count):
        bits=int.from_bytes(raw[width*i:width*(i+1)],'little')
        if dtype=='BF16':bits<<=16 # exact BF16 embedding in FP32; no arithmetic
        if i not in words or (words[i]&0xffffffff)!=bits:
            raise ValueError('released gamma rawbits mismatch/address '+str(i))
    return count


def write_exclusive(path,data):
    with tempfile.NamedTemporaryFile(dir=path.parent,prefix='.'+path.name+'.',delete=False) as f:
        temp=Path(f.name)
        try:
            f.write(data);f.flush();os.fsync(f.fileno());os.link(temp,path)
        finally:
            temp.unlink(missing_ok=True)


def emit(checkpoint,selected,reuse,manifest):
    start=time.monotonic()
    selected=Path(selected)
    if not selected.is_dir():raise ValueError('existing selected directory required')
    if any((selected/name).exists() for name in ('crom.hex','crom.receipt.json')):
        raise FileExistsError('preserve existing CROM artifacts')
    model_raw=(ROOT/MODEL).read_bytes();model=json.loads(model_raw)
    external=[e for op in model['prefix_operations'] for e in op['external_source_addresses']]
    ops=[op for op in model['prefix_operations'] if op['external_source_addresses']]
    if len(ops)!=1 or ops[0]['pc']!=6 or external!=[[1,i] for i in range(5120)]:
        raise ValueError('actual model requires unsupported external tensor/layout')
    book_raw=Path(manifest).read_bytes();book=json.loads(book_raw)
    image_raw=Path(reuse).read_bytes()
    if book['schema']!='opentallas.rtl.w17_die_l0_images.v1.rank' or book['rank']!=0 or sha(image_raw)!=book['images']['crom.hex']:
        raise ValueError('existing L0 rank0 CROM source manifest mismatch')
    words=parse_crom(image_raw)
    checkpoint=Path(checkpoint)
    if checkpoint.resolve().name!=SNAPSHOT:raise ValueError('released snapshot required')
    source=Checkpoint(checkpoint)
    try:
        fd,base,descriptor=source.descriptor(TENSOR)
        if descriptor['shape']!=[5120] or descriptor['dtype'] not in ('BF16','F32'):
            raise ValueError('released norm gamma shape/type')
        raw=source.raw(TENSOR,0,descriptor['data_offsets'][1]-descriptor['data_offsets'][0])
        values=qualify_gamma(words,raw,descriptor['dtype'],external)
        st=os.fstat(fd)
        record=dict(schema='opentallas.dsrom.s81.minimum-CROM-image.r1',status='PASS_RELEASED_I6_CROM_RAW_GAMMA_ONLY',
            scope='raw immutable constants artifact for existing native SU; no activations/inference/field image',
            snapshot=SNAPSHOT,tensor=TENSOR,descriptor=descriptor,source_byte_sha256=sha(raw),
            source_bytes=len(raw),checkpoint=str(checkpoint.resolve()),
            checkpoint_index_sha256=sha((checkpoint/'model.safetensors.index.json').read_bytes()),
            shard=source.index[TENSOR],shard_header_data_base=base,
            shard_identity=dict(device=st.st_dev,inode=st.st_ino,bytes=st.st_size,mtime_ns=st.st_mtime_ns),
            model=str(ROOT/MODEL),model_sha256=sha(model_raw),
            external=dict(pc=6,source=1,addresses=[0,5120],exact_values=values,
                literal_sha256=ops[0]['literal_sha256'],source1='low32',source2='high32',
                conversion='BF16 rawbits <<16; F32 rawbits unchanged; no host FP calculation'),
            reused_image=str(reuse),reused_image_manifest=str(manifest),reused_image_manifest_sha256=sha(book_raw),
            crom_sha256=sha(image_raw),crom_bytes=len(image_raw),image_entries=len(words),
            copy_byte_identical=True,all_unrequested_words='retained original bytes; not newly numerically qualified',
            selected_directory=str(selected),env='DSROM_S81_MINIMUM_CROM_HEX='+str(selected/'crom.hex'),
            emitter_sha256=sha(Path(__file__).read_bytes()),
            source_sha256={p:sha((ROOT/p).read_bytes()) for p in ('tools/dsrom_checkpoint.py',
                'tools/v41_die_l0_images.py','tools/runtime/dsrom/s81_minimum_su256.cpp')},
            resource=dict(elapsed_seconds=time.monotonic()-start,
                peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                source_read_bytes=source.read_bytes,added_image_bytes=len(image_raw),
                hardware_model_delta=0,no_execution_caps=True))
        write_exclusive(selected/'crom.hex',image_raw)
        write_exclusive(selected/'crom.receipt.json',(json.dumps(record,indent=2)+'\n').encode())
        return record
    finally:source.close()


# Existing layer20 binder owns these addresses; payload is raw released storage.
L20_BINDER='results/rtl/hdc_v41x_fullshape_1m_s20260930_l20_program_bind_rope_hbm.json'
L20_TENSORS={
    'attn_norm':'attn_norm.weight', 'ffn_norm':'ffn_norm.weight',
    'q_norm':'attn.q_norm.weight', 'kv_norm':'attn.kv_norm.weight',
    'hc_attn_scale':'hc_attn_scale', 'hc_attn_base':'hc_attn_base',
    'hc_ffn_scale':'hc_ffn_scale', 'hc_ffn_base':'hc_ffn_base',
    'attn_sink':'attn.attn_sink', 'gate.bias':'ffn.gate.bias',
    'compressor.norm':'attn.compressor.norm.weight',
    'indexer.k_norm':'attn.indexer.k_norm.weight',
}


def emit_layer20(checkpoint,selected,rank):
    start=time.monotonic();selected=Path(selected)
    if rank not in range(4) or not selected.is_dir():
        raise ValueError('existing selected directory and actual TP4 rank required')
    if any((selected/name).exists() for name in ('crom.hex','crom.receipt.json')):
        raise FileExistsError('preserve existing CROM artifacts')
    binder_raw=(ROOT/L20_BINDER).read_bytes();binder=json.loads(binder_raw)
    if binder['layer']!=20 or binder['rank']!=0:
        raise ValueError('current layer20 rank0 canonical binder required')
    layout_path=binder['layout_path'];layout_raw=(ROOT/layout_path).read_bytes()
    if sha(layout_raw)!=binder['layout_sha256']:
        raise ValueError('current binder layout source mismatch')
    spans=json.loads(layout_raw)['constants']
    if set(spans)!=set(L20_TENSORS)|{'pre0'}:
        raise ValueError('unsupported layer20 constant set')
    checkpoint=Path(checkpoint)
    if checkpoint.resolve().name!=SNAPSHOT:raise ValueError('released snapshot required')
    source=Checkpoint(checkpoint);words={};records={}
    try:
        for name,tensor_suffix in L20_TENSORS.items():
            tensor='layers.20.'+tensor_suffix
            fd,base,descriptor=source.descriptor(tensor)
            span=spans[name];dtype=descriptor['dtype'];width={'BF16':2,'F32':4}.get(dtype)
            if width is None or dtype!=span['source_format'] or len(descriptor['shape'])!=1:
                raise ValueError('released constant dtype/shape: '+tensor)
            count=descriptor['shape'][0]
            expected=3 if name.endswith('_scale') else 64 if name=='attn_sink' else span['word_count']
            if count!=expected or descriptor['data_offsets'][1]-descriptor['data_offsets'][0]!=count*width:
                raise ValueError('released constant extent: '+tensor)
            first=rank*16 if name=='attn_sink' else 0
            taken=16 if name=='attn_sink' else count
            raw=source.raw(tensor,first*width,taken*width)
            payload=[int.from_bytes(raw[i:i+width],'little') for i in range(0,len(raw),width)]
            if dtype=='BF16':payload=[v<<16 for v in payload]
            if name.endswith('_scale'):
                payload=[payload[0]]*4+[payload[1]]*4+[payload[2]]*16
            packed=b''.join(v.to_bytes(8,'little') for v in payload)
            if len(payload)!=span['word_count']:
                raise ValueError('binder constant word count: '+name)
            # Rank0 matches every original binder hash. Only sinks are TP-sliced.
            if name!='attn_sink' or rank==0:
                if sha(raw)!=span['source_tensor_sha256'] or sha(packed)!=span['output_image_sha256']:
                    raise ValueError('released payload differs from actual binder: '+name)
            address=span['base_word']
            if address<0 or address+len(payload)>1<<19:
                raise ValueError('layer20 CROM address19')
            for i,v in enumerate(payload):
                if address+i in words:raise ValueError('overlapping bound constants')
                words[address+i]=v
            st=os.fstat(fd)
            records[name]=dict(tensor=tensor,descriptor=descriptor,source_dtype=dtype,
                source_element_range=[first,first+taken],source_byte_sha256=sha(raw),
                source_bytes=len(raw),base_word=address,word_count=len(payload),
                output_image_sha256=sha(packed),shard=source.index[tensor],
                shard_header_data_base=base,
                shard_identity=dict(device=st.st_dev,inode=st.st_ino,bytes=st.st_size,mtime_ns=st.st_mtime_ns),
                endpoint_raw32=[payload[0],payload[-1]],
                conversion='BF16 rawbits <<16 or F32 unchanged; HC scale repeats4/4/16; high32 +0')
        # Preserve the binder's source-generated Layout constant, not a tensor.
        pre=spans['pre0'];pre_payload=[0x3f800000,0,0,0]
        if pre['word_count']!=4 or pre['generated_rule']!='hdc_program_v41.Layout: [1.0, 0.0, 0.0, 0.0]' or \
                sha(b''.join(v.to_bytes(8,'little') for v in pre_payload))!=pre['output_image_sha256']:
            raise ValueError('source-generated pre0 rule mismatch')
        for i,v in enumerate(pre_payload):
            a=pre['base_word']+i
            if not 0<=a<1<<19 or a in words:raise ValueError('pre0 address/overlap')
            words[a]=v
        records['pre0']=dict(base_word=pre['base_word'],word_count=4,generated_rule=pre['generated_rule'])
        image_raw=(''.join('@%x\n%016x\n'%(a,v) for a,v in sorted(words.items()))).encode('ascii')
        if parse_crom(image_raw)!=words:raise ValueError('actual emitted CROM rawbit readback')
        record=dict(schema='opentallas.dsrom.s81.minimum-CROM-image.r1',
            status='PASS_RELEASED_LAYER20_CROM_RAW_CONSTANTS_ONLY',layer=20,rank=rank,
            scope='raw released layer20 constants for existing native SU; no activation/golden intermediate/inference',
            snapshot=SNAPSHOT,checkpoint=str(checkpoint.resolve()),
            checkpoint_index_sha256=sha((checkpoint/'model.safetensors.index.json').read_bytes()),
            constants=records,binder=L20_BINDER,binder_sha256=sha(binder_raw),
            layout=layout_path,layout_sha256=sha(layout_raw),
            crom_sha256=sha(image_raw),crom_bytes=len(image_raw),image_entries=len(words),
            selected_directory=str(selected),env='DSROM_S81_MINIMUM_CROM_HEX='+str(selected/'crom.hex'),
            emitter_sha256=sha(Path(__file__).read_bytes()),
            source_sha256={p:sha((ROOT/p).read_bytes()) for p in (
                'tools/dsrom_checkpoint.py','tools/v41_fullshape_weight_layout.py',
                'tools/dsrom_s81_l20_sim_only.py','tools/runtime/dsrom/s81_minimum_su256.cpp',
                'tools/runtime/dsrom/s81_minimum_su256_constants.hpp')},
            resource=dict(elapsed_seconds=time.monotonic()-start,
                peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                source_read_bytes=source.read_bytes,added_image_bytes=len(image_raw),
                hardware_model_delta=0,no_execution_caps=True))
        write_exclusive(selected/'crom.hex',image_raw)
        write_exclusive(selected/'crom.receipt.json',(json.dumps(record,indent=2)+'\n').encode())
        return record
    finally:source.close()


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--checkpoint',type=Path,default=DEFAULT_CHECKPOINT)
    ap.add_argument('--selected-dir',type=Path,required=True)
    ap.add_argument('--layer',type=int,choices=(0,20),default=0)
    ap.add_argument('--rank',type=int,choices=range(4),default=0)
    ap.add_argument('--reuse-crom',type=Path)
    ap.add_argument('--reuse-manifest',type=Path)
    a=ap.parse_args()
    if a.layer==20:
        if a.reuse_crom or a.reuse_manifest:ap.error("L20 export reads actual released tensors, not a reused L0 image")
        result=emit_layer20(a.checkpoint,a.selected_dir,a.rank)
    else:
        if a.rank!=0 or not a.reuse_crom or not a.reuse_manifest:
            ap.error("legacy L0 requires rank0, --reuse-crom and --reuse-manifest")
        result=emit(a.checkpoint,a.selected_dir,a.reuse_crom,a.reuse_manifest)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
