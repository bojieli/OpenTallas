#!/usr/bin/env python3
"""Actual checkpoint embedding rows and independent decoded FP32 observers."""
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import hdc_golden as G
from hdc_qwen_int8_image_w12 import shipped_vocab_rows
from hdc_qwen_layer0_rom_w12 import pinned_snapshot

def emit(snapshot, out):
    pinned_snapshot(snapshot)
    out.mkdir(parents=True, exist_ok=True)
    report = {'scope':'ACTUAL_CHECKPOINT_INPUTS_AND_OBSERVER_ONLY', 'rows':{}}
    for token in (0, 65536, 151935):
        source = shipped_vocab_rows(snapshot, 'embedding', start=token, count=1)
        codes = source['codes'].numpy()[0].astype(np.int8)
        scale = source['scales'].float().numpy()[0,0]
        bf16 = int(source['scales'].view(__import__('torch').int16).numpy().view(np.uint16)[0,0])
        decoded = G.mul(codes.astype(np.float32), np.float32(scale))
        directory = out / f'token{token}'
        directory.mkdir(exist_ok=True)
        (directory/'codes.hex').write_text(''.join(row[::-1].tobytes().hex()+'\n' for row in codes.reshape(-1,64)))
        (directory/'scale.hex').write_text(f'{bf16:04x}\n')
        (directory/'expected_X.hex').write_text(''.join(f'{int(b):08x}\n' for b in G.bits(decoded)))
        (directory/'expected_SSX.hex').write_text(f'{int(G.bits(G.lane_sum(G.mul(decoded,decoded)))):08x}\n')
        report['rows'][str(token)] = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.iterdir()}
    report['source_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (out/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--snapshot',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();emit(a.snapshot,a.out)
