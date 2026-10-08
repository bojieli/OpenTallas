#!/usr/bin/env python3
"""Canonical 40-layer source control-profile census and minimal missing observer classes.
No numerical/timing qualification transfers from shape equality. No RTL or image generation.
"""
import argparse,collections,copy,gzip,hashlib,json
from pathlib import Path
import dsrom_1m_field as F
import dsrom_recovery_field as P


def digest(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def region_profile(ph, reg, rb, bfs):
    pairs=list(range(rb[reg],rb[reg+1])); bfp=[p for p in pairs if p in bfs]
    qp=[p for p in pairs if p not in bfs]
    qslots=[i for i in range(P.NP) if i not in F.BF_SLOTS]
    if len(bfp)>P.NBF or len(qp)>len(qslots):raise ValueError('actual region exceeds retained archive')
    slots={p:F.BF_SLOTS[i] for i,p in enumerate(bfp)}|{p:qslots[i] for i,p in enumerate(qp)}
    mats=[];rowbase=0
    for m in ph['mats']:
        pl=m['regions'].get(str(reg),[])
        if not pl:continue
        sr=sorted({s for s,seg,pair in pl});loc={s:i for i,s in enumerate(sr)}
        rows=[r for s in sr for r in (2*s,2*s+1) if r<m['entry_rows']]
        mats.append(dict(fmt=m['fmt'],K=m['K'],rows=len(rows),outbase=rowbase,segments=m['segments'],
                         placement=sorted([loc[s],seg,slots[pair]] for s,seg,pair in pl)))
        rowbase+=len(rows)
    if ph['K']>6144 or rowbase>P.OSTRIDE:raise ValueError('retained input/output capacity exceeded')
    return dict(K=ph['K'],out=ph['out'],fmts=ph['fmts'],mats=mats,rows=rowbase,
                actual_pairs=len(pairs),bf_pairs=len(bfp))


def profiles(phases,rb,bfs):
    groups={}
    for key,phs in P.node_groups(dict(phases=phases)).items():
        regs=sorted({r for ph in phs for r in ph['regions']})
        if len(phs)>8:raise ValueError('PHW3 op capacity exceeded')
        groups[P.gname(key)]=dict(key=key,phases=[ph['phase'] for ph in phs],regions=regs,
            # Keep region identities: actual return/bank placement is not a freely permutable array.
            control_profile=[(r,[region_profile(ph,r,rb,bfs) for ph in phs if r in ph['regions']]) for r in regs])
    return groups


def canonical_phases(ents,rb,bfs):
    phases=[]
    for L in range(40):
        for group,(node,xsrc,mats) in F.layer_groups(L,ents[L],rb,bfs).items():
            # Exact inherited R93+520 placement delta, separate from overlap scheduling credit.
            mats=copy.deepcopy(mats)
            for m in mats:
                if m['alias'].startswith('wo_a.group') and m['alias'].endswith('rows768'):
                    m['regions']['93']=[[sr,seg,P.NEW_BF] for sr,seg,_ in m['regions'].get('93',[])]
            split=[]
            for m in mats:
                if split and not any(F.illegal(split[-1]+[m],r) for r in range(128)):split[-1].append(m)
                else:split.append([m])
            for ms in split:
                bad=[r for r in range(128) if F.illegal(ms,r)]
                if bad:raise ValueError((L,group,'illegal actual placement',bad))
                stages={m['stage'] for m in ms}
                if len(stages)!=1:raise ValueError('phase spans owners')
                name=f'L{L}.{group}'+('' if len(split)==1 else '.'+'+'.join(m['alias'] for m in ms))
                K=ms[0]['K'];bf=ms[0]['fmt']=='bf16'
                phases.append(dict(layer=L,node=node,phase=name,stage=stages.pop(),K=K,
                    out='fp32' if bf or group=='wo_b' else 'bf16',fmts=sorted({m['fmt'] for m in ms}),mats=ms,
                    regions=sorted({int(r) for m in ms for r in m['regions']})))
    return phases


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--canonical',type=Path,required=True)
    ap.add_argument('--ref',type=Path,required=True)
    ap.add_argument('--prepared-plan',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();pins={}
    def load(p):pins[str(p)]=F.sha(p);return json.loads(p.read_text())
    sm=load(a.canonical/'stage_map.json');rb=sm['region_bounds'];bfs=set(sm['BF_site_IDs'])|{P.NEW_BF}
    experts={L:load(a.ref/f'ctx1048576_L{L:02d}.json')['experts'] for L in range(40)}
    ents={L:[] for L in range(40)};mp=a.canonical/'matrix_map.jsonl.gz';pins[str(mp)]=F.sha(mp)
    with gzip.open(mp,'rt') as f:
        for line in f:
            x=json.loads(line);L=x['layer']
            if L in ents and (x['expert'] is None or x['expert'] in experts[L]):ents[L].append(x)
    full=profiles(canonical_phases(ents,rb,bfs),rb,bfs)
    prepared=load(a.prepared_plan);old=profiles(prepared['phases'],rb,bfs)
    completed=[n for n in old if n.startswith('L20.') and any(s in n for s in ['attn.wo_a','ffn.experts_gu','ffn.down'])]
    classes=collections.defaultdict(list)
    for name,row in full.items():classes[digest(row['control_profile'])].append(name)
    existing=collections.defaultdict(list)
    for name,row in old.items():existing[digest(row['control_profile'])].append(name)
    covered={digest(old[name]['control_profile']) for name in completed}
    # Execution unit is one full return region, not a smaller pair/shape.
    region_classes=collections.defaultdict(list)
    prepared_regions=collections.defaultdict(list)
    completed_regions=set()
    for name,row in full.items():
        for reg,profile in row['control_profile']:
            region_classes[digest(profile)].append(dict(group=name,region=reg))
    for name,row in old.items():
        for reg,profile in row['control_profile']:
            sig=digest(profile)
            prepared_regions[sig].append(dict(group=name,region=reg))
            if name in completed:completed_regions.add(sig)
    region_next=[]
    for sig,members in sorted(region_classes.items()):
        if sig in completed_regions:continue
        ready=prepared_regions.get(sig,[])
        region_next.append(dict(signature=sig,members=members,prepared_representatives=ready,
            minimum_next_representative=ready[0] if ready else members[0],prepared_inputs_available=bool(ready)))
    rows=[]
    for sig,names in sorted(classes.items()):
        previous=sorted(existing.get(sig,[]));done=sig in covered
        rows.append(dict(signature=sig,members=sorted(names),measured_L20=done,
            available_prepared=previous,minimum_next_representative=None if done else (previous[0] if previous else names[0]),
            prepared_inputs_available=bool(previous),phase_count=len(full[names[0]]['phases'])))
    out=dict(scope='Static control profiles, not all-layer numerical/latency/physical PASS',layers=list(range(40)),
        selected_experts=experts,source_sha256=pins,geometry=dict(NP=32,R=1,NBF=5,PHW=3,VAW=17,KMAX=6144),
        placement='Exact source R93+520 delta kept fixed; no phase elimination credit',
        completed_groups=completed,full_groups=len(full),prepared_groups=len(old),classes=rows,
        full_region_classes=len(region_classes),completed_region_classes=len(completed_regions),
        minimum_next_region_classes=region_next,
        next_count=sum(not x['measured_L20'] for x in rows),profiles=full,
        claim='Class equality keeps ordered local slots, walker segments and output-row/tag structure. Numerical data and instantiated full-die consumer/clock timing still require their own authority.')
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,indent=1)+'\n')
    print('groups',len(full),'unique classes',len(rows),'completed classes',len(covered),'missing',out['next_count'],flush=True)
    print('region classes',len(region_classes),'additional',len(region_next),'prepared',sum(x['prepared_inputs_available'] for x in region_next),flush=True)
    for row in rows:
        if not row['measured_L20']:print(row['minimum_next_representative'],'prepared',row['prepared_inputs_available'],'phases',row['phase_count'],flush=True)

if __name__=='__main__':main()
