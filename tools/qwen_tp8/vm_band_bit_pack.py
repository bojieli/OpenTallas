#!/usr/bin/env python3
"""Repair actual-pin reach by swapping 8-bit lane chunks inside existing tiles.

No tile, lane, or pipeline stage changes. All eight pins in every affected
lane hop are evaluated. Provisional column inputs are included as constraints,
and must later be rechecked against the new closed source view.
"""
import collections,json
from pathlib import Path
from vm_lef_pins import read
from vm_bay_cluster import WID
from vm_band_pair import reach
ROOT=Path(__file__).resolve().parents[2]


def main():
    comp=json.loads((ROOT/'results/arch/qwen_tp8_1012/vm_band_composition_codex.json').read_text())
    if any(s.get('bit_permutation',list(range(8)))!=list(range(8)) for seg in comp['segments'] for s in seg['path']):
        raise ValueError('local pin-bit order is installed; preserve it with vm_band_bit_order.py before reassigning coarse chunks')
    x0,y0=comp['origin_um'];children={(c['bay'],c['slot']):c for c in comp['children'] if 'bay' in c}
    cols={int(c['inst'][3:]):c for c in comp['children'] if c['inst'].startswith('u_c')}
    pins={v:read(next((ROOT/v).glob('*.lef')))[1] for v in {c['view'] for c in children.values()}}
    oldpins=read(ROOT/'physical/ref_tile/qfd_vm_xcol_t/views/ot_qfd_vm_xcol_t/ot_qfd_vm_xcol_t.lef')[1]
    nodes=[];edges=[];adj=collections.defaultdict(set);tile_nodes=collections.defaultdict(dict)
    for seg in comp['segments']:
        prev=None
        for st in seg['path']:
            ix=len(nodes);key=st['bay'],st['slot'];nodes.append(st);tile_nodes[key][st['bit0']]=ix
            if prev is not None:
                ei=len(edges);edges.append((prev,ix,None));adj[prev].add(ei);adj[ix].add(ei)
            prev=ix
        col=int(seg['output'][0].split('_')[0][3:]);c=cols[col];port='d_hi' if seg['output'][0].endswith('hi') else 'd_lo'
        fixed=[]
        for bit in range(8):
            p=oldpins[f'{port}[{seg["output"][1]+bit}]'];fixed.append((x0+c['at'][0]+p['x'],y0+c['at'][1]+p['y']))
        ei=len(edges);edges.append((prev,None,fixed));adj[prev].add(ei)
    bits=[n['bit0'] for n in nodes]
    def point(i,port,bit,overrides):
        n=nodes[i];c=children[n['bay'],n['slot']];p=pins[c['view']][f'{port}[{overrides.get(i,bits[i])+bit}]']
        return x0+c['at'][0]+p['x'],y0+c['at'][1]+p['y']
    def lengths(ei,overrides=None):
        overrides=overrides or {};a,b,f=edges[ei]
        for bit in range(8):
            ax,ay=point(a,'q',bit,overrides);bx,by=point(b,'d',bit,overrides) if b is not None else f[bit]
            yield abs(ax-bx)+abs(ay-by)
    def limits(ei,ov=None):
        ov=ov or {};a,b,f=edges[ei]
        if b is None:return [499.8]*8
        la,ca=nodes[a],nodes[b];lc=children[la['bay'],la['slot']];cc=children[ca['bay'],ca['slot']]
        return [reach(lc['view'],ov.get(a,bits[a])+bit,cc['view'],ov.get(b,bits[b])+bit)-.2 for bit in range(8)]
    def cost(ei,ov=None):return sum(10000*max(0,d-h)**2+d for d,h in zip(lengths(ei,ov),limits(ei,ov)))
    def stats():
        ds=[d for ei in range(len(edges)) for d in lengths(ei)]
        pair=sum(d>h+.2 for ei in range(len(edges)) for d,h in zip(lengths(ei),limits(ei)))
        return dict(over500=sum(d>500 for d in ds),pair_failed_bits=pair,max_um=round(max(ds),4),edges=len(ds))
    before=stats();history=[]
    for iteration in range(16):
        bad=[ei for ei in range(len(edges)) if any(d>h for d,h in zip(lengths(ei),limits(ei)))];moves=0
        for ei in bad:
            if all(d<=h for d,h in zip(lengths(ei),limits(ei))):continue
            best=None
            for i in edges[ei][:2]:
                if i is None:continue
                st=nodes[i];key=st['bay'],st['slot'];occupants=tile_nodes[key]
                for bit0 in range(0,WID[st['kind']],8):
                    j=occupants.get(bit0)
                    if j==i:continue
                    ov={i:bit0}
                    if j is not None:ov[j]=bits[i]
                    affected=adj[i] | (adj[j] if j is not None else set())
                    gain=sum(cost(e) - cost(e,ov) for e in affected)
                    if gain>1e-6 and (best is None or gain>best[0]):best=(gain,i,j,bit0)
            if best:
                gain,i,j,bit0=best;st=nodes[i];key=st['bay'],st['slot'];occ=tile_nodes[key];old=bits[i]
                del occ[old]
                if j is not None:bits[j]=old;occ[old]=j
                bits[i]=bit0;occ[bit0]=i;moves+=1
        # A full tile can trap a two-way swap: allow a three-way rotation when
        # two endpoints need the same fast pin chunk. All affected hops count.
        if not moves:
            best3=None
            for ei in bad:
                if all(d<=h for d,h in zip(lengths(ei),limits(ei))):continue
                for i in edges[ei][:2]:
                    if i is None:continue
                    st=nodes[i];key=st['bay'],st['slot'];occ=tile_nodes[key]
                    for b1,j in list(occ.items()):
                        if j==i:continue
                        for b2 in range(0,WID[st['kind']],8):
                            k=occ.get(b2)
                            if k in (i,j):continue
                            ov={i:b1,j:b2}
                            if k is not None:ov[k]=bits[i]
                            affected=adj[i]|adj[j]|(adj[k] if k is not None else set())
                            gain=sum(cost(e)-cost(e,ov) for e in affected)
                            if gain>1e-6 and (best3 is None or gain>best3[0]):best3=(gain,i,j,k,b1,b2)
            if best3:
                gain,i,j,k,b1,b2=best3;st=nodes[i];occ=tile_nodes[st['bay'],st['slot']];old=bits[i]
                for b in (old,b1,b2):occ.pop(b,None)
                bits[i]=b1;bits[j]=b2;occ[b1]=i;occ[b2]=j
                if k is not None:bits[k]=old;occ[old]=k
                moves=1
        state=dict(iteration=iteration,moves=moves,**stats());history.append(state);print(state,flush=True)
        if not moves:break
    rec=dict(schema='opentallas.qwen.vm-band-bit-permutation.v1',before=before,after=stats(),rounds=history,
        structural_change='8bitlanechunkpermutation within same270closedtiles; all4096lanes/stages/bitorder preserved',
        physical_bits={n['placement_id']:bits[i] for i,n in enumerate(nodes)},
        unresolved='provisional column input pins and unassigned boundary/gather/control timing')
    (ROOT/'results/arch/qwen_tp8_1012/vm_band_bit_assignment_codex.json').write_text(json.dumps(rec,indent=1)+'\n')


if __name__=='__main__':main()
