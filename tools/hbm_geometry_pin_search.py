#!/usr/bin/env python3
"""Conservative actual-pin local translation search; external data pins stay fixed.

Flips require separate symmetry/PG evidence and are deliberately not inferred.
Objective covers every internal point-to-point signal bit, not a selected path.
Outputs candidates only: no timing, clock, congestion or native qualification.
"""
import argparse, hashlib, json
from pathlib import Path

def build(m):
    cs={c['instance']:c for c in m['children']};pairs=[];anchors=set();clock_ports={'clk','ck','rst_n','rst','reset','reset_n'}
    for binding in m.get('boundary_binding',[]):
        port=binding['parent_port']
        if port not in clock_ports and m.get('boundary_ports',{}).get(port,{}).get('role')!='clock':
            anchors.add(binding['child_instance'])
    def shapes(e,k):
        p=cs[e['instance']]['pins'];key=f"{e['port']}[{e['lsb']+k}]";key=key if key in p else e['port']
        if key not in p:raise ValueError('missing pin '+str(e))
        return [((s['rect_um'][0]+s['rect_um'][2])/2,(s['rect_um'][1]+s['rect_um'][3])/2) for s in p[key]['shapes']]
    for c in m['connections']:
        if c['kind']!='signal':continue
        es=[e for e in c['endpoints'] if e['port'] not in clock_ports]
        drivers=[e for e in es if e['direction']=='output'];loads=[e for e in es if e['direction']=='input']
        if not drivers or not loads:
            anchors.update(e['instance'] for e in es);continue
        if len(drivers)!=1:raise ValueError('multiple driver '+c['net'])
        a=drivers[0]
        for b in loads:
            if a['width']!=b['width']:raise ValueError('width mismatch')
            for k in range(b['width']):pairs.append((a['instance'],b['instance'],shapes(a,k),shapes(b,k),c['net'],k))
    return cs,pairs,anchors

def distances(pairs,shift):
    for a,b,ap,bp,net,k in pairs:
        ax,ay=shift[a];bx,by=shift[b]
        yield min(abs(x+ax-u-bx)+abs(y+ay-v-by) for x,y in ap for u,v in bp)

def clearance(a,b,shift):
    ax,ay=a['xy_um'];dx,dy=shift[a['instance']];ax+=dx;ay+=dy;aw,ah=a['outline_um']
    bx,by=b['xy_um'];dx,dy=shift[b['instance']];bx+=dx;by+=dy;bw,bh=b['outline_um']
    return max(max(ax-bx-bw,bx-ax-aw),max(ay-by-bh,by-ay-ah))

def search(m,passes=4):
    cs,pairs,anchors=build(m);shift={n:[0.,0.] for n in cs};initial=list(distances(pairs,shift));reach=max(initial)
    halo={(a,b):min(5.4,clearance(cs[a],cs[b],shift)) for a in cs for b in cs if a<b}
    adjacent={n:[p for p in pairs if n in p[:2]] for n in cs};W,H=m['outline_um'];moves=[]
    def legal(n):
        c=cs[n];dx,dy=shift[n];x,y=c['xy_um'];w,h=c['outline_um']
        if min(x+dx,y+dy)<-1e-6 or x+dx+w>W+1e-6 or y+dy+h>H+1e-6:return False
        for b in cs:
            if b==n:continue
            if clearance(c,cs[b],shift)<halo[tuple(sorted([n,b]))]-1e-6:return False
        return True
    for sweep in range(passes):
        changed=False
        for n in sorted(cs):
            if n in anchors:continue
            old=shift[n][:];before=sum(distances(adjacent[n],shift));best=(before,old)
            for dx,dy in [(21.6,0),(-21.6,0),(0,21.6),(0,-21.6),(4.32,0),(-4.32,0),(0,4.32),(0,-4.32)]:
                candidate=[round(old[0]+dx,6),round(old[1]+dy,6)]
                if max(abs(x) for x in candidate)>43.2:continue
                shift[n]=candidate
                if not legal(n):continue
                ds=list(distances(adjacent[n],shift));total=sum(ds)
                if ds and max(ds)<=reach+1e-6 and total<best[0]-1e-6:best=(total,candidate)
            shift[n]=best[1]
            if best[1]!=old:moves.append(dict(instance=n,from_delta_um=old,to_delta_um=best[1],all_incident_bits_saving_um=before-best[0]));changed=True
        if not changed:break
    final=list(distances(pairs,shift));group={}
    for p,old,new in zip(pairs,initial,final):
        a,b,_,_,net,_=p;key=(net,a,b);g=group.setdefault(key,dict(net=net,source=a,sink=b,bits=0,before_bit_um=0.,after_bit_um=0.,before_max_um=0.,after_max_um=0.));g['bits']+=1;g['before_bit_um']+=old;g['after_bit_um']+=new;g['before_max_um']=max(g['before_max_um'],old);g['after_max_um']=max(g['after_max_um'],new)
    return dict(schema='opentallas.hbm_geometry.actual_pin_search.v1',component=m['component'],component_sha256=m['component_sha256'],native_qualified=False,geometry_candidate_only=True,objective='sum Manhattan distance over all internal non-clock/reset actual LEF pin-shape pairs',actual_bit_pairs=len(pairs),external_data_anchored_children=sorted(anchors),before=dict(total_bit_um=sum(initial),max_pin_manhattan_um=max(initial)),after=dict(total_bit_um=sum(final),max_pin_manhattan_um=max(final)),placement_deltas_um={n:d for n,d in shift.items() if d!=[0.,0.]},moves=moves,top20_before=sorted(group.values(),key=lambda g:g['before_bit_um'],reverse=True)[:20],top20_after=sorted(group.values(),key=lambda g:g['after_bit_um'],reverse=True)[:20],limits=['Clock/reset ports are excluded from the data objective. All external data endpoint children fixed; clock/reset pin positions move with children, clock-route proof outstanding.','No flips without actual LEF symmetry and PG legality evidence.','Existing pair clearance retained up to 5.4um; no halo is reduced by search.','No routed congestion, clock, timing, source-native or throughput claim.','Bounded local translation search, not proof of global optimum.','Whole-die service, SM, VM, SU and other omitted links are outside this component objective.'])

def main():
    p=argparse.ArgumentParser();p.add_argument('manifest');p.add_argument('--out',required=True);p.add_argument('--passes',type=int,default=4);a=p.parse_args();raw=Path(a.manifest).read_bytes();m=json.loads(raw);r=search(m,a.passes);r['manifest_sha256']=hashlib.sha256(raw).hexdigest();Path(a.out).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:r[k] for k in ['actual_bit_pairs','before','after','placement_deltas_um']}))
if __name__=='__main__':main()
