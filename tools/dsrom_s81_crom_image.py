#!/usr/bin/env python3
"""Reuse immutable L0 rank0 CROM; qualify actual SUN256 I6 gamma from raw checkpoint bits."""
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


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--checkpoint',type=Path,default=DEFAULT_CHECKPOINT)
    ap.add_argument('--selected-dir',type=Path,required=True)
    ap.add_argument('--reuse-crom',type=Path,required=True)
    ap.add_argument('--reuse-manifest',type=Path,required=True)
    a=ap.parse_args()
    print(json.dumps(emit(a.checkpoint,a.selected_dir,a.reuse_crom,a.reuse_manifest),indent=2))


if __name__=='__main__':main()
