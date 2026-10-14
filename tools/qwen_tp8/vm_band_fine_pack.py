#!/usr/bin/env python3
"""Use the existing 4.32um channels' 2.16um legal placement slack.

Shift existing tiles on the child lattice, with minimum 2.16um channels;
preserve all whole tile slots and the region/band outer abutments.
"""
import collections,gzip,hashlib,itertools,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]


def main():
    comp=json.loads((ROOT/'results/arch/qwen_tp8_1012/vm_band_composition_codex.json').read_text())
    report=json.loads((ROOT/'results/arch/qwen_tp8_1012/vm_band_paths_codex.json').read_text())
    assert report['source_sha256']==hashlib.sha256((ROOT/report['source']).read_bytes()).hexdigest(),'re-run all-bit paths after composition changed'
    detail=json.load(gzip.open(ROOT/report['all_bit_details']['path'],'rt'));edges=detail['edges']
    children={f'{c["bay"]}:{c["slot"]}':c for c in comp['children'] if 'bay' in c}
    def key(s):return f'{s["bay"]}:{s["slot"]}'
    adjacent=collections.defaultdict(set);keys=[]
    for i,e in enumerate(edges):
        a=key(e['launch']) if 'launch' in e else None
        # Provisional final-column edges currently lack stage identity. They
        # are checked after regeneration; only measured internal edges optimize.
        b=key(e['capture']) if 'capture' in e else None
        keys.append((a,b))
        if a:adjacent[a].add(i)
        if b:adjacent[b].add(i)
    initial={k:tuple(c['fine_offset']) for k,c in children.items()};offsets=dict(initial)
    def length(i,override=None):
        e=edges[i];a,b=keys[i];override=override or {};ax,ay=e['A'];bx,by=e['B']
        if a:
            dx,dy=override.get(a,offsets[a]);ox,oy=initial[a];ax+=dx-ox;ay+=dy-oy
        if b:
            dx,dy=override.get(b,offsets[b]);ox,oy=initial[b];bx+=dx-ox;by+=dy-oy
        return abs(ax-bx)+abs(ay-by)
    def cost(i,override=None):
        d=length(i,override);reach=edges[i].get('pair_reach_um',500)-.2
        return 10000*max(0,d-reach)**2+d
    def stats():
        return dict(pair_failed_bits=sum(length(i)>e.get('pair_reach_um',500)+1e-4 for i,e in enumerate(edges)),
                    max_um=round(max(length(i) for i in range(len(edges))),4))
    before=stats();hist=[]
    for iteration in range(16):
        moves=0
        for k,c in children.items():
            direction=1 if '_S' in c['bay'] else -1
            old=sum(cost(i) for i in adjacent[k]);best=(old,offsets[k])
            for dx,dy in itertools.product((0,2.16),(0,direction*2.16)):
                proposal=(dx,dy);score=sum(cost(i,{k:proposal}) for i in adjacent[k])
                if score<best[0]-1e-6:best=(score,proposal)
            if best[1]!=offsets[k]:offsets[k]=best[1];moves+=1
        state=dict(iteration=iteration,moves=moves,**stats());hist.append(state);print(state,flush=True)
        if not moves:break
    # Every positive x offset consumes half the 4.32um inter-slot channel;
    # every y offset consumes half the 4.32um pad-to-column channel.
    rec=dict(schema='opentallas.qwen.vm-band-fine-placement.v1',before=before,after=stats(),rounds=hist,
        minimum_channel_um=2.16,child_lattice_um=2.16,
        structural_change='existing tile placements shifted by at most2.16um inside existing pad-row channel slack; no stage/tile/outerboundary changes',
        physical_offsets=offsets,unresolved='must re-gate actual wholegeometry and new column/boundary pins')
    (ROOT/'results/arch/qwen_tp8_1012/vm_band_fine_assignment_codex.json').write_text(json.dumps(rec,indent=1)+'\n')


if __name__=='__main__':main()
