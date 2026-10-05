"""Translate saved source bytes into the existing HBM partition image format.

No checkpoint load, inference, program recompile or reference payload input.
The admitted source is the existing reduced DSpark image schema (CTX32);
full-shape native source producers need their own declared geometry successor.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
from tools.gpu_sys.ds_hbm_simulator20 import sha


def prepare(manifest,out):
    manifest=Path(manifest).resolve();out=Path(out).resolve()
    source=json.loads(manifest.read_text())
    if source.get('schema')!='opentallas.ds_hbm_dspark_connected_images.v1' or source['tp']!=2 or source['nsm']!=2 or source['imw']!=14:
        raise ValueError('existing native image schema/topology required')
    if not 0<source['mem_bytes']<=2*2097152*32 or source['mem_bytes']%256:
        raise ValueError('source image sector footprint must fit without modulo alias')
    for name,digest in source['artifacts'].items():
        if Path(name).name!=name or sha(manifest.parent/name)!=digest:
            raise ValueError('original source bytes/hash mismatch: '+name)
    out.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(manifest,out/'origin.json')
    for name in source['artifacts']:
        # Copy paths are inputs owned by this source bundle, never a live
        # mutable state buffer and never expected arithmetic output.
        os.symlink(manifest.parent/name,out/name)
    for die in range(2):
        with (manifest.parent/f'die{die}.bin').open('rb') as data:
            files=[(out/f'mem_d{die}_p{part}.hex').open('w') for part in range(2)]
            try:
                read=0
                while True:
                    block=data.read(256)
                    if not block:break
                    if len(block)!=256:raise ValueError('incomplete original interleave block')
                    read+=len(block)
                    for part in range(2):
                        segment=block[part*128:(part+1)*128]
                        files[part].write(''.join(segment[i:i+32][::-1].hex()+'\n' for i in range(0,128,32)))
                if read!=source['mem_bytes']:
                    raise ValueError('original image length does not match compiler extent')
                pad=(2097152-read//64)
                zeros=('0'*64+'\n')*4096
                for f in files:
                    for _ in range(pad//4096):f.write(zeros)
                    f.write(('0'*64+'\n')*(pad%4096))
            finally:
                for f in files:f.close()
    artifacts={p.name:sha(p) for p in out.iterdir() if p.name!='origin.json'}
    result=dict(schema='opentallas.ds_hbm.simulator20_source.v1',
        topology=dict(dies=2,sms_per_die=2,partitions_per_die=2,sector_words=2097152),
        origin_manifest='origin.json',origin_sha256=sha(out/'origin.json'),
        entries=source['entries'],position_extent=32,full_shape=False,
        prompt=source['prompt'],noise=source['noise'],layout=source['layout'],
        artifacts=artifacts,source_images_numerical_qualified=False,
        transformation='128B partition interleave, 32B little endian sectors; no arithmetic')
    (out/'source.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args();prepare(a.source,a.out)


if __name__=='__main__':main()
