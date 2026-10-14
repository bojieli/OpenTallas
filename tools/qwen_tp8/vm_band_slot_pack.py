#!/usr/bin/env python3
"""Place the SAME whole pad-row tiles in the SAME six slots per bay.

Lane stage lists and tile bit assignments are immutable. Coordinate descent
assigns whole tiles to slots using every actual-pin hop's 500um excess. This
cannot certify missing boundary or new column pins; it repairs the known
intra-band physical hops without adding or removing stages.
"""
import collections
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.optimize import linear_sum_assignment
from vm_lef_pins import read
from vm_band_pair import reach

ROOT=Path(__file__).resolve().parents[2]


def main():
    path=ROOT/'results/arch/qwen_tp8_1012/vm_band_composition_codex.json'
    comp=json.loads(path.read_text());x0,y0=comp['origin_um']
    if any(s.get('bit_permutation',list(range(8)))!=list(range(8)) for seg in comp['segments'] for s in seg['path']):
        raise ValueError('local pin-bit order is installed; preserve it and use bit_order/fine_pack, or explicitly rebuild its model before coarse slot packing')
    if any(c.get('fine_offset',[0,0])!=[0,0] for c in comp['children']):
        raise ValueError('fine placement is installed; coarse slot model must be rebuilt before changing whole-slot assignments')
    plan=json.loads((ROOT/'results/arch/qwen_tp8_1012/vm_leaf_plan_claude.json').read_text())
    bays={b['n']:b for b in plan['x_relay_bays'] if b.get('padrow')}
    ch={(c['bay'],c['slot']):c for c in comp['children'] if 'bay' in c}
    pins={v:read(next((ROOT/v).glob('*.lef')))[1] for v in {c['view'] for c in ch.values()}}
    edges=[];adj=collections.defaultdict(list);limits=[]
    oldpins=read(ROOT/'physical/ref_tile/qfd_vm_xcol_t/views/ot_qfd_vm_xcol_t/ot_qfd_vm_xcol_t.lef')[1]
    columns={int(c['inst'][3:]):c for c in comp['children'] if c['inst'].startswith('u_c')}
    for segment in comp['segments']:
        p=segment['path']
        for a,b in zip(p,p[1:]):
            ka,kb=(a['bay'],a['slot']),(b['bay'],b['slot'])
            if ka==kb:continue
            pairs=[]
            for bit in range(8):
                pa=pins[ch[ka]['view']][f'q[{a["bit0"]+bit}]']
                pb=pins[ch[kb]['view']][f'd[{b["bit0"]+bit}]']
                pairs.append(((pa['x'],pa['y']),(pb['x'],pb['y'])))
            ix=len(edges);edges.append((ka,kb,pairs));adj[ka].append(ix);adj[kb].append(ix)
            limits.append([reach(ch[ka]['view'],a['bit0']+bit,ch[kb]['view'],b['bit0']+bit)-.2 for bit in range(8)])
        a=p[-1];ka=(a['bay'],a['slot']);col=int(segment['output'][0].split('_')[0][3:]);cc=columns[col]
        port='d_hi' if segment['output'][0].endswith('hi') else 'd_lo'
        pairs=[]
        for bit in range(8):
            pa=pins[ch[ka]['view']][f'q[{a["bit0"]+bit}]'];pb=oldpins[f'{port}[{segment["output"][1]+bit}]']
            pairs.append(((pa['x'],pa['y']),(x0+cc['at'][0]+pb['x'],y0+cc['at'][1]+pb['y'])))
        ix=len(edges);edges.append((ka,None,pairs));adj[ka].append(ix)
        limits.append([499.8]*8)
    slots={key:c['physical_slot'] for key,c in ch.items()}
    def pos(k,slot,p):return (bays[k[0]]['x']+slot*21.6+p[0],bays[k[0]]['y']+p[1]) if k else p
    def lengths(edge,override=None):
        a,b,pp=edge;sa=override.get(a,slots[a]) if override else slots[a];sb=(override.get(b,slots[b]) if override else slots[b]) if b else 0
        for pa,pb in pp:
            ax,ay=pos(a,sa,pa);bx,by=pos(b,sb,pb)
            yield abs(ax-bx)+abs(ay-by)
    def value(ei,override=None):return sum(1000*max(0,d-h)**2+d for d,h in zip(lengths(edges[ei],override),limits[ei]))
    def stats():
        ds=[d for e in edges for d in lengths(e)]
        return dict(edges=len(ds),over500=sum(d>500 for d in ds),pair_failed_bits=sum(d>h+.2 for ei in range(len(edges)) for d,h in zip(lengths(edges[ei]),limits[ei])),max_um=round(max(ds),4),cost=sum(value(ei) for ei in range(len(edges))))
    before=stats();rounds=[]
    bybay=collections.defaultdict(list)
    for k in ch:bybay[k[0]].append(k)
    for iteration in range(32):
        moves=0
        for bn,keys in sorted(bybay.items(),reverse=bool(iteration%2)):
            cost=np.zeros((len(keys),6))
            for i,k in enumerate(keys):
                for slot in range(6):
                    cost[i,slot]=sum(value(ix,{k:slot}) for ix in adj[k])
            rows,cols=linear_sum_assignment(cost)
            proposal={keys[int(i)]:int(s) for i,s in zip(rows,cols)}
            affected={ix for k in keys for ix in adj[k]}
            old=sum(value(ix) for ix in affected)
            new=sum(value(ix,proposal) for ix in affected)
            if new<old-1e-6:
                moves+=sum(slots[k]!=s for k,s in proposal.items());slots.update(proposal)
        current=stats();rounds.append(dict(iteration=iteration,moves=moves,**current))
        print(rounds[-1],flush=True)
        if not moves:break
    after=stats()
    out=dict(schema='opentallas.qwen.vm-band-slot-permutation.v1',source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        structural_change='same270wholetiles/same4096lanechains/same154832stagebits; physical permutation inside64existing6slotbays only',
        before=before,after=after,rounds=rounds,
        physical_slots={f'{k[0]}:{k[1]}':s for k,s in slots.items()},
        unresolved='boundary and new source column actual pins, pair-specific reach and gather/control')
    (ROOT/'results/arch/qwen_tp8_1012/vm_band_slot_assignment_codex.json').write_text(json.dumps(out,indent=1)+'\n')


if __name__=='__main__':main()
