#!/usr/bin/env python3
"""Joint station/delay-bank reservation with transactional rollback.

Preserves actual20um transit station and proposed32.4um DEPTH8 bank shapes.
No placement result qualifies physical views, clock, PDN or routing capacity.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
from hbm_relay_station_inventory import Index, center, connect, length, sample, overlap
from hbm_relay_channel_model import channel_path

class RollbackIndex(Index):
    def rollback(self, count):
        self.boxes=self.boxes[:count]
        for k in list(self.buckets):
            self.buckets[k]=[i for i in self.buckets[k] if i<count]
            if not self.buckets[k]:del self.buckets[k]

def square(p,side):return [p[0]-side/2,p[1]-side/2,p[0]+side/2,p[1]+side/2]
def physical_obstacles(placement):
    """Native macro reservations are physical obstacles even before instantiation."""
    result=[];seen=set()
    for inst in placement['insts']:
        b=inst['box_um'] if 'box_um' in inst else [inst['x'],inst['y'],inst['x']+inst['w'],inst['y']+inst['h']]
        result.append({'name':inst.get('name','instance'),'box_um':b,'source':'insts'});seen.add(tuple(b))
    for key in ('native_owner_bays','native_descriptor_bays','native_result_store_bays'):
        for n,r in enumerate(placement.get(key,[])):
            if tuple(r['box_um']) not in seen:
                result.append({'name':r.get('name',f"{key}:{r.get('sm',n)}"),'box_um':r['box_um'],'source':key});seen.add(tuple(r['box_um']))
    return result

def macros(placement):return [r['box_um'] for r in physical_obstacles(placement)]

def placement_exclusions(placement):
    """Control escape/U corridors exclude result stations but are not hard macros.

    result_pin_bays intentionally admit result endpoints, so are not exclusions
    for this owner. They remain explicit reservations against unrelated macros.
    """
    return [dict(r,source=key) for key in ('native_control_escape_bays','native_control_u_corridors') for r in placement.get(key,[])]


def complex_connect(a,b,physical,ignore,width,max_length):
    """Shortest local rectilinear path when simple obstacle-edge doglegs fail."""
    pad=(max_length-length([a,b]))/2+1
    region=[max(1,min(a[0],b[0])-pad),max(1,min(a[1],b[1])-pad),min(physical.outline[0]-1,max(a[0],b[0])+pad),min(physical.outline[1]-1,max(a[1],b[1])+pad)]
    if min(region[2]-region[0],region[3]-region[1])<=0:return None
    offset=lambda p:[p[0]-region[0],p[1]-region[1]]
    boxes=[]
    for i in physical.near(region):
        if i in ignore:continue
        c=physical.boxes[i];boxes.append([c[0]-region[0],c[1]-region[1],c[2]-region[0],c[3]-region[1]])
    try:path=channel_path(offset(a),offset(b),boxes,[region[2]-region[0],region[3]-region[1]],width/2+2.16)
    except ValueError:return None
    if length(path)>max_length+1e-7:return None
    return [[p[0]+region[0],p[1]+region[1]] for p in path]

def candidate_positions(target,side,occupied,offsets):
    """Include exact obstacle-edge centres; a coarse lattice can miss narrow bays."""
    region=[target[0]-280,target[1]-280,target[0]+280,target[1]+280]
    xs={target[0]};ys={target[1]};gap=side/2+2.160001
    for n in occupied.near(region):
        b=occupied.boxes[n]
        xs.update((b[0]-gap,b[2]+gap));ys.update((b[1]-gap,b[3]+gap))
    xs=sorted((x for x in xs if abs(x-target[0])<280),key=lambda x:abs(x-target[0]))[:30]
    ys=sorted((y for y in ys if abs(y-target[1])<280),key=lambda y:abs(y-target[1]))[:30]
    points={(round(target[0]+dx,6),round(target[1]+dy,6)) for dx,dy in offsets}
    points.update((round(x,6),round(y,6)) for x in xs for y in ys)
    return [list(q) for q in sorted(points,key=lambda q:(abs(q[0]-target[0])+abs(q[1]-target[1]),q))]

def solve(paths,placement,bank_model, *, rings=12,order='longest'):
    choice=bank_model['choices'][0]
    if choice['depth']!=8 or choice['proposed_bank_um']!=[32.4,32.4]:raise ValueError('requires full64bit8cycle32.4um bank')
    ledger={(r['bus'],r['group']):r for r in choice['rows']}
    physical=RollbackIndex(paths['outline_um']);occupied=RollbackIndex(paths['outline_um'])
    for b in macros(placement):physical.add(b);occupied.add(b)
    reserved_corridors=[r['box_um'] for r in placement_exclusions(placement)]
    for b in reserved_corridors:occupied.add(b)
    eids={};endpoint_failures=[]
    for b in paths['endpoint_boxes']:
        if not occupied.legal(b):endpoint_failures.append(b)
        eids[tuple(b)]=physical.add(b);occupied.add(b)
    if endpoint_failures:raise ValueError(f'{len(endpoint_failures)} endpoints collide with supplied combined obstacles')
    work=[(r,g,k) for r in paths['result_leaves'] for k,g in enumerate(r['groups'])]
    keys={'longest':lambda x:(-x[1]['route_length_um'],x[0]['bus'],x[2]),'shortest':lambda x:(x[1]['route_length_um'],x[0]['bus'],x[2]),'banks':lambda x:(-ledger[x[0]['bus'],x[2]]['bank_count'],x[0]['bus'],x[2])}
    work.sort(key=keys[order]);offsets=sorted(((x*22.16,y*22.16) for x in range(-rings,rings+1) for y in range(-rings,rings+1)),key=lambda p:(abs(p[0])+abs(p[1]),p))
    chains=[];failed=[]
    for r,g,k in work:
        if 'path_um' not in g:
            failed.append({'bus':r['bus'],'group':k,'failure':'upstream path absent'});continue
        for exponent in (1.0,.9,1.1,.8,1.2):
            row=ledger[r['bus'],k]
            src,dst=g['source_station']['box_um'],g['sink_station']['box_um'];prev=center(src);end=center(dst);pid=eids[tuple(src)]
            nbank=row['bank_count'];nsingle=row['transport_stations']+row['remaining_single_cycle_stations']-2
            node_count=nbank+nsingle+2
            mark=(len(physical.boxes),len(occupied.boxes));prevside=20;cycle=1
            chain={'bus':r['bus'],'group':k,'bit_indices':g['bit_indices'],'arc_exponent':exponent,'required_bank_count':nbank,'required_single_count':nsingle+2,'stations':[{'box_um':src,'kind':'source','cycles':1,'stage_exit_cycle':1}],'hops':[]}
            for j in range(1,node_count):
                last=j==node_count-1;target=sample(g['path_um'],g['route_length_um']*(j/(node_count-1))**exponent)
                prefer_bank=(row['bank_count']-nbank)<j*row['bank_count']/max(1,node_count-2)
                sizes=[20] if last else (([32.4,20] if prefer_bank else [20,32.4]) if nbank else [20])
                if not last and not nsingle:sizes=[32.4]
                accepted=None
                for side in sizes:
                    positions=[end] if last else candidate_positions(target,side,occupied,offsets)
                    for q in positions:
                        qb=dst if last else square(q,side)
                        if not last and not occupied.legal(qb):continue
                        qid=eids[tuple(dst)] if last else None
                        if length([prev,q])+prevside+side>300+1e-7:continue
                        path=connect(prev,q,physical,{pid,qid},len(g['bit_indices'])*.080)
                        if path is None:path=complex_connect(prev,q,physical,{pid,qid},len(g['bit_indices'])*.080,300-prevside-side)
                        if path is None or length(path)+prevside+side>300+1e-7:continue
                        if length([q,end])>(node_count-j-1)*260+1e-7:continue
                        if j==node_count-2:
                            finish=connect(q,end,physical,{eids[tuple(dst)]},len(g['bit_indices'])*.080)
                            if finish is None:finish=complex_connect(q,end,physical,{eids[tuple(dst)]},len(g['bit_indices'])*.080,280-side)
                            if finish is None or length(finish)+side+20>300+1e-7:continue
                        accepted=(q,qb,qid,path,side);break
                    if accepted:break
                if not accepted:
                    chain['failure']={'node':j,'target_um':target,'previous_um':prev,'unplaced_banks':nbank,'unplaced_interior_singles':nsingle,'reason':'local constructive search exhausted; rolled back all partial boxes and wire reservations'};break
                q,qb,qid,path,side=accepted
                if not last:
                    qid=physical.add(qb);occupied.add(qb)
                    if side>20:nbank-=1
                    else:nsingle-=1
                cycles=8 if side>20 else 1;cycle+=cycles
                chain['stations'].append({'box_um':qb,'kind':'sink' if last else ('delay_bank8' if side>20 else 'single_cycle'),'cycles':cycles,'stage_exit_cycle':cycle})
                chain['hops'].append({'path_um':path,'centre_length_um':length(path),'conservative_pin_length_um':length(path)+prevside+side})
                for u,v in zip(path,path[1:]):
                    width=len(g['bit_indices'])*.080
                    occupied.add([min(u[0],v[0])-width/2,min(u[1],v[1])-width/2,max(u[0],v[0])+width/2,max(u[1],v[1])+width/2])
                prev,pid,prevside=q,qid,side
            if 'failure' in chain:
                physical.rollback(mark[0]);occupied.rollback(mark[1]);failed.append(chain)
            else:
                if cycle!=72 or nbank or nsingle:raise ValueError('complete chain violates fixed72cycle ledger')
                chains.append(chain);break
    return {'schema':'opentallas.hbm_relay_bank_inventory.v1','selected':False,'status':'FULL_CONSTRUCTIVE_PACKING' if len(chains)==192 else 'PARTIAL_CONSTRUCTIVE_PACKING','scope':'geometric reservation only; actualmacro pin/timing,clock,PDN and fulltraffic qualification open','outline_um':paths['outline_um'],'order':order,'search_rings':rings,'rollback_partial_chains':True,'required_slices':192,'complete_slices':len(chains),'candidate_cycles':72,'required_banks':725,'required_singles':8024,'required_area_um2':3970676,'endpoint_boxes':paths['endpoint_boxes'],'reserved_station_boxes':len(physical.boxes)-len(macros(placement)),'chains':chains,'failed_attempts':failed,'unresolved_slices':[{'bus':r['bus'],'group':k} for r,g,k in work if (r['bus'],k) not in {(c['bus'],c['group']) for c in chains}]}

def validate(result,placement):
    index=Index(result['outline_um']);ids={};errors=[];stations=[]
    for b in macros(placement):index.add(b)
    for b in result['endpoint_boxes']:stations.append((b,1))
    for c in result['chains']:
        if sum(s['cycles'] for s in c['stations'])!=72:errors.append({'wrong_latency':c['bus']})
        if any(s['cycles'] not in (1,8) for s in c['stations']):errors.append({'invalid_primitive_latency':c['bus']})
        for s in c['stations']:
            if s['kind'] not in ('source','sink'):stations.append((s['box_um'],s['cycles']))
    for b,cycles in stations:
        side=32.4 if cycles==8 else 20
        if abs(b[2]-b[0]-side)>1e-6 or abs(b[3]-b[1]-side)>1e-6:errors.append({'wrong_shape':b})
        if not index.legal(b):errors.append({'collision':b})
        if any(overlap(b,r['box_um'],2.16) for r in placement_exclusions(placement)):errors.append({'control_corridor_collision':b})
        ids[tuple(b)]=index.add(b)
    hops=0;worst=0
    for c in result['chains']:
        for j,h in enumerate(c['hops']):
            hops+=1;a,b=c['stations'][j:j+2];p=h['path_um'];width=len(c['bit_indices'])*.080
            bound=length(p)+(a['box_um'][2]-a['box_um'][0])+(b['box_um'][2]-b['box_um'][0]);worst=max(worst,bound)
            if bound>300+1e-6:errors.append({'long_hop':c['bus'],'node':j})
            if length([p[0],center(a['box_um'])])>1e-6 or length([p[-1],center(b['box_um'])])>1e-6:errors.append({'wrong_endpoint':c['bus'],'node':j})
            ignore={ids[tuple(a['box_um'])],ids[tuple(b['box_um'])]}
            for u,v in zip(p,p[1:]):
                if u[0]!=v[0] and u[1]!=v[1]:errors.append({'nonrectilinear':c['bus'],'node':j})
                rect=[min(u[0],v[0])-width/2,min(u[1],v[1])-width/2,max(u[0],v[0])+width/2,max(u[1],v[1])+width/2]
                if not index.legal(rect,ignore):errors.append({'blocked_hop':c['bus'],'node':j})
    return {'checked_station_boxes':len(stations),'checked_hops':hops,'worst_pin_hop_um':worst,'error_count':len(errors),'errors':errors}

def main():
    p=argparse.ArgumentParser();p.add_argument('--paths',type=Path,required=True);p.add_argument('--placement',type=Path,required=True);p.add_argument('--model',type=Path,default=Path('results/uarch/hbm_result_delay_bank_20261007/model.json'));p.add_argument('--out',type=Path,required=True);p.add_argument('--order',choices=['longest','shortest','banks'],default='longest');p.add_argument('--rings',type=int,default=12);a=p.parse_args()
    sources=[a.paths,a.placement,a.model,Path(__file__),Path(__file__).with_name('hbm_relay_station_inventory.py'),Path(__file__).with_name('hbm_relay_channel_model.py')]
    initial_hashes={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in sources}
    result=solve(json.loads(a.paths.read_text()),json.loads(a.placement.read_text()),json.loads(a.model.read_text()),rings=a.rings,order=a.order)
    result['validation']=validate(result,json.loads(a.placement.read_text()))
    result['source_sha256']={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in sources}
    if result['source_sha256']!=initial_hashes:raise ValueError('input/tool changed during construction; refuse mixed provenance')
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('chains','failed_attempts','endpoint_boxes','source_sha256','validation')}));print(json.dumps(result['validation']))
if __name__=='__main__':main()
