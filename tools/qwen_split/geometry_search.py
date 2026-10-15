#!/usr/bin/env python3
"""Reproducible locality proposals from actual assigned pins, never route proof."""
import argparse, copy, hashlib, json, math
from collections import defaultdict
from pathlib import Path
from band1_pin_sensitivity import xy
from placement_repack import overlap, validate


def span(a, pa, b, pb):
    return max(abs(x-u)+abs(y-v) for x,y in xy(a,pa) for u,v in xy(b,pb))


def load(dump, projection, pin_dirs, actual_model=None):
    raw=json.loads(dump.read_text());model={i['n']:dict(i) for i in raw['insts']}
    projection_data=json.loads(projection.read_text())
    if actual_model:
        for i in json.loads(actual_model.read_text())['insts']:
            model[i['n']]={**model.get(i['n'],{}),**i}
    for i in projection_data['placements']:
        if i['n'] in model:
            model[i['n']].update({k:i[k] for k in ('x','y','o')})
        else:model[i['n']]=dict(i)
    for n in projection_data['retired']:model.pop(n,None)
    plans={};hashes={}
    for directory in pin_dirs:
        for p in sorted(directory.glob('*.json')):
            r=json.loads(p.read_text())
            if 'master' in r and 'ports' in r:
                plans[r['master']]=r['ports'];hashes[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
    return raw,model,plans,hashes


def analyze(raw,model,plans):
    known=[];missing=[];incident=defaultdict(list)
    for b in raw['buses']:
        if b['c'] in ('clock_trunk','reset'):continue
        if len(b['e'])!=2:
            missing.append(dict(bus=b['b'],reason='multi-terminal graph requires per-bit topology'));continue
        unresolved=[]
        for n,p in b['e']:
            if n not in model or p not in plans.get(model[n]['m'],{}):unresolved.append([n,p])
        if unresolved:
            missing.append(dict(bus=b['b'],bits=b['n'],missing=unresolved));continue
        k=len(known);known.append(b)
        for n,p in b['e']:incident[n].append(k)
    def row(b):
        (n,p),(m,q)=b['e'];length=span(model[n],plans[model[n]['m']][p],model[m],plans[model[m]['m']][q])
        return dict(bus=b['b'],family=b['c'],bits=b['n'],endpoints=b['e'],pin_bound_um=round(length,3),bit_um=round(length*b['n'],3),geometric_hops=math.ceil(round(length,5)/490))
    return known,missing,incident,row


def search(raw,model,plans,known,incident):
    def edgecost(k):
        b=known[k];(n,p),(m,q)=b['e']
        return span(model[n],plans[model[n]['m']][p],model[m],plans[model[m]['m']][q])*b['n']
    costs=[edgecost(k) for k in range(len(known))];baseline=sum(costs)
    missing_incident=defaultdict(int)
    for b in raw['buses']:
        if b['c'] in ('clock_trunk','reset'):continue
        for n,p in b['e']:
            if n in model and (len(b['e'])!=2 or any(m not in model or q not in plans.get(model[m]['m'],{}) for m,q in b['e'])):missing_incident[n]+=1
    # Whole stack moves retain existing relative layout; orientations below are
    # proposals pending hierarchical LEF/macro and native clock qualification.
    groups={n:[n] for n in incident}
    for band in range(3):
        names=[f'sp_{kind}_{band}' for kind in ('band_lanes','port_tiles','res_ser')]+[f'sp_port_tiles_{band}_f1']
        groups[f'band{band}_coherent']=names
    central=[n for n in model if n in ('sp_vector_memory','sp_su64_sfu','seq_su','xs_tap','tt_ctlm') or n.startswith(('cbuf_g_','crom_g_'))]
    groups['central_coherent']=central
    proposals=[]
    for name,names in groups.items():
        affected=set(k for n in names for k in incident[n])
        if not affected:continue
        before={n:dict(model[n]) for n in names};old=sum(costs[k] for k in affected)
        operations=[('orientation',o) for o in ('R0','MX','MY','R180')] if len(names)==1 else []
        if name.startswith('sp_') or name.endswith('_coherent'):
            operations += [('translation',(dx,dy)) for dx,dy in ((-432,0),(-216,0),(216,0),(432,0),(0,-432),(0,-216),(0,216),(0,432))]
        for kind,value in operations:
            for n in names:model[n]=dict(before[n])
            if kind=='orientation':model[names[0]]['o']=value
            else:
                for n in names:model[n]['x']+=value[0];model[n]['y']+=value[1]
            if all(model[n]==before[n] for n in names):continue
            # Only changed rectangles need collision tests. Baseline may have
            # legacy unrelated overlap, which is never silently certified.
            if any(a['x']<0 or a['y']<0 or a['x']+a['w']>raw['die']['w'] or a['y']+a['h']>raw['die']['h'] for a in (model[n] for n in names)):continue
            if kind=='translation' and any(overlap(model[n],other) for n in names for other in model.values() if other['n'] not in names):continue
            new=sum(edgecost(k) for k in affected)
            if old-new<1e-4:continue
            proposals.append(dict(group=name,operation=kind,value=value,known_bit_um_saved=round(old-new,3),known_affected_before_bit_um=round(old,3),known_affected_after_bit_um=round(new,3),unresolved_incident_nets=sum(missing_incident[n] for n in names),placements=[dict(model[n]) for n in names],qualification=False,physical_gates=['actual child/macro legal orientation','clock XY and phi-R','halo clearance','full actual graph including unknown peers','allocated relay reach','cuts <=0.60','routed TT/FF/DRC']))
        for n in names:model[n]=before[n]
    proposals.sort(key=lambda r:-r['known_bit_um_saved'])
    for proposal in proposals[:40]:
        saved={n:dict(model[n]) for n in (i['n'] for i in proposal['placements'])}
        affected=set(k for n in saved for k in incident[n]);before={k:edgecost(k) for k in affected}
        model.update({i['n']:dict(i) for i in proposal['placements']})
        proposal['changed_known_legs']=[dict(bus=known[k]['b'],before_bit_um=round(before[k],3),after_bit_um=round(edgecost(k),3),before_pin_bound_um=round(before[k]/known[k]['n'],3),after_pin_bound_um=round(edgecost(k)/known[k]['n'],3),before_geometric_hops=math.ceil(round(before[k]/known[k]['n'],5)/490),after_geometric_hops=math.ceil(round(edgecost(k)/known[k]['n'],5)/490)) for k in sorted(affected) if abs(edgecost(k)-before[k])>1e-4]
        proposal['transformed_clock_entries']=[dict(instance=n,port=p,before=xy(saved[n],r),after=xy(model[n],r)) for n in saved for p,r in plans.get(model[n]['m'],{}).items() if p.startswith('ck')]
        model.update(saved)
    return baseline,proposals


def main():
    a=argparse.ArgumentParser();a.add_argument('dump',type=Path);a.add_argument('projection',type=Path);a.add_argument('--actual-model',type=Path);a.add_argument('--pin-dir',type=Path,action='append',required=True);a.add_argument('--out',type=Path,required=True);s=a.parse_args()
    raw,model,plans,hashes=load(s.dump,s.projection,s.pin_dir,s.actual_model)
    known,missing,incident,row=analyze(raw,model,plans)
    baseline,proposals=search(raw,model,plans,known,incident)
    result=dict(schema='opentallas.qwen.geometry-search.v1',scope='Assigned pin bounding span on historical P2P graph; partial graph proposal only',source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in ([s.dump,s.projection]+([s.actual_model] if s.actual_model else []))},baseline_geometry_errors=validate(list(model.values()),raw['die']),pin_plan_sha256=hashes,baseline_known_bit_um=round(baseline,3),resolved_buses=len(known),unresolved_buses=len(missing),top20=sorted((row(b) for b in known),key=lambda r:-r['bit_um'])[:20],proposal_count=len(proposals),proposals=proposals[:40],missing=missing,qualification=False,notes=['No existing production layout changed.','Pin bounding spans are conservative Manhattan bounds, not physical routes or total wire length.','Missing endpoint plans prevent global optimum or no-regression claim.','Orientation legality and halos must be checked before implementation in die flow.'])
    s.out.parent.mkdir(parents=True,exist_ok=True);s.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(resolved=len(known),unresolved=len(missing),proposals=len(proposals),best=proposals[:3]),indent=2))
if __name__=='__main__':main()
