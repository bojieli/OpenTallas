"""Source-bound finite body emitter; existing lowerer events and all deltas retained.

Inputs must contain the actual source-lowered commands, never counts. The
ordinary stage0 contains the source token-start prefix and embedding commands.
INIT copies that segment and replaces exactly one AMAX emit by a positive-delta
non-go NOP. No runtime first-token inference. This emitter does not qualify the
provider phase, head constants or cap1 programme merely because it packs.
"""
import hashlib,json
from pathlib import Path
from calendar_rom_image import emit
ORDER=('embed','decode','head','boot','init')

def compile_body(segments, source):
    if set(segments)!=set(ORDER)-{'init'}:raise ValueError('four actual source segments required')
    for key in ('lowerer_sha256','programme_sha256','phase_manifest_sha256'):
        if len(source.get(key,''))!=64:raise ValueError('missing '+key)
        int(source[key],16)
    normal=segments['embed']
    def amemit(c):return (c>>1)&7==6 and (c>>5)&1 and c>>112!=14
    emits=[i for i,(_,c) in enumerate(normal) if amemit(c)]
    if len(emits)!=1 or not any(c>>112==14 and (c>>1)&7==1 for _,c in normal):
        raise ValueError('token-start prefix must contain one emit and LOCAL EMB')
    segments=dict(segments,init=[(t,0 if i==emits[0] else c) for i,(t,c) in enumerate(normal)])
    entries=[];ranges={}
    for seg in ORDER:
        while len(entries)%4:entries.append(1<<116)
        first=len(entries);last=0
        for t,c in segments[seg]:
            d=t-last
            if not 1<=d<=4095 or not 0<=c<1<<116:raise ValueError('invalid source command/delta')
            entries.append(d<<116|c);last=t
        ranges[seg]=dict(first=first,count=len(entries)-first)
    if not 0<len(entries)<=1023:raise ValueError('ten-bit calendar overflow')
    words=[0]*4096
    for i,e in enumerate(entries):words[i//4]|=e<<(128*(i%4))
    descriptor=[(0x43414c52<<32)|len(entries)]
    descriptor += [(ranges[k]['first']<<16)|ranges[k]['count'] for k in ORDER[:4]]
    # Canonical empty CTX4d43/mask0. Caller may opt into CTX_DW; no filler preload.
    descriptor += [0,0x4d43<<48,0]
    canonical=json.dumps(dict(segments=segments,source=source),sort_keys=True,separators=(',',':')).encode()
    rec=dict(schema='opentallas.qwen.playhead-calendar.v1',source=source,
             source_sha256=hashlib.sha256(canonical).hexdigest(),entries=len(entries),
             rows=(len(entries)+3)//4,entry_count_bits=10,physical_macros=2,descriptor=descriptor,
             ranges=ranges,fetch_capture_extra_edges=1,
             production_bound=False,qualification='source calendar playback only; actual cap1/phase/head payload bindings required')
    return rec,words

def main():
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();doc=json.loads(a.input.read_text())
    rec,words=compile_body(doc['segments'],doc['source']);emit(a.out,rec,words)
if __name__=='__main__':main()
