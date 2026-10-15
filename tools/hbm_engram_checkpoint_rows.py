#!/usr/bin/env python3
"""Bounded actual released Engram rows for EXTERNAL HBM stimuli and comparison.

No result is fed to on-chip arithmetic except the original external table bytes.
"""
from __future__ import annotations
import argparse, hashlib, json, os, subprocess
from pathlib import Path
import numpy as np
import hdc_v41_engram_shipped as S
import hbm_engram_partition as E
ROOT=Path(__file__).resolve().parents[1]
CATALOGUE='25631b8754f4ec295d5d6415ca85e75f38564664'
CONTRACT='a9d1fad2835d96e4c0585a150b6a9d484b9791cc'

def blob(commit,path):return subprocess.check_output(['git','show',f'{commit}:{path}'],cwd=ROOT)
def sha(raw):return hashlib.sha256(raw).hexdigest()

def prepare(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    catraw=blob(CATALOGUE,'results/quality/w16_w17_checkpoint_header_catalogue_20261001/catalogue.json')
    conraw=blob(CONTRACT,'results/quality/w16_dsrom_engram_contract_20261001/contract.json')
    cat=json.loads(catraw);con=json.loads(conraw);snapshot=Path(cat['snapshot'])
    # Valid compressed-token sequence. The actual hash is driven with all four
    # tokens, preserving its real history; only the final token is gathered.
    history=[17,999,5543,99091]
    t=S.shipped_tables();ids=S.hashes(t,history);rows=[];sectors=[];gold=[]
    for li,L in enumerate(E.LAYERS):
        codes=[];scales=[]
        for col,row in enumerate(ids[li]):
            parts=[];regions=[]
            for suffix,width in [('weight',256),('scale',8)]:
                rec=con['tensors'][f'layers.{L}.engram.embed.{suffix}'];hb=cat['shards'][rec['shard']]
                path=snapshot/rec['shard'];before=path.stat();fd=os.open(path,os.O_RDONLY)
                try:
                    header=os.pread(fd,hb['header_bytes'],8)
                    if sha(header)!=hb['raw_header_sha256']:raise ValueError('released checkpoint header changed')
                    offset=rec['absolute_file_offsets'][0]+row*width
                    raw=os.pread(fd,width,offset)
                    if len(raw)!=width:raise ValueError('short actual checkpoint row')
                finally:os.close(fd)
                after=path.stat()
                if (before.st_ino,before.st_size,before.st_mtime_ns)!=(after.st_ino,after.st_size,after.st_mtime_ns):raise ValueError('checkpoint changed during bounded read')
                parts.append(raw);regions.append(dict(path=str(path),offset=offset,bytes=width,sha256=sha(raw),header_sha256=sha(header)))
            code,scale=parts;packet=code+scale+bytes(24)
            h,rank,local=E.locate(row,E.RELEASED_ROWS[li],li)
            rows.append(dict(layer=L,list_index=col,global_row=row,home=h,rank=rank,local_row=local,
                address=E.TABLE_BASE+local*288,bytes=288,sha256=sha(packet),source_regions=regions))
            codes.append(list(code));scales.append(list(scale))
            sectors.extend(int.from_bytes(packet[b:b+32],'little') for b in range(0,288,32))
        expected=S.decode_rows8(codes,scales)
        gold.extend(int.from_bytes(np.asarray(expected[col,32*b:32*(b+1)],dtype='<u2').tobytes(),'little') for col in range(24) for b in range(8))
    (out/'external_hbm_sectors.hex').write_text(''.join(f'{v:064x}\n' for v in sectors))
    (out/'expected_bf16.hex').write_text(''.join(f'{v:0128x}\n' for v in gold))
    receipt=dict(schema='opentallas.hbm.engram.external_checkpoint_rows.v1',checkpoint_revision=cat['checkpoint_revision'],
        catalogue_commit=CATALOGUE,catalogue_sha256=sha(catraw),contract_commit=CONTRACT,contract_sha256=sha(conraw),
        compressed_history=history,rows=rows,actual_source_bytes=48*264,external_hbm_bytes=48*288,
        golden_boundary='comparison only; actual codes/scales enter DUT solely at modeled external HBM pins',
        data_sha256={p.name:sha(p.read_bytes()) for p in out.glob('*.hex')},
        generator_sha256=sha(Path(__file__).read_bytes()),full_layer_qualified=False)
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');return receipt

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);args=ap.parse_args();r=prepare(args.out)
    print(json.dumps({k:v for k,v in r.items() if k!='rows'},indent=2))
