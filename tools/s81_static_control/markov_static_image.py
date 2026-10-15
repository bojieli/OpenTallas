"""Copy actual released Markov embedding bytes into all506 physical ROM masks."""
from pathlib import Path
import hashlib,json,argparse
TOKENS=129280;K=256;BYTES=TOKENS*K*2


def generate(payload,source_manifest,out):
    raw=Path(payload).read_bytes();meta=json.loads(Path(source_manifest).read_text())
    sha=hashlib.sha256(raw).hexdigest()
    if len(raw)!=BYTES or meta['payload_sha256']!=sha or meta['tensor']!='mtp.2.markov_head.embed.weight' or meta['checkpoint_revision']!='dba1be0a40aa45a94ad051997016db3960a90277':
        raise ValueError('actual released full129280x256 BF16 table/source identity required')
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    spread=[sum(((b>>k)&1)<<(8*k) for k in range(8))for b in range(256)]
    images={}
    for macro in range(506):
        physical=[0]*512;bank,par=divmod(macro,2)
        for local in range(4096):
            global_word=bank*8192+local*2+par
            off=global_word*32;word=raw[off:off+32]
            # Only unused cells beyond the true table's final row are zero.
            expanded=sum(spread[b]<<(64*j)for j,b in enumerate(word))
            physical[local//8]|=expanded<<(local%8)
        image=out/f'macro{macro:03}.viamap.hex'
        image.write_text(''.join(f'{row:0548x}\n'for row in physical))
        images[image.name]=hashlib.sha256(image.read_bytes()).hexdigest()
    result=dict(source=meta,payload_sha256=sha,tokens=TOKENS,dim=K,dtype='BF16',macros=506,pairs=253,
                all_released_rows_present=True,ROM_ECC=False,images=images,physical_qualified=False)
    (out/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--payload',type=Path,required=True);ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    generate(a.payload,a.source,a.out)
