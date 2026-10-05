#!/usr/bin/env python3
"""Qualify/reuse one released raw HE image for the existing S81 minimum provider."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import tempfile
import time

import numpy as np
from dsrom_checkpoint import Checkpoint, DEFAULT_CHECKPOINT, SNAPSHOT
from v41_fullshape_weight_layout import pack_he_fp32, verify_he

ROOT=Path(__file__).resolve().parents[1]
TENSOR='layers.0.hc_attn_fn'
LAYOUT='HHW8 bankline=(wbase+row*320+run)*8+term lane=chunk'
ROWS,K,DEPTH,LINES=24,20480,7680,61440


def sha(data):
    return hashlib.sha256(data).hexdigest()


def literal_operation():
    path=ROOT/'tools/runtime/dsrom/s81_minimum_prefix.cpp'
    row=next(line for line in path.read_text().splitlines() if 'DsromS81PrefixOperation{1, 5,' in line)
    words=[int(s,16) for s in re.findall(r'0x([0-9a-fA-F]+)u',row)]
    if len(words)!=64:
        raise ValueError('literal L0I1 instruction shape')
    instruction=sum(w<<(32*i) for i,w in enumerate(words))
    field=lambda lo,n:(instruction>>lo)&((1<<n)-1)
    record=dict(he_nout=field(1563,21),he_k=field(1584,21),he_wbase=field(1605,30))
    if record!=dict(he_nout=24,he_k=2560,he_wbase=0):
        raise ValueError('literal L0I1 not admitted HE scope')
    record.update(source_sha256=sha(path.read_bytes()),instruction_sha256=sha(instruction.to_bytes(256,'little')))
    return record


def extract(path, expected_sha):
    raw=path.read_bytes()
    if sha(raw)!=expected_sha:
        raise ValueError('existing hbank changed from its image manifest')
    words=[];address=0
    for line in raw.decode('ascii').splitlines():
        if not line:
            continue
        if line.startswith('@'):
            address=int(line[1:],16)
            continue
        if address>=LINES:
            break
        if address!=len(words) or len(line)!=64 or not re.fullmatch('[0-9a-fA-F]{64}',line):
            raise ValueError('HE prefix missing/duplicate/wrong-width address')
        words.append(line);address+=1
    if len(words)!=LINES:
        raise ValueError('incomplete HE image prefix')
    image=np.empty((DEPTH,8,8),dtype='<u4')
    flat=image.reshape(LINES,8)
    for i,line in enumerate(words):
        for lane in range(8):
            flat[i,lane]=int(line[56-8*lane:64-8*lane],16)
    return image,('@0\n'+'\n'.join(words)+'\n').encode('ascii')


def write_exclusive(path,data):
    # Publish fully written data without ever replacing an existing artifact.
    with tempfile.NamedTemporaryFile(dir=path.parent,prefix='.'+path.name+'.',delete=False) as f:
        temporary=Path(f.name)
        try:
            f.write(data);f.flush();os.fsync(f.fileno())
            os.link(temporary,path)
        finally:
            temporary.unlink(missing_ok=True)


def emit(checkpoint,selected,reuse=None,manifest=None):
    start=time.monotonic()
    operation=literal_operation()
    selected=Path(selected)
    if not selected.is_dir():
        raise ValueError('existing selected directory required')
    for name in ('hbank.hex','hbank.source','hbank.receipt.json'):
        if (selected/name).exists():
            raise FileExistsError('preserve existing artifact: '+str(selected/name))
    checkpoint=Path(checkpoint)
    if checkpoint.resolve().name!=SNAPSHOT:
        raise ValueError('released snapshot required')
    source=Checkpoint(checkpoint)
    try:
        fd,base,descriptor=source.descriptor(TENSOR)
        if descriptor['dtype']!='F32' or descriptor['shape']!=[ROWS,K]:
            raise ValueError('actual F32[24,20480] tensor required')
        raw=source.raw(TENSOR,0,ROWS*K*4)
        bits=np.frombuffer(raw,dtype='<u4').reshape(ROWS,K)
        geom=dict(banks=8,hhw=8,words_per_row=320,word_count=DEPTH,
                  image_bytes=len(raw),base_word=0,end_word_exclusive=DEPTH)
        reuse_record=None
        if reuse is not None:
            if manifest is None:
                raise ValueError('reused image requires its original manifest')
            book=json.loads(Path(manifest).read_text())
            if book.get('rank')!=0 or book.get('schema')!='opentallas.rtl.w17_die_l0_images.v1.rank':
                raise ValueError('wrong existing image source scope')
            expected=book['images']['hbank.hex']
            image,hex_bytes=extract(Path(reuse),expected)
            reuse_record=dict(image=str(reuse),image_sha256=expected,
                              manifest=str(manifest),manifest_sha256=sha(Path(manifest).read_bytes()))
        else:
            # Existing packer only: no new packing code, activations or arithmetic.
            image,packed_geom=pack_he_fp32(bits,base_word=0,hhw=8)
            if packed_geom!=geom:
                raise ValueError('existing packer geometry mismatch')
            lines=[''.join(f'{int(v):08x}' for v in word[::-1]) for word in image.reshape(LINES,8)]
            hex_bytes=('@0\n'+'\n'.join(lines)+'\n').encode('ascii')
        # Existing readback validator checks all491520 uint32 values exactly.
        verify_he(image,bits,geom)
        decoded=image.transpose(0,2,1).reshape(ROWS,K).tobytes()
        if decoded!=raw:
            raise ValueError('independent raw-byte inversion mismatch')
        hex_sha=sha(hex_bytes)
        meta=('\n'.join((SNAPSHOT,TENSOR,'F32 24 20480',LAYOUT,hex_sha))+'\n').encode()
        st=os.fstat(fd)
        record=dict(schema='opentallas.dsrom.s81.minimum-HE-image.r1',
            scope='one L0I1 raw immutable HE tensor, no activations/field/allocator/numerical simulation',
            snapshot=SNAPSHOT,tensor=TENSOR,descriptor=descriptor,source_byte_sha256=sha(raw),
            source_bytes=len(raw),checkpoint=str(checkpoint.resolve()),
            checkpoint_index_sha256=sha((checkpoint/'model.safetensors.index.json').read_bytes()),
            shard=source.index[TENSOR],shard_header_data_base=base,
            shard_identity=dict(device=st.st_dev,inode=st.st_ino,bytes=st.st_size,mtime_ns=st.st_mtime_ns),
            geometry=geom,bank_lines=LINES,layout=LAYOUT,literal_L0I1=operation,reused_image=reuse_record,
            exact_raw_values=ROWS*K,independent_inverse_sha256=sha(decoded),
            hbank_sha256=hex_sha,hbank_bytes=len(hex_bytes),hbank_source_sha256=sha(meta),
            emitter_sha256=sha(Path(__file__).read_bytes()),
            existing_code_sha256={p:sha((ROOT/p).read_bytes()) for p in ('tools/dsrom_checkpoint.py',
                'tools/v41_fullshape_weight_layout.py','tools/v41_die_l0_images.py',
                'tools/runtime/dsrom/s81_minimum_he_bootstrap_provider.cpp')},
            resource=dict(elapsed_seconds=time.monotonic()-start,
                peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                source_read_bytes=source.read_bytes,added_image_bytes=len(hex_bytes),
                no_execution_caps=True,hardware_model_delta=0),
            selected_directory=str(selected),status='PASS_RELEASED_HE_RAW_IMAGE_ONLY')
        # Metadata is published last: the consumer cannot accept a partial image.
        write_exclusive(selected/'hbank.hex',hex_bytes)
        write_exclusive(selected/'hbank.receipt.json',(json.dumps(record,indent=2)+'\n').encode())
        write_exclusive(selected/'hbank.source',meta)
        return record
    finally:
        source.close()


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--checkpoint',type=Path,default=DEFAULT_CHECKPOINT)
    ap.add_argument('--selected-dir',type=Path,required=True)
    ap.add_argument('--reuse-hbank',type=Path)
    ap.add_argument('--reuse-manifest',type=Path)
    a=ap.parse_args()
    print(json.dumps(emit(a.checkpoint,a.selected_dir,a.reuse_hbank,a.reuse_manifest),indent=2))


if __name__=='__main__':main()
