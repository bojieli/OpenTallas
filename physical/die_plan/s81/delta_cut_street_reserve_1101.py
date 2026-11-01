#!/usr/bin/env python3
"""Allocate actual gcell-wide M4..M7 streets for the S81-007 cut class.

Bands are plan geometry, consumed by die_trial.band_share_obs and by the
partition's exact-complement partition_ft_reserve hook.  No scalar budget or
cut limit is changed.  The candidate remains a trial until physical probes
show both the die and partition can route their disjoint shares.
"""
import collections
import copy
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tools/die_plan'))
import check
import die_trial as D
import schema as S

TARGETS = ('s_2N_L1', 'svc_1', 's_3S_L2', 's_0S_L0', 's_5S_L0',
           's_5S_L1', 's_6S_L1', 's_1N_L0', 's_1N_L1', 's_0N_L3')


def candidates(P, baseline, target=.58):
    # Every selected type is singleton, so the exact global gcell-map has one
    # unambiguous transform into the one hardened type.
    count = collections.Counter(p['type'] for p in P.parts.values())
    core = {L: D.die_core_rects(P, L) for L in ('M4', 'M5', 'M6', 'M7')}
    constraints = []; cells = {}
    for orient in ('vertical', 'horizontal'):
        horizontal = orient == 'vertical'
        direction = 'H' if horizontal else 'V'
        for row in baseline[orient]:
            pn = row.get('worst_part')
            if row['worst_part_ratio'] <= target: continue
            part=P.parts[pn]; tn=part['type']; assert count[tn]==1
            c=row['at_um']; r=P.rect(pn)
            lo,hi = (r[1],r[3]) if horizontal else (r[0],r[2])
            cap=row['worst_part_bits']/row['worst_part_ratio']
            need=row['worst_part_bits']/target-cap
            idx=len(constraints)
            constraints.append(dict(part=pn,type=tn,orient=orient,at_um=c,bits=row['worst_part_bits'],
                                    baseline_tracks=cap,needed_tracks=need,added_tracks=0.0,hit_positions=row.get('hits_um',[])))
            for L in check.PART_FT_LAYERS[direction]:
                blocks=[(a[1],a[3]) if horizontal else (a[0],a[2]) for a in core[L]
                        if (a[0]<c<a[2] if horizontal else a[1]<c<a[3])]
                for k in range(math.ceil(lo/D.GCELL_UM), math.floor(hi/D.GCELL_UM)):
                    a=k*D.GCELL_UM; b=(k+1)*D.GCELL_UM
                    # A whole gcell fits in the actual open street at this cut.
                    if any(a<e+0.2 and b>s-0.2 for s,e in blocks): continue
                    w,h=P.types[tn]['outline_um'];ox,oy=part['origin_um']
                    x,y=(a-oy,b-oy) if horizontal else (a-ox,b-ox)
                    if (horizontal and part.get('orient') in ('MX','R180')): x,y=h-y,h-x
                    if (not horizontal and part.get('orient') in ('MY','R180')): x,y=w-y,w-x
                    key=(tn,'EW' if horizontal else 'NS',L,round(x,4),round(y,4))
                    gain=(1-check.FT_TRACK_FRAC)*(b-a)/P.layers[L]['pitch_um']
                    cells.setdefault(key,{})[idx]=gain
    selected=[]
    while True:
        deficits={i:max(0,c['needed_tracks']-c['added_tracks']) for i,c in enumerate(constraints)}
        if max(deficits.values(),default=0)<1e-6:break
        scored=[]
        for key,gains in cells.items():
            score=sum(min(deficits[i],g)/max(1.0,constraints[i]['needed_tracks']) for i,g in gains.items())
            if score>0:
                tn,d,L,a,b=key;near=0.0
                for i in gains:
                    if not deficits[i]:continue
                    c=constraints[i];part=P.parts[c['part']];w,h=P.types[tn]['outline_um']
                    xy=P.to_die(c['part'],(0,(a+b)/2) if d=='EW' else ((a+b)/2,0))
                    mid=xy[1] if d=='EW' else xy[0]
                    near+=sum(width/(40+abs(mid-pos)) for pos,width in c['hit_positions'])/c['bits']
                scored.append((score,near,key,gains))
        if not scored: raise RuntimeError('no physical street gcell can satisfy cut demand')
        # Ties alternate layers/spans through the sorted keys; all allocations
        # are explicit rectangles, with macro OBS retaining precedence.
        _,_,key,gains=max(scored)
        selected.append(key); del cells[key]
        for i,g in gains.items():constraints[i]['added_tracks']+=g
    bands=collections.defaultdict(list)
    for tn,d,L,a,b in sorted(selected):
        if bands[tn] and bands[tn][-1]['dir']==d and bands[tn][-1]['layers']==[L] and abs(bands[tn][-1]['span_um'][1]-a)<1e-5:
            bands[tn][-1]['span_um'][1]=b
        else:bands[tn].append(dict(dir=d,span_um=[a,b],layers=[L],die_share=1.0))
    for c in constraints:
        c['candidate_tracks']=c['baseline_tracks']+c['added_tracks']
        c['candidate_ratio']=c['bits']/c['candidate_tracks']
    return dict(bands),constraints


def all_segments(P, geo):
    """Check every occupied partition segment; the public summary emits only its worst."""
    core={L:D.die_core_rects(P,L) for L in ('M4','M5','M6','M7')}
    segments=[]
    for lid,(points,_,_) in geo.items():
        width=P.ports[P.lanes[lid]['ports'][0]]['width']
        segments.extend((a,b,width) for a,b in zip(points,points[1:]))
    out=dict(vertical=[],horizontal=[])
    for orient,extent in [('vertical',P.W),('horizontal',P.H)]:
        horizontal=orient=='vertical';layers=check.PART_FT_LAYERS['H' if horizontal else 'V']
        for c in range(P.budgets['cut_step_um'],int(extent),P.budgets['cut_step_um']):
            hits=[]
            for a,b,width in segments:
                s,e=(a[0],b[0]) if horizontal else (a[1],b[1])
                if min(s,e)<c-check.EPS and max(s,e)>c+check.EPS:
                    hits.append((a[1] if horizontal else a[0],width))
            for pn in P.parts:
                r=P.rect(pn);lo,hi,s,e=(r[1],r[3],r[0],r[2]) if horizontal else (r[0],r[2],r[1],r[3])
                if not s+check.EPS<c<e-check.EPS:continue
                bits=sum(w for y,w in hits if lo-check.EPS<=y<=hi+check.EPS)
                if not bits:continue
                tracks=0
                for L in layers:
                    obs=[(x[1],x[3]) if horizontal else (x[0],x[2]) for x in core[L]
                         if (x[0]+check.EPS<c<x[2]-check.EPS if horizontal else x[1]+check.EPS<c<x[3]-check.EPS)]
                    tracks+=check.cut_interval_tracks(lo,hi,P.layers[L]['pitch_um'],check.FT_TRACK_FRAC,obs,[])
                ratio=bits/tracks if tracks else math.inf
                if ratio>.58:
                    out[orient].append(dict(at_um=c,worst_part=pn,worst_part_bits=bits,worst_part_ratio=ratio,hits_um=[(y,w) for y,w in hits if lo-check.EPS<=y<=hi+check.EPS]))
    return out


def main():
    path=Path(sys.argv[1]); text=path.read_text(); raw=json.loads(text);before=copy.deepcopy(raw)
    P=S.Plan(raw,path=path)
    geo={lid:check.lane_geometry(P,lid) for lid in P.lanes}
    R=check.Report(); baseline=check.check_cuts(P,R,geo)
    allcuts=all_segments(P,geo)
    bands,cons=candidates(P,allcuts)
    for tn,bs in bands.items():
        assert not raw['partition_types'][tn].get('die_ft_bands')
        raw['partition_types'][tn]['die_ft_bands']=bs
        marker='  '+json.dumps(tn)+': {\n'; assert text.count(marker)==1
        text=text.replace(marker,marker+'   "die_ft_bands": '+json.dumps(bs,separators=(',',':'))+',\n')
    assert json.loads(text)==raw
    r=check.Report(); after=check.check_cuts(P,r,geo)
    assert not r.errors(),r.errors()
    assert all(before[k]==raw[k] for k in raw if k!='partition_types')
    path.write_text(text)
    out=Path(sys.argv[2]);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(dict(schema='opentallas.s81.cut_street_trial.v1',verdict='CANDIDATE',
                     cut_errors_before=R.errors(),cut_errors_after=r.errors(),
                     constraints=cons,bands=bands,worst_before=baseline['worst_partition_segment'],
                     worst_after=after['worst_partition_segment'],new_cycles=0,
                     next_gate='exact physical reservation-map review + partition/die routing probes'),indent=1)+'\n')
    print('types',len(bands),'bands',sum(map(len,bands.values())),'cut errors',len(R.errors()),'->',len(r.errors()))
    print('worst',baseline['worst_partition_segment'],'->',after['worst_partition_segment'])


if __name__=='__main__':main()
