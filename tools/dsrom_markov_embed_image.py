#!/usr/bin/env python3
"""Copy released BF16 bytes into 256-bit ROM payload beats; never requantize."""
import argparse,hashlib,json,struct
from pathlib import Path
KEY='mtp.2.markov_head.embed.weight'
REV='dba1be0a40aa45a94ad051997016db3960a90277'
DEFAULT=Path('/home/ubuntu/.cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4.1-Flash/snapshots')/REV

def source(snapshot):
    index= snapshot/'model.safetensors.index.json'
    name=json.loads(index.read_text())['weight_map'][KEY]
    file=snapshot/name
    with file.open('rb') as f:
        size=struct.unpack('<Q',f.read(8))[0];header=json.loads(f.read(size))
    record=header[KEY]
    if record['dtype']!='BF16' or record['shape']!=[129280,256]:raise ValueError('released shape/dtype mismatch')
    lo,hi=record['data_offsets']
    if hi-lo!=66191360:raise ValueError('released payload size mismatch')
    return file,8+size+lo,dict(checkpoint_revision=REV,index_sha256=hashlib.sha256(index.read_bytes()).hexdigest(),tensor=KEY,shard=name,header_sha256=hashlib.sha256(json.dumps(header,sort_keys=True).encode()).hexdigest())

def generate(snapshot,out,tokens=None):
    file,offset,meta=source(snapshot);out.mkdir(parents=True,exist_ok=True)
    payload=hashlib.sha256();selection={};handles={}
    try:
        with file.open('rb') as f:
            for token in range(129280):
                f.seek(offset+token*512);row=f.read(512)
                if len(row)!=512:raise ValueError('truncated payload')
                payload.update(row)
                if tokens is not None and token not in tokens:continue
                selection[str(token)]=row.hex()
                for beat in range(16):
                    addr=token*16+beat;bank=addr//4096;local=addr%4096
                    if bank not in handles:handles[bank]=(out/f'macro{bank:03}.hex').open('w')
                    word=int.from_bytes(row[beat*32:(beat+1)*32],'little')
                    handles[bank].write(f'@{local:x}\n{word:064x}\n')
    finally:
        for h in handles.values():h.close()
    if tokens is None:
        for macro in range(506):
            image=out/f'macro{macro:03}.hex'
            if not image.exists():image.write_text('@0\n'+'0'*64+'\n')
    spread=[sum(((b>>k)&1)<<(8*k) for k in range(8)) for b in range(256)]
    for image in sorted(out.glob('macro*.hex')):
        physical=[0]*512;address=0
        for line in image.read_text().splitlines():
            if line.startswith('@'):address=int(line[1:],16);continue
            word=int(line,16)
            expanded=sum(spread[(word>>(8*j))&255]<<(64*j) for j in range(32))
            physical[address//8]|=expanded<<(address%8);address+=1
        image.with_suffix('.viamap.hex').write_text('\n'.join(f'{row:0548x}' for row in physical)+'\n')
    meta.update(payload_sha256=payload.hexdigest(),tokens=tokens if tokens is not None else 'all',selected_rows=selection if tokens else {},bank_count=253,macros=506,bank_pair_rows=8192,macro_rows=4096,ROM_ECC=False)
    meta['image_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.glob('macro*.hex'))}
    (out/'manifest.json').write_text(json.dumps(meta,indent=2)+'\n');return meta
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--snapshot',type=Path,default=DEFAULT);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--tokens',nargs='+',type=int)
    a=ap.parse_args()
    if a.tokens and any(x<0 or x>=129280 for x in a.tokens):ap.error('token bounds')
    generate(a.snapshot,a.out,a.tokens)
