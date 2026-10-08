#!/usr/bin/env python3
"""Constructive relay station packing; failed searches are not infeasibility proofs.

Full 20um square reservations, conservative 300um pin-to-pin bound, immutable
endpoint boxes. This is a candidate inventory, never physical qualification.
"""
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path

SIZE=20.0
GAP=2.16

class Index:
    def __init__(self, outline):
        self.outline=outline;self.buckets=defaultdict(list);self.boxes=[]
    def near(self,b):
        ids=set()
        for x in range(math.floor((b[0]-GAP)/100),math.floor((b[2]+GAP)/100)+1):
            for y in range(math.floor((b[1]-GAP)/100),math.floor((b[3]+GAP)/100)+1):
                ids.update(self.buckets[x,y])
        return ids
    def add(self,b):
        n=len(self.boxes);self.boxes.append(b)
        for x in range(math.floor(b[0]/100),math.floor(b[2]/100)+1):
            for y in range(math.floor(b[1]/100),math.floor(b[3]/100)+1):self.buckets[x,y].append(n)
        return n
    def legal(self,b,ignore=(),gap=GAP):
        if min(b[:2])<1 or b[2]>self.outline[0]-1 or b[3]>self.outline[1]-1:return False
        return not any(overlap(b,self.boxes[i],gap) for i in self.near(b) if i not in ignore)

def overlap(a,b,gap=0):
    return a[0]<b[2]+gap-1e-8 and b[0]<a[2]+gap-1e-8 and a[1]<b[3]+gap-1e-8 and b[1]<a[3]+gap-1e-8

def box(p):return [p[0]-10,p[1]-10,p[0]+10,p[1]+10]
def center(b):return [(b[0]+b[2])/2,(b[1]+b[3])/2]
def length(path):return sum(abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(path,path[1:]))
def sample(path,d):
    for a,b in zip(path,path[1:]):
        l=length([a,b])
        if d<=l:return [a[i]+(b[i]-a[i])*d/l if l else a[i] for i in range(2)]
        d-=l
    return list(path[-1])

def connect(a,b,physical,ignore,width):
    # Centre-to-centre path plus40um bounds any choice of facing station pins.
    if length([a,b])+40>300+1e-8:return None
    candidates=[[a,[a[0],b[1]],b],[a,[b[0],a[1]],b]]
    local=[physical.boxes[i] for i in physical.near([min(a[0],b[0])-40,min(a[1],b[1])-40,max(a[0],b[0])+40,max(a[1],b[1])+40]) if i not in ignore]
    clearance=width/2+GAP+1e-6
    for c in local:
        for x in (c[0]-clearance,c[2]+clearance):candidates.append([a,[x,a[1]],[x,b[1]],b])
        for y in (c[1]-clearance,c[3]+clearance):candidates.append([a,[a[0],y],[b[0],y],b])
    candidates.sort(key=length)
    for p in candidates:
        if length(p)+40>300+1e-8:continue
        valid=True
        for u,v in zip(p,p[1:]):
            rect=[min(u[0],v[0])-width/2,min(u[1],v[1])-width/2,max(u[0],v[0])+width/2,max(u[1],v[1])+width/2]
            if not physical.legal(rect,ignore):valid=False;break
        if valid:return p
    return None

def build(paths,placement, *, search_rings=6, depth_override=None):
    outline=paths['outline_um'];physical=Index(outline);occupancy=Index(outline)
    macros=[i.get('box_um',[i['x'],i['y'],i['x']+i['w'],i['y']+i['h']]) for i in placement['insts']]
    for b in macros:physical.add(b);occupancy.add(b)
    endpoint_ids={}
    for b in paths['endpoint_boxes']:
        endpoint_ids[tuple(b)]=physical.add(b);occupancy.add(b)
    chains=[];depth=depth_override or paths['candidate_all_result_leaves_balanced_cycles']
    # Longest paths have the least room for detours and go first.
    work=sorted(((r,g,k) for r in paths['result_leaves'] for k,g in enumerate(r['groups'])),key=lambda x:(-x[1]['route_length_um'],x[0]['bus'],x[2]))
    offsets=sorted(((x*22.16,y*22.16) for x in range(-search_rings,search_rings+1) for y in range(-search_rings,search_rings+1)),key=lambda p:(abs(p[0])+abs(p[1]),p))
    for r,g,k in work:
        src=g['source_station']['box_um'];dst=g['sink_station']['box_um']
        start,end=center(src),center(dst);prev=start;pid=endpoint_ids[tuple(src)]
        chain={'bus':r['bus'],'group':k,'bit_indices':g['bit_indices'],'target_stages':depth,'stations':[{'stage':0,'box_um':src,'kind':'source'}],'hops':[]}
        chains.append(chain)
        for stage in range(1,depth):
            last=stage==depth-1;target=sample(g['path_um'],g['route_length_um']*stage/(depth-1))
            candidates=[end] if last else [[round(target[0]+dx,6),round(target[1]+dy,6)] for dx,dy in offsets]
            accepted=None
            for q in candidates:
                qb=dst if last else box(q)
                if not last and not occupancy.legal(qb):continue
                qid=endpoint_ids[tuple(dst)] if last else None
                p=connect(prev,q,physical,{pid,qid},len(g['bit_indices'])*.080)
                if p is None:continue
                if length([q,end])>(depth-stage-1)*260+1e-8:continue
                accepted=(q,qb,qid,p);break
            if accepted is None:
                chain['failure']={'stage':stage,'target_um':target,'previous_um':prev,'nearest_macro_boxes_um':sorted(macros,key=lambda b:abs(center(b)[0]-target[0])+abs(center(b)[1]-target[1]))[:3],'reason':'deterministic local candidate search exhausted; not an infeasibility proof'};break
            q,qb,qid,p=accepted
            if not last:qid=physical.add(qb);occupancy.add(qb)
            chain['stations'].append({'stage':stage,'box_um':qb,'kind':'sink' if last else 'intermediate_or_balance'})
            chain['hops'].append({'path_um':p,'centre_length_um':length(p),'conservative_pin_length_um':length(p)+40})
            for u,v in zip(p,p[1:]):
                width=len(g['bit_indices'])*.080
                occupancy.add([min(u[0],v[0])-width/2,min(u[1],v[1])-width/2,max(u[0],v[0])+width/2,max(u[1],v[1])+width/2])
            prev,pid=q,qid
    complete=[c for c in chains if 'failure' not in c]
    return {'schema':'opentallas.hbm_relay_station_inventory.v1','selected':False,'status':'constructive-partial-packing' if len(complete)!=192 else 'candidate-packing-not-physical-qualified','outline_um':outline,'station_shape_um':[20,20],'minimum_box_gap_um':GAP,'candidate_depth_cycles':depth,'required_station_count':len(work)*depth,'reserved_station_count':len(physical.boxes)-len(macros),'complete_slices':len(complete),'total_slices':len(work),'reserved_station_area_um2':(len(physical.boxes)-len(macros))*400,'chains':chains,'limitations':['Partial failed chains remain reserved; no claim of global infeasibility.','Wires are mutually shareable; track capacity, clock/reset and PDN are not qualified.','Any-point station pin allowance is conservative40um added to centre path.','Actual hardened dimensions, pin directions and timing remain required.','All192 chains must complete and combined die obstacles must pass before adoption.']}

def validate_inventory(result, paths, placement):
    """Independent replay of boxes and every emitted wire against final obstacles."""
    index=Index(result['outline_um']);errors=[];ids={}
    for inst in placement['insts']:
        index.add(inst.get('box_um',[inst['x'],inst['y'],inst['x']+inst['w'],inst['y']+inst['h']]))
    boxes=list(paths['endpoint_boxes'])+[s['box_um'] for c in result['chains'] for s in c['stations'] if s['kind']=='intermediate_or_balance']
    for b in boxes:
        if abs(b[2]-b[0]-20)>1e-6 or abs(b[3]-b[1]-20)>1e-6:errors.append({'wrong_shape':b})
        if not index.legal(b):errors.append({'illegal_box':b})
        ids[tuple(b)]=index.add(b)
    hops=0;worst=0
    for chain in result['chains']:
        width=len(chain['bit_indices'])*.080
        if 'failure' not in chain and len(chain['stations'])!=result['candidate_depth_cycles']:errors.append({'wrong_depth':chain['bus']})
        for j,hop in enumerate(chain['hops']):
            hops+=1;p=hop['path_um'];bound=length(p)+40;worst=max(worst,bound)
            if bound>300+1e-8:errors.append({'overlength':chain['bus'],'hop':j})
            a,b=chain['stations'][j:j+2]
            if length([p[0],center(a['box_um'])])>1e-6 or length([p[-1],center(b['box_um'])])>1e-6:errors.append({'wrong_endpoint':chain['bus'],'hop':j})
            ignore={ids[tuple(a['box_um'])],ids[tuple(b['box_um'])]}
            for u,v in zip(p,p[1:]):
                if u[0]!=v[0] and u[1]!=v[1]:errors.append({'nonrectilinear':chain['bus'],'hop':j})
                rect=[min(u[0],v[0])-width/2,min(u[1],v[1])-width/2,max(u[0],v[0])+width/2,max(u[1],v[1])+width/2]
                if not index.legal(rect,ignore):errors.append({'blocked_hop':chain['bus'],'group':chain['group'],'hop':j})
    return {'checked_boxes':len(boxes),'checked_hops':hops,'worst_conservative_pin_hop_um':worst,'error_count':len(errors),'errors':errors}

def combined_obstacle_audit(result, paths, combined):
    stations=[('endpoint',i,b) for i,b in enumerate(paths['endpoint_boxes'])]
    stations += [(c['bus'],s['stage'],s['box_um']) for c in result['chains'] for s in c['stations'] if s['kind']=='intermediate_or_balance']
    index=Index(result['outline_um']);names=[]
    for inst in combined['insts']:
        names.append(inst['name']);index.add(inst.get('box_um',[inst['x'],inst['y'],inst['x']+inst['w'],inst['y']+inst['h']]))
    clashes=[]
    for bus,stage,b in stations:
        for n in sorted(index.near(b)):
            if overlap(b,index.boxes[n],GAP):clashes.append({'bus':bus,'stage':stage,'box_um':b,'macro':names[n],'macro_box_um':index.boxes[n]})
    counts=defaultdict(int)
    for c in clashes:counts[c['macro']]+=1
    return {'scope':'separate combined VM8 owner/descriptor candidate; no geometry adopted','station_macro_conflicts':len(clashes),'by_macro':dict(sorted(counts.items())),'clashes':clashes}

def main():
    p=argparse.ArgumentParser();p.add_argument('--paths',type=Path,required=True);p.add_argument('--placement',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--search-rings',type=int,default=6);p.add_argument('--depth',type=int);a=p.parse_args()
    result=build(json.loads(a.paths.read_text()),json.loads(a.placement.read_text()),search_rings=a.search_rings,depth_override=a.depth)
    result['validation']=validate_inventory(result,json.loads(a.paths.read_text()),json.loads(a.placement.read_text()))
    result['source_sha256']={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in [a.paths,a.placement,Path(__file__)]}
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('chains','source_sha256','validation')}))
if __name__=='__main__':main()
