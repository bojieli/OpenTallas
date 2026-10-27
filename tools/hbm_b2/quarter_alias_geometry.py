#!/usr/bin/env python3
"""Diagnose bare-mapped aliases against an existing source/RF subset allocation."""
import argparse,collections,json,math,statistics
from pathlib import Path
import quarter_ff_bays as q

def diagnose(layout,outputs,control,aliases,allocation,rf,extra):
    q.W=allocation['cell_um'][0];q.H=allocation['cell_um'][1]
    nodes,fixed,edges,obstacles=q.load_problem(layout,outputs,control)
    positions=fixed|{n:tuple(p)for n,p in allocation['placements'].items()}|{n:tuple(p)for n,p in rf.items()if n in nodes}
    name2cell={n:a['cell']for n,a in aliases.items()if a.get('cell')and n in nodes}
    groups=collections.defaultdict(list)
    for n,c in name2cell.items():groups[c].append(n)
    merged={c:ns for c,ns in groups.items()if len(ns)>1}
    affected={n for ns in merged.values()for n in ns}
    if any(s in affected and t in affected for s,t,k in edges):raise ValueError('coupled merged aliases require joint solver')
    obstacles += [dict(name=x['name'],kind='RF',rect=x['rect'])for x in extra]
    blocked={tuple(s)for b in allocation['bays']for s in b['sites']}
    for n in affected:
        x,y=positions[n];blocked.discard((round(x/q.W-.5),round(y/q.H-.5)))
    adjacent=collections.defaultdict(set)
    for s,t,k in edges:adjacent[s].add(t);adjacent[t].add(s)
    chosen={};fail=[];receipts=[]
    def legal(ix,iy):
        if(ix,iy)in blocked:return False
        x,y=(ix+.5)*q.W,(iy+.5)*q.H;rect=(x-q.W/2,y-q.H/2,x+q.W/2,y+q.H/2)
        if rect[0]<0 or rect[1]<0 or rect[2]>1816.992 or rect[3]>2347.488:return False
        return not any(rect[0]<z[2]-1e-8 and rect[2]>z[0]+1e-8 and rect[1]<z[3]-1e-8 and rect[3]>z[1]+1e-8 for z in(o['rect']for o in obstacles))
    for cell,ns in sorted(merged.items()):
        neighbors=sorted({t for n in ns for t in adjacent[n]})
        pts=[positions[t]for t in neighbors]
        lu=max((x+y-q.REACH for x,y in pts),default=0);uu=min((x+y+q.REACH for x,y in pts),default=4164.48)
        lv=max((x-y-q.REACH for x,y in pts),default=-2347.488);uv=min((x-y+q.REACH for x,y in pts),default=1816.992)
        ox=statistics.median(positions[n][0]for n in ns);oy=statistics.median(positions[n][1]for n in ns)
        receipt=dict(cell=cell,logical_ids=ns,neighbors=len(neighbors),uv_bounds=[lu,uu,lv,uv],original_points=[positions[n]for n in ns])
        if lu>uu+1e-7 or lv>uv+1e-7:
            receipt['reason']='EMPTY_EXACT_405_DIAMOND_INTERSECTION';fail.append(receipt);continue
        ymin=max(0,(lu-uv)/2);ymax=min(2347.488,(uu-lv)/2);pool=[]
        for iy in range(max(0,math.ceil(ymin/q.H-.5)),math.floor(ymax/q.H-.5)+1):
            y=(iy+.5)*q.H;xlo=max(lu-y,lv+y,0);xhi=min(uu-y,uv+y,1816.992)
            lo=math.ceil(xlo/q.W-.5);hi=math.floor(xhi/q.W-.5)
            if lo>hi:continue
            # Scan nearest sites first; all sites remain eligible if reservations block them.
            for ix in sorted(range(lo,hi+1),key=lambda i:abs((i+.5)*q.W-ox)):
                x=(ix+.5)*q.W;pool.append((abs(x-ox)+abs(y-oy),ix,iy))
        found=None
        for _,ix,iy in sorted(pool):
            if legal(ix,iy):found=(ix,iy);break
        if found is None:receipt['reason']='NO_LEGAL_UNRESERVED_ROW_SITE';fail.append(receipt);continue
        ix,iy=found;chosen[cell]=((ix+.5)*q.W,(iy+.5)*q.H);blocked.add(found)
        # One spare cell makes this newly merged one-FF bay 50% full.
        spare=None
        for radius in range(1,185):
            for sx,sy in[(ix+radius,iy),(ix-radius,iy),(ix,iy+radius),(ix,iy-radius)]:
                if legal(sx,sy):spare=(sx,sy);break
            if spare:break
        if spare is None:receipt['reason']='NO_60PCT_SPARE';fail.append(receipt);continue
        blocked.add(spare);receipt.update(point_um=chosen[cell],spare_site=spare,max_hop_um=max((q.distance(chosen[cell],p)for p in pts),default=0));receipts.append(receipt)
    canonical={}
    for n,p in positions.items():
        c=name2cell.get(n,n)
        if c not in merged:canonical[c]=p
    canonical.update(chosen);bad=[];missing=[];unique=set();worst=(0,None)
    for s,t,k in edges:
        s,t=name2cell.get(s,s),name2cell.get(t,t)
        if s==t:continue
        if(s,t,k)in unique:continue
        unique.add((s,t,k))
        if s not in canonical or t not in canonical:missing.append((s,t,k));continue
        d=q.distance(canonical[s],canonical[t])
        if d>worst[0]:worst=(d,(s,t,k))
        if d>q.REACH+1e-6:bad.append(dict(source=s,target=t,kind=k,length_um=d))
    return dict(schema='opentallas.quarter_bare_alias_geometry.v1',verdict='PASS_BARE_ALIAS_SUBSET'if not(fail or bad or missing)else'FAIL',merged_groups=len(merged),multipoint_groups=sum(len({tuple(nodes[n])for n in ns})>1 for ns in merged.values()),eliminated_duplicate_FF=sum(len(ns)-1 for ns in merged.values()),resolved_alias_IDs=len(name2cell),unresolved_non_md_IDs=[n for n,a in aliases.items()if a['kind']=='UNRESOLVED'and'.md.'not in n],placed_merges=receipts,failures=fail,unique_edges=len(unique),missing_edges=len(missing),reach_failures=bad,max_actual_hop_um=worst[0],worst_edge=worst[1],qualification='Bare mapped control aliases only. Full ordinary-keep-enabled synth supersedes this graph; unresolved source IDs and output FF aliases remain unqualified. All existing FF/RF/blank reservations preserved except freed duplicate cells; each merged FF receives one spare site.')

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for n in['layout','outputs','control','aliases','allocation','rf','obstacles','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();read=lambda n:json.loads(getattr(a,n).read_text())
 r=diagnose(read('layout'),read('outputs'),read('control'),read('aliases'),read('allocation'),read('rf'),read('obstacles'));a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=1)+'\n');print(json.dumps({k:v for k,v in r.items()if k not in['placed_merges','unresolved_non_md_IDs','reach_failures','failures']}));print('failure samples',r['failures'][:2]);return int(r['verdict']=='FAIL')
if __name__=='__main__':raise SystemExit(main())
