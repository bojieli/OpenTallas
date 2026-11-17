#!/usr/bin/env python3
"""Reproduce the explicit component calendar masks; not a global programme."""
import json
from pathlib import Path
root=Path(__file__).resolve().parent
entries=json.loads((root/'preparation.json').read_text())['calendar_entries']
words=[0]*4096
for i,e in enumerate(entries):
    words[i//4]|=((int(e['delta'])<<116)|int(e['cmd'],16))<<(128*(i%4))
(root/'rom').mkdir(exist_ok=True)
for lane in (0,1):
    rows=[0]*512
    for address,word in enumerate(words):
        part=(word>>(266*lane))&((1<<266)-1)
        for io in range(266):
            rows[address//8]|=((part>>io)&1)<<(8*io+address%8)
    data=''.join(f'{v:0532x}\n' for v in rows)
    target=root/'rom'/f'calendar_m{lane}.viamap.hex'
    if target.exists() and target.read_text()!=data:
        raise ValueError('existing component calendar mask differs; refused')
    target.write_text(data)
