"""Compare actual source-assigned pin motion for the optional band-1 mirror.

Uses immutable historical bus endpoints and the wider current rectangle plan.
Missing peer pin plans remain explicit; this is not a relay or route verdict.
"""
import json,math,hashlib,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def xy(inst,p):
    if p.get('interior'): pts=p['positions_xy_um']
    else:
        lo,hi=p['range_um'];f=p['face']
        pts=[([0,t] if f=='W' else [inst['w'],t] if f=='E' else [t,0] if f=='S' else [t,inst['h']]) for t in (lo,hi)]
    o=inst.get('o','R0');out=[]
    for x,y in pts:
        if o in ('MY','R180'):x=inst['w']-x
        if o in ('MX','R180'):y=inst['h']-y
        out.append((inst['x']+x,inst['y']+y))
    return out

def compare(dump,projection):
    before={i['n']:dict(i) for i in dump['insts']}
    for i in projection['placements']:before[i['n']]=dict(i)
    before.pop('tt_up4_0',None)
    after={n:dict(i) for n,i in before.items()}
    names=[f'sp_{k}_1' for k in ('band_lanes','port_tiles','res_ser')]
    bottom=min(before[n]['y'] for n in names)
    for n,y in zip((names[2],names[1],names[0]),(bottom,bottom+522.72,bottom+2989.44)):
        after[n]['y']=y;after[n]['o']='MX'
    after['sp_port_tiles_1_f1']['y']=after[names[1]]['y']
    plans={}
    paths=list((ROOT/'results/arch/qwen_split_compute_1014/c17_source_pins').glob('*.json'))
    paths += [ROOT/'results/arch/qwen_split_compute_1014/c17_band_quarter_pins/qfd_sp_band_lanes.json']
    hashes={}
    for p in paths:
        r=json.loads(p.read_text())
        if 'master' in r:plans[r['master']]=r['ports'];hashes[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
    changed=set(n for n in after if after[n]!=before[n]);rows=[];missing=[]
    for b in dump['buses']:
        es=b['e']
        if b['c'] in ('clock_trunk','reset') or len(es)!=2 or not any(n in changed for n,p in es):continue
        pp=[]
        for n,p in es:
            i=before.get(n)
            if i is None:
                missing.append(dict(bus=b['b'],instance=n,port=p,reason='retired historical endpoint; direct-leaf lowering must replace'));break
            rec=plans.get(i['m'],{}).get(p)
            if rec is None:missing.append(dict(bus=b['b'],instance=n,port=p,master=i['m']));break
            pp.append(rec)
        if len(pp)!=2:continue
        def dist(insts):
            A=xy(insts[es[0][0]],pp[0]);B=xy(insts[es[1][0]],pp[1])
            return max(abs(a[0]-b[0])+abs(a[1]-b[1]) for a in A for b in B)
        old,new=dist(before),dist(after)
        rows.append(dict(bus=b['b'],bits=b['n'],old_pin_span_um=round(old,3),new_pin_span_um=round(new,3),delta_um=round(new-old,3),old_geometric_hops=math.ceil(old/490),new_geometric_hops=math.ceil(new/490)))
    clocks=[]
    for n in sorted(changed):
        i=before[n]
        for p,r in plans.get(i['m'],{}).items():
            if p.startswith('ck'):
                clocks.append(dict(instance=n,port=p,before=xy(i,r),after=xy(after[n],r),R_ps=None,phi_ps=None))
    return dict(schema='opentallas.qwen.band1-source-pin-sensitivity.v1',scope='Actual source-assigned pin bounding spans; historical P2P endpoint graph. Not allocated routes, cuts or compiler ages.',placements=[after[n] for n in sorted(changed)],pin_plan_sha256=hashes,paired_paths=rows,missing_peer_pin_plans=missing,transformed_clock_entries=clocks,qualification=False,critical_upper_geometric_depth='27 unchanged: band2 remains limiting',notes=['Clock XY transformed with actual MX; measured root route/phi-R remains unavailable.','Geometric hops are ceil(max pin bounding span /490), never actual relay counts.','Legacy res_ser and VM peers without complete source pin plans remain explicit gaps.'])

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('dump',type=Path);a.add_argument('projection',type=Path);a.add_argument('output',type=Path);s=a.parse_args()
    r=compare(json.loads(s.dump.read_text()),json.loads(s.projection.read_text()));r['input_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (s.dump,s.projection)};s.output.parent.mkdir(parents=True,exist_ok=True);s.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(dict(paired_paths=len(r['paired_paths']),missing=len(r['missing_peer_pin_plans']),clocks=len(r['transformed_clock_entries']),largest_worsening=sorted(r['paired_paths'],key=lambda p:-p['delta_um'])[:3])))
