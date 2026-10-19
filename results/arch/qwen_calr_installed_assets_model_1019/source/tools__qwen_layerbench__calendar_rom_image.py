"""Opt-in immutable calendar ABI; separate from the legacy 976-PW image.

The input is the actual lowered ordered segment entries, never a count-only
placeholder. Four 128-bit entries share one 512-bit read; two actual266b macros
hold that row. The 10-bit entry count supports the production774-command body.
No table payload is stored in this calendar.
"""
import hashlib
import json
from pathlib import Path
from programme_store import physical_rows

SEGMENTS=('boot','init','decode','head')

def compile_image(segments, source_sha256):
    if len(source_sha256)!=64:
        raise ValueError('source digest required')
    int(source_sha256,16)
    if set(segments)!=set(SEGMENTS):
        raise ValueError('all four explicit segments required')
    entries=[]; ranges={}
    for seg in SEGMENTS:
        while len(entries)%4: entries.append(1<<116)
        first=len(entries)
        for delta,command in segments[seg]:
            if not 1<=delta<4096 or not 0<=command<1<<116:
                raise ValueError('invalid delta/command')
            entries.append((delta<<116)|command)
        ranges[seg]=dict(first=first,count=len(entries)-first)
    if not 0<len(entries)<=1023:
        raise ValueError('calendar exceeds ten-bit entry ABI')
    words=[0]*4096
    for i,w in enumerate(entries): words[i//4]|=w<<(128*(i%4))
    # Independent ABI tag CALR, count[9:0], all remaining low32 bits reserved.
    descriptor=[(0x43414c52<<32)|len(entries)]
    for seg in SEGMENTS:
        r=ranges[seg]; descriptor.append((r['first']<<16)|r['count'])
    return dict(schema='opentallas.qwen.immutable-calendar.v1',source_sha256=source_sha256,
                entries=len(entries),rows=(len(entries)+3)//4,entry_count_bits=10,
                physical_macros=2,descriptor=descriptor,ranges=ranges),words

def emit(out,receipt,words):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    for lane in range(2):
        rows=physical_rows(words,lane)
        (out/f'calendar_m{lane}.viamap.hex').write_text(''.join(f'{r:0532x}\n' for r in rows))
    (out/'expected.hex').write_text(''.join(f'{w:0128x}\n' for w in words))
    (out/'descriptor.json').write_text(json.dumps(receipt,indent=2)+'\n')

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();raw=a.input.read_bytes();doc=json.loads(raw)
    rec,words=compile_image(doc['segments'],hashlib.sha256(raw).hexdigest());emit(a.out,rec,words)
