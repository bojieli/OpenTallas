#!/usr/bin/env python3
"""Propose a collision-free fault tree on an exact inventory; no physical admission.

Every added stage is the closed resettable qkd_astk_fault_join. Long same-root
links get real duplicate-input pipe stages. Cross-root transport uses distinct
unused payload bits of existing lanes. The emitted plan still requires native
clock/reset/phase checks and actual bus/case regeneration before any use.
"""
import argparse
import json
import heapq
import math
from collections import defaultdict
from pathlib import Path

CELL=21.6
REACH=405.0

def distance(a,b):return abs(a[0]-b[0])+abs(a[1]-b[1])


class Sites:
    def __init__(self,obstacles):
        self.bins=defaultdict(list)
        self.limit=[max(r[2] for r in obstacles),max(r[3] for r in obstacles)]
        for rect in obstacles:self.add(rect)
    def keys(self,r):
        for x in range(math.floor(r[0]/100),math.floor(r[2]/100)+1):
            for y in range(math.floor(r[1]/100),math.floor(r[3]/100)+1):yield x,y
    def add(self,r):
        for key in self.keys(r):self.bins[key].append(r)
    def free(self,x,y):
        if min(x,y)<0 or x+CELL>self.limit[0] or y+CELL>self.limit[1]:return False
        r=[x-1.08,y-1.08,x+CELL+1.08,y+CELL+1.08]
        return not any(r[0]<q[2] and q[0]<r[2] and r[1]<q[3] and q[1]<r[3]
                       for key in self.keys(r) for q in self.bins[key])
    def find(self,target,inputs):
        gx,gy=[round(v/CELL) for v in target]
        candidates=[]
        for dx in range(-20,21):
            for dy in range(-20,21):
                x,y=(gx+dx)*CELL,(gy+dy)*CELL
                pins=[[x+.042,y+10.812],[x+.042,y+10.956]]
                if any(distance(p,pins[k])>REACH for k,p in enumerate(inputs)):continue
                if self.free(x,y):candidates.append((distance([x+CELL/2,y+CELL/2],target),x,y))
        if not candidates:return None
        _,x,y=min(candidates);return [round(x,4),round(y,4)]


def propose(inv):
    sites=Sites(inv['physical_obstacles']);nodes=[];transports=[];points={};lat={};clock={};reset={};source_ids=[]
    physical_requirements=list(inv['requirements'])
    def add(a,b,kind,xy,ck,rst):
        name='fault_'+str(len(nodes));x,y=xy
        pins=[[x+.042,y+10.812],[x+.042,y+10.956]]
        distances=[distance(points[a],pins[0])]
        if b!=name:distances.append(distance(points[b],pins[1]))
        if max(distances)>REACH+1e-6:raise ValueError('unbounded same-root edge')
        if clock[a]!=ck or (b!=name and clock[b]!=ck):raise ValueError('untransported clock crossing')
        nodes.append(dict(id=name,a=a,b=b,kind=kind,latency=1,master='qkd_astk_fault_join',
                          placement=dict(x=x,y=y,orient='R0'),clock=ck,reset=rst,
                          edge_manhattan_um=[round(d,4) for d in distances]))
        sites.add([x,y,x+CELL,y+CELL]);points[name]=[x+21.558,y+10.812]
        clock[name]=ck;reset[name]=rst;lat[name]=max(lat[a],lat.get(b,0))+1
        return name
    def sticky(a):
        xy=sites.find(points[a],[points[a]])
        if xy is None:raise ValueError('no legal sticky site near '+a)
        name='fault_'+str(len(nodes));return add(a,name,'sticky',xy,clock[a],reset[a])
    def route(a,target):
        if distance(points[a],target)<=REACH:return a
        first=sites.find(points[a],[points[a],points[a]])
        if first is None:raise ValueError('no source escape site '+a)
        start=tuple(round(v/CELL) for v in first);queue=[];parent={start:None};cost={start:0}
        def output(g):return [g[0]*CELL+21.558,g[1]*CELL+10.812]
        heapq.heappush(queue,(distance(output(start),target),start));goal=None;visited=set()
        steps=[(d,0) for d in (-16,-12,-8,-4,-1,1,4,8,12,16)]+[(0,d) for d in (-16,-12,-8,-4,-1,1,4,8,12,16)]+[(x,y) for x in (-8,-4,4,8) for y in (-8,-4,4,8)]
        while queue and len(visited)<200000:
            _,g=heapq.heappop(queue)
            if g in visited:continue
            visited.add(g);p=output(g)
            if distance(p,target)<=REACH-50:goal=g;break
            for dx,dy in steps:
                nxt=(g[0]+dx,g[1]+dy);x,y=nxt[0]*CELL,nxt[1]*CELL
                if not sites.free(x,y):continue
                value=cost[g]+distance(p,output(nxt))
                if value<cost.get(nxt,float('inf')):
                    cost[nxt]=value;parent[nxt]=g
                    heapq.heappush(queue,(value+distance(output(nxt),target),nxt))
        if goal is None:raise ValueError('no bounded collision-free routing corridor '+str(dict(source=a,xy=points[a],target=target,visited=len(visited))))
        path=[]
        while goal is not None:path.append(goal);goal=parent[goal]
        path.reverse();cursor=0
        while distance(points[a],target)>REACH:
            # Compress the search corridor to the farthest legal single registered hop.
            options=[j for j in range(cursor,len(path))
                     if distance(points[a],[path[j][0]*CELL+.042,path[j][1]*CELL+10.956])<=REACH
                     and sites.free(path[j][0]*CELL,path[j][1]*CELL)]
            if not options:raise ValueError('search corridor cannot be realized as registered hops: '+str(dict(source=a,position=points[a],target=target,cursor=cursor,pathlen=len(path),remaining=path[cursor:cursor+4])))
            cursor=max(options);g=path[cursor]
            a=add(a,a,'pipe',[g[0]*CELL,g[1]*CELL],clock[a],reset[a]);cursor+=1
        return a
    def fold(group,allow_pipes):
        group=list(group)
        while len(group)>1:
            pairs=sorted((distance(points[a],points[b]),a,b) for j,a in enumerate(group) for b in group[j+1:])
            selected=None
            for d,a,b in pairs:
                if d>2*REACH:break
                target=[(points[a][k]+points[b][k])/2 for k in (0,1)]
                xy=sites.find(target,[points[a],points[b]])
                if xy is not None:selected=(a,b,xy);break
            if selected is None:
                if not allow_pipes:break
                _,a,b=pairs[0]
                routed=route(a,points[b])
                if routed==a:raise ValueError('nearby pair has no legal fold site; explicit detour required')
                group.remove(a);group.append(routed);continue
            a,b,xy=selected;group.remove(a);group.remove(b)
            group.append(add(a,b,'join',xy,clock[a],reset[a]))
        return group
    by_clock=defaultdict(list)
    sources=[]
    for s in inv['sources']:
        s=dict(s);name=s['id'];p=s['pin_xy'] or s.get('successor_native_pin_xy')
        if p is None:raise ValueError('no proven physical source position '+name)
        source_ids.append(name);points[name]=p;lat[name]=0;clock[name]=s['clock'];reset[name]=s['reset'];sources.append(s)
        by_clock[s['clock']].append(sticky(name) if s['requires_sticky_latch'] else name)
    core=inv['consumer']['clock'];core_roots=fold(by_clock.pop(core),False)
    used=set()
    for ck,group in sorted(by_clock.items()):
        roots=fold(group,False)
        available=[(l,b) for l in inv['spare_transport_candidates'] if l['source_clock']==ck for b in l['free_bits']]
        for root in roots:
            choices=[(distance(points[root],l['input_pin_xy'][str(b)]),l['id'],b,l) for l,b in available if (l['id'],b) not in used]
            if not choices:raise ValueError('no exact unused regional transport')
            _,_,bit,lane=min(choices,key=lambda x:x[:3]);used.add((lane['id'],bit));target=lane['input_pin_xy'][str(bit)]
            root=route(root,target)
            name='transport_'+str(len(transports))
            transports.append(dict(id=name,source=root,latency_cycles=lane['conservative_model_cycles'],lane_id=lane['id'],
                                   payload_bit=bit,stations=lane['stations'],physical_price_cycles=lane['physical_price_cycles'],
                                   timing_basis=lane['timing_basis'],ingress_manhattan_um=distance(points[root],target)))
            points[name]=lane['output_pin_xy'][str(bit)];clock[name]=lane['destination_clock'];reset[name]=lane['destination_reset']
            lat[name]=lat[root]+lane['conservative_model_cycles'];core_roots.append(name)
    root=fold(core_roots,True)[0];target=inv['consumer']['pin_xy']
    root=route(root,target)
    # Place the final sticky cell close enough to its consumer as well as its input.
    xy=sites.find(target,[points[root]])
    if xy is None:raise ValueError('no final sticky site')
    x,y=xy
    if distance([x+21.558,y+10.812],target)>REACH:raise ValueError('final consumer edge too long')
    name='fault_'+str(len(nodes));sink=add(root,name,'sticky',xy,core,inv['consumer']['reset'])
    return dict(schema='opentallas.kv_fault_plane_candidate.v1',status='CANDIDATE_NOT_PHYSICALLY_ADMITTED',
                sources=sources,nodes=nodes,transports=transports,sink=sink,
                retirement_quiet_cycles=lat[sink]+2,max_leaf_latency_bound=lat[sink],
                source_count=len(sources),binary_join_count=sum(n['kind']=='join' for n in nodes),
                sticky_cell_count=sum(n['kind']=='sticky' for n in nodes),pipe_cell_count=sum(n['kind']=='pipe' for n in nodes),
                added_cell_count=len(nodes),added_cell_area_um2=round(len(nodes)*CELL*CELL,4),
                consumed_existing_payload_bits=len(transports),
                physical_blockers=inv['physical_blockers'],
                requirements=physical_requirements+[
                    'Geometry uses first available LEF rectangles; actual native bound pin and full routed path checks required',
                    'New reset and clock consumers are unimplemented; local reset release calendar and native clock corridor required',
                    'Fixed-cycle transport model is conservative metadata, not evidence of actual age or CDC correctness',
                    'Existing fault retirement guard must be extended/priced to this candidate bound before admission'])


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('inventory',type=Path);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();doc=propose(json.loads(a.inventory.read_text()));a.out.write_text(json.dumps(doc,indent=1)+'\n')
    print(json.dumps({k:doc[k] for k in ('source_count','binary_join_count','sticky_cell_count','pipe_cell_count','added_cell_count','added_cell_area_um2','consumed_existing_payload_bits','max_leaf_latency_bound')}))
if __name__=='__main__':main()
