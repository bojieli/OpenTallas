#!/usr/bin/env python3
"""Connected PHY-fit planning prototype. No route/adoption until every gate passes.

Replay same-area rectangle proposal, retain unchanged logical lane endpoints,
replace genuinely used transit slots only, and make explicit wrapper variants.
Hardened field/ROM children are preserved byte-for-byte. Pin windows are allocated
on abutting faces before per-bit registered station placement. Fail closed on
window exhaustion or unsupported same-face transits.
"""
import argparse
import collections
import copy
import json
import math
import heapq
import re
import sys
from pathlib import Path

OPP=dict(N='S',S='N',E='W',W='E')


def edge(a,b):
    if abs(a[2]-b[0])<1e-3:return 'E',[max(a[1],b[1]),min(a[3],b[3])]
    if abs(b[2]-a[0])<1e-3:return 'W',[max(a[1],b[1]),min(a[3],b[3])]
    if abs(a[3]-b[1])<1e-3:return 'N',[max(a[0],b[0]),min(a[2],b[2])]
    if abs(b[3]-a[1])<1e-3:return 'S',[max(a[0],b[0]),min(a[2],b[2])]
    raise ValueError(f'non-abutting rectangles {a} {b}')


def local_geom(part,rect,face,window):
    orient=part.get('orient','R0');fx=orient in ('MY','R180');fy=orient in ('MX','R180')
    w,h=rect[2]-rect[0],rect[3]-rect[1]
    lf=OPP[face] if (face in 'EW' and fx) or(face in 'NS' and fy) else face
    base=rect[0] if face in 'NS' else rect[1];extent=w if face in 'NS' else h
    flip=fx if face in 'NS' else fy
    win=[extent-(v-base) if flip else v-base for v in window]
    return lf,sorted(round(v,6) for v in win),'lsb_high' if flip else 'lsb_low'


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('root',type=Path);ap.add_argument('--plan',required=True,type=Path)
    ap.add_argument('--candidate',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);ap.add_argument('--report',required=True,type=Path)
    a=ap.parse_args();raw=json.loads(a.plan.read_text());proposal=json.loads(a.candidate.read_text())
    sys.path.insert(0,str(a.root));from tools.die_plan import schema as S
    model=S.Plan(raw,a.plan)
    rect=proposal['rects'];parts={p['name']:p for p in raw['partitions']};oldtypes=raw['partition_types'];ports=model.ports
    routes={r['lane']:r['parts'] for r in proposal['spatial_graph']['routes']};affected=set(routes)
    if proposal['spatial_graph']['unreachable_affected_lanes']:raise ValueError('proposal has unreachable lanes')
    oldlat=copy.deepcopy(raw.get('latency',{}).get('lanes',{}));oldlane={l['id']:copy.deepcopy(l) for l in raw['lanes']}
    removed_ports={pid for l in raw['lanes'] if l['id'] in affected for pid in l['ports']}
    oldslots={n:{s['name'] for s in oldtypes[p['type']].get('ft_slots',[])} for n,p in parts.items()}
    remove=collections.defaultdict(set);touch=set(proposal['changes'])
    for pid in removed_ports:
        p=ports[pid]
        for side in ('src','dst'):
            n,b=p[side]['part'],p[side]['bus'];touch.add(n)
            if b.endswith(('_i','_o')) and b[:-2] in oldslots[n]:remove[n].add(b[:-2])
    for path in routes.values():touch.update(path)
    variants={};original={}
    def ensure_variant(n):
        if n in variants:return
        p=parts[n];old=p['type'];name=old+'_phy1026_'+re.sub(r'\W','_',n);t=copy.deepcopy(oldtypes[old])
        t['ft_slots']=[s for s in t.get('ft_slots',[]) if s['name'] not in remove[n]]
        t['note']=t.get('note','')+'; D-S81-PHY same-area explicit used-lane wrapper variant of '+old
        r=rect[n];t['outline_um']=[round(r[2]-r[0],6),round(r[3]-r[1],6)]
        p['origin_um']=r[:2];p['type']=name;oldtypes[name]=t;variants[n]=name;original[name]=old
        if n in ('gunit','bk_sel'):
            t['hard_cores']=copy.deepcopy(proposal['packing'][n]['hard_cores'])
            for c in t['hard_cores']:c.pop('rebuild_required',None)
            if n=='bk_sel':
                tx=next(c for c in t['hard_cores'] if c['module']=='dsdv_idx_tx_n32')
                tx['lef']='physical/die_plan/s81/cores/tx_current_1026/dsdv_idx_tx_n32_trial.lef'
                tx['pins_file']='cores/tx_current_1026/dsdv_idx_tx_n32.json'
                assert(a.root/tx['lef']).exists() and (a.root/'physical/die_plan/s81'/tx['pins_file']).exists(),'fresh TX candidate source c83e00dc4 required; never crop historical LEF'
            t['internal_stations']=[]
            t['clock']['tap_um']=[round(t['outline_um'][0]-86.4,3),round(t['outline_um'][1]-86.4,3)]
        elif n.startswith('lk_'):
            north=any(m['part']==n and m['side']=='N' for m in proposal['macros'])
            wy=51.84 if north else t['outline_um'][1]-51.84
            if p.get('orient','R0') in ('MX','R180'):wy=t['outline_um'][1]-wy
            t['clock']['tap_um']=[round(t['outline_um'][0]/2,3),round(wy,3)]
    for n in sorted(touch):ensure_variant(n)
    # Preserve known direct core connectivity for every explicit wrapper variant.
    side=a.root/'physical/die_plan/s81/core_conns.json'
    if side.exists():
        conns=json.loads(side.read_text())
        for new,old in original.items():
            if old in conns:conns[new]=copy.deepcopy(conns[old])
        side.write_text(json.dumps(conns,indent=1)+'\n')
    # All old unaffected windows remain fixed. New windows use spare intervals
    # on exactly the common face; both hardened wrappers receive identical pins.
    occupied=collections.defaultdict(list)
    for p in ports.values():
        if p['id'] in removed_ports:continue
        fa=p['face'];lo,hi=sorted(p['window_um'])
        occupied[(p['src']['part'],fa)].append((lo-2,hi+2));occupied[(p['dst']['part'],OPP[fa])].append((lo-2,hi+2))
    def allocate(na,nb,width,commit=True):
        fa,bounds=edge(rect[na],rect[nb]);lo,hi=bounds;length=max(17.28,(width+1)/4.6)
        intervals=sorted(occupied[(na,fa)]+occupied[(nb,OPP[fa])]);at=lo+6.144
        for left,right in intervals:
            if right<=at:continue
            if left-at>=length+2:break
            at=max(at,right)
        if at+length>hi-6.144:
            raise ValueError(f'WINDOW_EXHAUSTED {na}/{fa}|{nb}: {width}bits need{length:.3f}um, common{bounds}, at{at:.3f}, occupied{intervals}')
        win=[round(at,6),round(at+length,6)]
        if commit:
            occupied[(na,fa)].append((at-2,at+length+2));occupied[(nb,OPP[fa])].append((at-2,at+length+2))
        return fa,win
    neighbours={n:[] for n in rect}
    nodes=list(rect)
    for i,na in enumerate(nodes):
        for nb in nodes[i+1:]:
            try:fa,span=edge(rect[na],rect[nb])
            except ValueError:continue
            if span[1]-span[0]>12:
                neighbours[na].append((nb,fa));neighbours[nb].append((na,OPP[fa]))
    def select_path(src,dst,width):
        heap=[(0,src,'')];dist={(src,''):0};prev={};end=None
        while heap:
            cost,n,inface=heapq.heappop(heap);state=(n,inface)
            if cost!=dist[state]:continue
            if n==dst:end=state;break
            for nxt,face in neighbours[n]:
                if face==inface:continue
                if (nxt.startswith('lk_') or nxt=='phy_hbm') and nxt!=dst:continue
                if nxt.startswith(('fW','fE')) and nxt!=dst and not(rect[nxt][1]<=103.68+1226.88+.01 or rect[nxt][3]>=103.68+19*1226.88-.01):continue
                try:allocate(n,nxt,width,False)
                except ValueError:continue
                ar,br=rect[n],rect[nxt];step=abs((ar[0]+ar[2]-br[0]-br[2])/2)+abs((ar[1]+ar[3]-br[1]-br[3])/2)
                nc=cost+step*(4 if n.startswith(('fW','fE')) or nxt.startswith(('fW','fE')) else 1)
                ns=(nxt,OPP[face])
                if nc<dist.get(ns,float('inf')):dist[ns]=nc;prev[ns]=state;heapq.heappush(heap,(nc,*ns))
        if end is None:raise ValueError(f'NO_WINDOW_ROUTE {src}->{dst} width{width}')
        path=[end[0]]
        while end!=(src,''):end=prev[end];path.append(end[0])
        return path[::-1]
    newports=[];slot_counts=collections.Counter();newslots=collections.defaultdict(list);route_rows=[]
    for lid,path in sorted(routes.items(),key=lambda z:(-ports[oldlane[z[0]]['ports'][0]]['width'],z[0])):
        ln=next(l for l in raw['lanes'] if l['id']==lid);pr0=ports[ln['ports'][0]];pr1=ports[ln['ports'][-1]];width=pr0['width']
        source,dest=copy.deepcopy(pr0['src']),copy.deepcopy(pr1['dst']);assert source['part']==path[0] and dest['part']==path[-1]
        path=select_path(source['part'],dest['part'],width)
        for n in path:ensure_variant(n)
        names={}
        for n in path[1:-1]:
            idx=slot_counts[n];slot_counts[n]+=1;names[n]='ft_phy'+str(idx)
        edges=[]
        for i,(na,nb) in enumerate(zip(path,path[1:])):
            fa,win=allocate(na,nb,width);src=source if i==0 else dict(part=na,bus=names[na]+'_o');dst=dest if i==len(path)-2 else dict(part=nb,bus=names[nb]+'_i')
            layers=['M7','M5'] if fa in 'NS' else ['M6','M4']
            pid=lid+'__phy1026_'+str(i);p=dict(id=pid,src=src,dst=dst,width=width,kind=pr0.get('kind','data'),face=fa,layers=layers,window_um=win,order='lsb_low');newports.append(p);edges.append(p)
            for ep,wf in ((src,fa),(dst,OPP[fa])):
                n=ep['part'];t=oldtypes[parts[n]['type']];lf,lwin,order=local_geom(parts[n],rect[n],wf,win)
                bus=next((b for b in t.get('buses',[]) if b['name']==ep['bus']),None)
                if bus is not None:bus.update(face=lf,window_um=lwin,layers=layers,order=order)
        for i,n in enumerate(path[1:-1],1):
            incoming,outgoing=edges[i-1],edges[i];fin=OPP[incoming['face']];fout=outgoing['face']
            if fin==fout:raise ValueError(f'SAME_FACE_TRANSIT {lid} {n} {fin}')
            lf,wi,order=local_geom(parts[n],rect[n],fin,incoming['window_um']);lo,wo,orderout=local_geom(parts[n],rect[n],fout,outgoing['window_um'])
            t=oldtypes[parts[n]['type']];w,h=t['outline_um']
            def point(face,win):
                v=sum(win)/2;return {'N':(v,h),'S':(v,0),'W':(0,v),'E':(w,v)}[face]
            aa,bb=point(lf,wi),point(lo,wo);distance=abs(aa[0]-bb[0])+abs(aa[1]-bb[1])
            count=max(1,math.ceil((distance+max(wi[1]-wi[0],wo[1]-wo[0]))/(405*.98)))
            slot=dict(name=names[n],in_face=lf,out_face=lo,width=width,stations=count,in_window_um=wi,out_window_um=wo,order=order)
            t['ft_slots'].append(slot);newslots[parts[n]['type']].append(slot['name'])
        ln['ports']=[p['id'] for p in edges];route_rows.append(dict(lane=lid,parts=path,width=width))
    raw['ports']=[p for p in raw['ports'] if p['id'] not in removed_ports]+newports
    if side.exists():
        for new,old in original.items():
            if old in conns:conns[new]=copy.deepcopy(conns[old])
        side.write_text(json.dumps(conns,indent=1)+'\n')
    # Candidate physical PHY windows and separate supply domains follow the
    # actual macro rectangles. Die outline and fourteen logical links stay fixed.
    mm={m['part']:m for m in proposal['macros']}
    for io in raw['die'].get('io',[]):
        n=io.get('part')
        if n in mm:
            m=mm[n];io['rect_um']=m['macro_um'];io['pitch_um']=45.;io['sites']=int((m['macro_um'][2]-m['macro_um'][0])//45)*int((m['macro_um'][3]-m['macro_um'][1])//45)
            io['note']='D-S81-PHY published central-size macro; same14links; micro-bump face45um; signal+dedicated PG site assignment remains to be finalized.'
        elif n=='phy_hbm' and n in proposal['changes']:
            dx=proposal['changes'][n]['after'][0]-proposal['changes'][n]['before'][0];io['rect_um']=[v+(dx if i in (0,2) else 0) for i,v in enumerate(io['rect_um'])]
    iod={io['name']:io for io in raw['die'].get('io',[])}
    for domain in raw['die'].get('pg',{}).get('domains',[]):
        io=iod.get((domain.get('io') or [None])[0]);n=io.get('part') if io else None
        if n in mm:
            r=io['rect_um'];domain['rect_um']=r;domain['phy_macro_um']=r;domain['phy_area_target_mm2']=3.36;domain['bumps']['rect_um']=r;domain['bumps']['pitch_um']=45.
            domain['core_strip_um']=[[rect[n][0],r[3] if mm[n]['side']=='S' else rect[n][1],rect[n][2],rect[n][3] if mm[n]['side']=='S' else r[1]]]
    kept_types={p['type'] for p in raw['partitions']}
    raw['partition_types']={name:t for name,t in raw['partition_types'].items() if name in kept_types}
    report=dict(used_types=len(kept_types),status='CONNECTED GEOMETRY PROTOTYPE: stations/per-bit placement and all gates pending',variants=variants,source_types=original,new_slots=dict(newslots),routes=route_rows,
        preserved_field_children=all(raw['partition_types'][variants[n]].get('hard_cores')==oldtypes[original[variants[n]]].get('hard_cores') for n in variants if n.startswith(('fW','fE'))),
        pending=['Allocate every new FT station bit off hard cores; regenerate full G0C/latency and price all changed cycles.', 'TX candidate view not signed; all new wrapper variants need actual trial placement.', 'Independent image review + shared infra-first PG/clock/reset precede die route.'])
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(raw,separators=(',',':'))+'\n');a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('status','preserved_field_children')},indent=2));print('variants',len(variants),'newFTslots',sum(map(len,newslots.values())))


if __name__=='__main__':main()
