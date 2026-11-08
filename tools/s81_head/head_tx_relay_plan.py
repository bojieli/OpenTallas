#!/usr/bin/env python3
"""DRAFT, NOT FOR KIT APPLICATION: plan +1 TX relay targets from actual PLACE.

Known next task: status flops in the reference are named u_enc.p_v and
u_enc.fault (public-port aliases), not g_ch_out.pv_mid/fault_mid. Resolve
those aliases and complete the apply helper before any new P&R. No pilot
was launched from this draft. Earlier relay_plan.json/PNG remains a plan
snapshot, not a new mapped result.

Inputs: relay_seeds.json and placed.csv from the source-pinned read-only probes.
Produces registered-hop targets and a mapped-area ownership budget. Coordinates
are planned; a new PLACE must measure them again, including actual buffer hops.
"""
import argparse,csv,json,math,re,collections
from pathlib import Path
SITE=.054;ROW=.27;WIDTH=1.08

def plan(seeds,placed):
    ref=json.loads(Path(seeds).read_text());old={}
    for d in csv.DictReader(open(placed)):
        if 'DFF' in d['master']:
            n=d['name'].replace('\\','').split('$')[0]
            old[n]=[float(d[k]) for k in ('x','y','w','h')]
    occupied=collections.defaultdict(set);targets={};groups=[];tile_area=collections.defaultdict(float)
    def tiles(x,y):
        result={}
        for iy in range(int(y//5),int((y+ROW)//5)+1):
            for ix in range(int(x//5),int((x+WIDTH)//5)+1):
                result[ix,iy]=max(0,min(x+WIDTH,(ix+1)*5)-max(x,ix*5))*max(0,min(y+ROW,(iy+1)*5)-max(y,iy*5))
        return result
    def alloc(n,x,y,kind):
        sx=round((x-4.32)/SITE);sy=round((y-4.32)/ROW)
        for radius in range(25):
            for dy in range(-radius,radius+1):
                dx=radius-abs(dy)
                for sign in ((1,-1) if dx else (1,)):
                    xx=sx+sign*dx*5;yy=sy+dy
                    if xx<0 or yy<0 or xx*SITE+4.32+WIDTH>481.68 or yy*ROW+4.32+ROW>116.64:continue
                    slots=set(range(xx,xx+20))
                    if occupied[yy]&slots:continue
                    p=[round(4.32+xx*SITE,6),round(4.32+yy*ROW,6)]
                    contributions=tiles(*p)
                    cap=.34 if kind=='relay' else (.40 if kind=='bridge' else None)
                    if cap and any(tile_area[t]+a>25*cap for t,a in contributions.items()):continue
                    occupied[yy].update(slots)
                    for t,a in contributions.items():tile_area[t]+=a
                    targets[n]=dict(x=p[0],y=p[1],kind=kind)
                    return [p[0]+WIDTH/2,p[1]+ROW/2]
        raise RuntimeError('no local legal site for '+n)
    # Actual input/output face positions survive the form change.
    for n,p in old.items():
        if re.match(r'^u_enc.d0\[|^u_ptx.l\[2\]',n):alloc(n,p[0],p[1],'face')
    for bit in range(512):
        for stage in range(1,9):
            alloc(f'u_enc.d{stage}[{bit}]',238.68+.288*bit,8+.675*(4*(stage-1)+(bit%4)),'data')
    for bit in range(544):
        for name,stage in ((f'u_enc.p_d[{bit}]',8),(f'u_ptx.l[0][{bit}]',9),(f'u_ptx.l[1][{bit}]',10)):
            rank=stage if bit<512 else stage-5
            alloc(name,238.68+.288*bit,8+.675*(4*rank+(bit%4)),'data')
    for r in range(4):
        for bit in range(520):
            x=32+100*r+1.15*(bit%65);y=66+6*(bit//65)
            alloc(f'u_enc.g_ch_region.mid[{r}][{bit}]',x,y,'mid')
            alloc(f'u_enc.g_ff.cq[{r}][{bit}]',x,y+.54,'cq')
        # Never put opposite ends of a 65-bit row in one atomic group.
        for row in range(8):
            for start in range(0,65,8):
                groups.append([f'u_enc.{root}[{r}][{row*65+bit}]' for bit in range(start,min(65,start+8)) for root in ('g_ch_region.mid','g_ff.cq')])
    for nr in range(17):
        for bit in range(10):
            for root,stage in (('sw',0),('g_ch_out.sw_mid',1),('g_ch_out.sw_relay',2)):
                alloc(f'u_enc.{root}[{nr}][{bit}]',238.68+.288*(nr*32+15.5)+1.15*((bit%5)-2),46+3*(bit//5)+.54*stage,'select')
        for start in range(0,10,4):
            groups.append([f'u_enc.{root}[{nr}][{bit}]' for bit in range(start,min(10,start+4)) for root in ('sw','g_ch_out.sw_mid','g_ch_out.sw_relay')])
    # New zero-logic control stages get explicit local clock groups too.
    for r in range(4):
        rem=[p for n,p in old.items() if re.match(r'^u_enc.rem_q\[([0-9]+)\]',n) and r*75<=int(re.search(r'\[([0-9]+)\]',n)[1])<(r+1)*75]
        if not rem:raise RuntimeError('no reference rem quarter '+str(r))
        cx=sum(p[0]+p[2]/2 for p in rem)/len(rem);cy=sum(p[1]+p[3]/2 for p in rem)/len(rem)
        ns=[]
        for field,col in (('f0',0),('fv',1)):
            for root,row in ((f'g_la2.g_ch_flags.{field}_mid',0),(f'g_la2.g_ch_flags.{field}_relay',1),(f'g_la2.{"f0v" if field=="f0" else "fv"}',2)):
                n=f'u_enc.{root}[{r}]';alloc(n,cx+1.15*col,cy+.54*row,'flags');ns.append(n)
        groups.append(ns)
    for bit in range(8):
        name=f'u_enc.h0s_out_mid[{bit}]';p=old[name]
        alloc(name,p[0],p[1],'header');nr=f'u_enc.h0s_out_relay[{bit}]';alloc(nr,p[0],p[1]+.54,'header');groups.append([name,nr])
    for oldroot,newroot in (('pv_mid','pv_relay'),('fault_mid','fault_relay')):
        n=f'u_enc.g_ch_out.{oldroot}';p=old[n]
        # The new fault register inherits the old output face site.
        nr=f'u_enc.g_ch_out.{newroot}'
        alloc(nr,p[0],p[1],'status');alloc(n,p[0],p[1]+.54,'status');groups.append([n,nr])
    relay_hops=[]
    for r in range(4):
        for bit in range(520):
            source=ref['seeds'][f'{r},{bit}']['source']
            dest=targets[f'u_enc.g_ch_region.mid[{r}][{bit}]'];d=[dest['x']+WIDTH/2,dest['y']+ROW/2]
            q=alloc(f'u_enc.g_ch_relay.q[{r}][{bit}]',(source[0]+d[0])/2-WIDTH/2,(source[1]+d[1])/2-ROW/2,'relay')
            relay_hops.extend([abs(source[0]-q[0])+abs(source[1]-q[1]),abs(d[0]-q[0])+abs(d[1]-q[1])])
    bridge_hops=[]
    for bit in range(512):
        p=targets[f'u_enc.d0[{bit}]'];a=[p['x']+WIDTH/2,p['y']+ROW/2]
        p=targets[f'u_enc.d1[{bit}]'];d=[p['x']+WIDTH/2,p['y']+ROW/2]
        q=alloc(f'u_enc.d_bridge[{bit}]',(a[0]+d[0])/2-WIDTH/2,(a[1]+d[1])/2-ROW/2,'bridge')
        bridge_hops.extend([abs(a[0]-q[0])+abs(a[1]-q[1]),abs(d[0]-q[0])+abs(d[1]-q[1])])
    for start in range(0,512,8):
        groups.append([f'u_enc.d0[{b}]' for b in range(start,start+8)])
        groups.append([f'u_enc.d_bridge[{b}]' for b in range(start,start+8)])
    for bit in range(512):
        groups.append([f'u_enc.d{s}[{bit}]' for s in range(1,9)]+[f'u_enc.p_d[{bit}]']+[f'u_ptx.l[{s}][{bit}]' for s in range(3)])
    for start in range(512,544,4):groups.append([n for bit in range(start,start+4) for n in [f'u_enc.p_d[{bit}]']+[f'u_ptx.l[{s}][{bit}]' for s in range(3)]])
    buckets=collections.defaultdict(list)
    for n,p in targets.items():
        if p['kind']=='relay':buckets[int(p['x']//12),int(p['y']//12)].append(n)
    for ns in buckets.values():
        for j in range(0,len(ns),16):groups.append(ns[j:j+16])
    # Check actual proposed group centroids, including face-flop outliers.
    safe=[]
    def radius(ns):
        xs=[targets[n]['x']+WIDTH/2 for n in ns];ys=[targets[n]['y']+ROW/2 for n in ns]
        cx=sum(xs)/len(xs);cy=sum(ys)/len(ys)
        return max(abs(x-cx)+abs(y-cy) for x,y in zip(xs,ys))
    def split(ns):
        if len(ns)<=16 and radius(ns)<=20:safe.append(ns);return
        spread=[max(targets[n][axis] for n in ns)-min(targets[n][axis] for n in ns) for axis in ('x','y')]
        axis='x' if spread[0]>=spread[1] else 'y';ns=sorted(ns,key=lambda n:targets[n][axis]);k=len(ns)//2
        split(ns[:k]);split(ns[k:])
    for ns in groups:split(ns)
    groups=safe
    stars=collections.defaultdict(list)
    for key,seed in ref['seeds'].items():
        rr,bb=key.split(',');p=targets[f'u_enc.g_ch_relay.q[{rr}][{bb}]']
        stars[seed['driver']].extend([seed['source'],[p['x']+WIDTH/2,p['y']+ROW/2]])
    star_hpwl=max(max(p[0] for p in pts)-min(p[0] for p in pts)+max(p[1] for p in pts)-min(p[1] for p in pts) for pts in stars.values())
    # Include final output face flops and conservative reserves, not just data DFFs.
    areas=dict(internal_data_registers=ref['data_internal_register_area_um2'],final_pma_face_registers=544*.2916,mapped_comb_buffers=ref['data_comb_buffer_area_um2'],new_data_bridge=512*.2916,all_chunk_relays_charged_to_data_box=2080*.2916,word_header_control_reserve=200,extra_signal_buffer_reserve=.25*ref['data_comb_buffer_area_um2'],clock_cell_reserve=200)
    box=[220,4.32,414,59];capacity=(box[2]-box[0])*(box[3]-box[1]);total=sum(areas.values())
    return dict(schema='opentallas.tx_registered_relay_plan.v1',source_place=ref['base_odb'],pin_cycles_added=1,default_off=True,targets=targets,atomic_groups=groups,register_target_count=len(targets),max_registered_5um_density=round(max(tile_area.values())/25,4),atomic_group_count=len(groups),max_atomic_centroid_l1_radius_um=round(max(radius(ns) for ns in groups),3),max_source_to_chunk_relay_star_hpwl_um=round(star_hpwl,3),max_planned_chunk_relay_hop_um=round(max(relay_hops),3),max_planned_data_bridge_hop_um=round(max(bridge_hops),3),signal_buffer_segment_budget_um=80,ownership=dict(data_box_um=box,area_um2=round(capacity,3),owned_area_budget_um2=round(total,3),utilization_budget=round(total/capacity,4),mapped_area_components_um2=areas,remaining_region_um=[4.32,60,481.68,116.64]),warning='Source points come from the prior mapped PLACE; the new PLACE must measure actual driver hops and density. No timing/signoff claim.')

if __name__=='__main__':
    raise SystemExit('DRAFT: resolve p_v/fault reference aliases and complete kit apply helper before use')
    p=argparse.ArgumentParser();p.add_argument('seeds');p.add_argument('placed');p.add_argument('out');a=p.parse_args();r=plan(a.seeds,a.placed);Path(a.out).write_text(json.dumps(r,indent=1)+'\n');print({k:v for k,v in r.items() if k not in ('targets','atomic_groups')})
