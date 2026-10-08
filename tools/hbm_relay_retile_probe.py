#!/usr/bin/env python3
"""Actual-pin result relay prerequisite on a serialized candidate die.

No station RTL, hardened view or routing claim. All 270 result bits, including
valid, row and fault, retain their logical gather input. Planned successor SM
pins and retained routed gather LEF pins are mandatory inputs. Shared endpoint
boxes are reserved; intermediate paths are still independently probed.
"""
import argparse,hashlib,json,math,sys
from pathlib import Path
from types import SimpleNamespace
from hbm_die_relays import Free,lef_pins,to_die
from hbm_relay_channel_model import channel_path,spatial_slices
ROOT=Path(__file__).resolve().parents[1]

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def centre(b): return ((b[0]+b[2])/2,(b[1]+b[3])/2)

def clustered_slices(source, sink, source_box, sink_box):
    """Fill spatially adjacent groups; keep remote valid/fault pins separate.

    Every candidate still passes the existing two-endpoint reach check. This
    avoids recursive bisection creating tiny groups beside a remote outlier.
    Packing order puts the widest pin spread first, independent of bit order.
    """
    faces={}
    for i in range(len(source)):
        one=spatial_slices([source[i]],[sink[i]],source_box,sink_box)[0]
        faces.setdefault((one['source_face'],one['sink_face']),[]).append(i)
    groups=[]
    def candidate(indices):
        parts=spatial_slices([source[i] for i in indices],[sink[i] for i in indices],source_box,sink_box,max_bits=64)
        if len(parts)!=1:return None
        part=parts[0];part['bit_indices']=list(indices);return part
    for (sf,tf),ids in sorted(faces.items()):
        axis=1 if sf in 'WE' else 0
        ids.sort(key=lambda i:(source[i][axis],sink[i][1 if tf in 'WE' else 0],i))
        batch=[]
        for i in ids:
            if batch and (len(batch)==64 or candidate(batch+[i]) is None):
                groups.append(candidate(batch));batch=[]
            batch.append(i)
        if batch:groups.append(candidate(batch))
    return sorted(groups,key=lambda g:max(g['source_max_pin_distance_um'],g['sink_max_pin_distance_um']),reverse=True)

def reserve(group,pins,side,free):
    pts=[pins[i] for i in group['bit_indices']]
    face=group[side+'_face']; portal=group[side+'_portal_um']; axis=1 if face in 'WE' else 0
    sums=[x+y for x,y in pts];diffs=[x-y for x,y in pts]
    minsum,maxsum,mindiff,maxdiff=min(sums),max(sums),min(diffs),max(diffs)
    candidates=[]
    for along in range(-47,48):
        for away in range(-5,36):
            p=list(portal); p[axis]+=along*2.16; p[1-axis]+=away*2.16*(-1 if face in 'WS' else 1)
            b=[p[0]-10,p[1]-10,p[0]+10,p[1]+10]
            face_box=list(b)
            if face=='W':face_box[0]=face_box[2]
            elif face=='E':face_box[2]=face_box[0]
            elif face=='S':face_box[1]=face_box[3]
            else:face_box[3]=face_box[1]
            u0,v0,u1,v1=face_box
            reach=max(maxsum-u0-v0,u1+v1-minsum,maxdiff-u0+v1,u1-v0-mindiff)
            if reach<=100: candidates.append((reach,abs(along)+abs(away),b))
    for reach,_,b in sorted(candidates):
        # 12um endpoint escape aisle, including Free's 2.16um halo.
        padded=[b[0]-9.84,b[1]-9.84,b[2]+9.84,b[3]+9.84]
        if free.ok(padded):
            free.add(b)
            return dict(box_um=b,centre_um=centre(b),worst_pin_to_endpoint_facing_side_um=reach,
                assumed_endpoint_facing_pins='d' if side=='source' else 'q')
    raise ValueError('greedy endpoint search exhausted current reservations within 100um; alternate packing or floorplan needed')

def pack_face_batch(items, free):
    """Match all ports on one macro face jointly to a station grid.

    Four grid phases and three rows are constructive alternatives, not an
    exhaustive floorplan feasibility proof. All stations remain 20x20um with
    >=12um physical aisles. Matching can displace earlier assignments, unlike
    independent greedy reservations of t0 followed by t1.
    """
    face=items[0][1][items[0][3]+'_face'];axis=1 if face in 'WE' else 0
    portal=items[0][1][items[0][3]+'_portal_um'];sign=-1 if face in 'WS' else 1
    clouds=[[pins[i] for i in g['bit_indices']] for _,g,pins,side in items]
    amin=min(p[axis] for cloud in clouds for p in cloud)-100
    amax=max(p[axis] for cloud in clouds for p in cloud)+100
    for phase in (0.,8.1,16.2,24.3):
        slots=[]
        for row in range(3):
            offset=phase+(16.2 if row%2 else 0)
            for k in range(math.floor((amin-offset)/32.4),math.ceil((amax-offset)/32.4)+1):
                p=list(portal);p[axis]=k*32.4+offset;p[1-axis]+=sign*(22.84+32.4*row-25)
                b=[p[0]-10,p[1]-10,p[0]+10,p[1]+10]
                if free.ok([b[0]-9.84,b[1]-9.84,b[2]+9.84,b[3]+9.84]):slots.append(b)
        edges=[]
        for cloud in clouds:
            valid=[]
            for k,b in enumerate(slots):
                fb=list(b)
                if face=='W':fb[0]=fb[2]
                elif face=='E':fb[2]=fb[0]
                elif face=='S':fb[1]=fb[3]
                else:fb[3]=fb[1]
                reach=max(abs(x-u)+abs(y-v) for x,y in cloud for u,v in [(fb[0],fb[1]),(fb[2],fb[3])])
                if reach<=100:valid.append((reach,k))
            edges.append(sorted(valid))
        matched={}
        def assign(i,seen):
            for reach,k in edges[i]:
                if k in seen:continue
                seen.add(k)
                if k not in matched or assign(matched[k][0],seen):
                    matched[k]=(i,reach);return True
            return False
        if all(assign(i,set()) for i in sorted(range(len(items)),key=lambda i:len(edges[i]))):
            for k,(i,reach) in matched.items():
                rec,g,pins,side=items[i];b=slots[k];free.add(b)
                g[side+'_station']=dict(box_um=b,centre_um=centre(b),worst_pin_to_endpoint_facing_side_um=reach,
                    assumed_endpoint_facing_pins='d' if side=='source' else 'q',packing='joint-face-grid-matching',grid_phase_um=phase)
            return [slots[k] for k in matched]
    raise ValueError('joint face-grid matching exhausted four phases under current obstacles; not an infeasibility proof')

def cut_capacity(records, boxes, outline):
    """Necessary geometric cut check, not a router or sufficient capacity proof.

    Optimistically gives all M4/M6/M8 horizontal or M5/M7/M9 vertical
    tracks to these result wires. PDN, clock and other traffic are not deducted.
    Overflow even under this upper bound proves the probed corridors inadequate;
    passing does not admit the design. Pitch is the repository ASAP7 model.
    """
    output=[]
    for axis in (0,1):
        segs=[]
        for rec in records:
            for g in rec.get('groups',[]):
                for a,b in zip(g.get('path_um',[]),g.get('path_um',[])[1:]):
                    if a[axis]!=b[axis] and a[1-axis]==b[1-axis]:
                        lo,hi=sorted((a[axis],b[axis]))
                        segs.append((lo,hi,a[1-axis],len(g['bit_indices'])))
        cuts=sorted({v for s in segs for v in s[:2]}|{v for b in boxes for v in (b[axis],b[axis+2])})
        for lo,hi in zip(cuts,cuts[1:]):
            x=(lo+hi)/2
            active=[s for s in segs if s[0]<x<s[1]]
            if not active: continue
            occupied=sorted((b[1-axis],b[3-axis]) for b in boxes if b[axis]<x<b[axis+2])
            merged=[]
            for a,b in occupied:
                if merged and a<=merged[-1][1]:merged[-1][1]=max(b,merged[-1][1])
                else:merged.append([a,b])
            prev=0
            for a,b in merged+[[outline[1-axis],outline[1-axis]]]:
                demand=sum(s[3] for s in active if prev<=s[2]<=a)
                width=max(0,a-prev)
                if demand:
                    cap=sum(math.ceil(width/p)+1 for p in (.048,.064,.080))
                    output.append(dict(axis='xy'[axis],cut_um=x,corridor_um=[prev,a],
                         demand_tracks=demand,optimistic_track_upper_bound=cap,
                         upper_bound_overflow=demand>cap,utilization_of_upper_bound=demand/cap))
                prev=max(prev,b)
    return dict(scope='result-leaf wires only; optimistic necessary cut bound, not admission',
      track_pitch_um=[.048,.064,.080],layer_sets=['M4/M6/M8 horizontal','M5/M7/M9 vertical'],
      pitch_source='tools/qwen_rom_floorplan_nearhbm_r2.py PITCH_UM',
      evaluated_cuts=len(output),overflow_cuts=sum(r['upper_bound_overflow'] for r in output),
      worst_cuts=sorted(output,key=lambda r:r['utilization_of_upper_bound'],reverse=True)[:20])

def run(placement, out):
    data=json.loads(placement.read_text())
    if 'outline' not in data:data['outline']=[data['geo']['W'],data['geo']['H']]
    by={i['name']:i for i in data['insts']}
    boxes=[i.get('box',[i['x'],i['y'],i['x']+i['w'],i['y']+i['h']]) for i in data['insts']]
    free=Free(boxes,*data['outline']); records=[]; reservations=[]; batches={}
    pins_path=ROOT/'results/uarch/hbm_relay_endpoint_pack_20261007/sm_successor_planned_pins.json'
    srcpins={p['pin']:p['xy'] for p in json.loads(pins_path.read_text())['pins']}
    names=['rv']+[f'rrow[{i}]' for i in range(12)]+[f'rdata[{i}]' for i in range(256)]+['fault']
    hashes={str(placement):sha(placement),str(pins_path.relative_to(ROOT)):sha(pins_path)}
    for p in [Path(__file__),ROOT/'tools/hbm_die_relays.py',ROOT/'tools/hbm_relay_channel_model.py',ROOT/'tools/qwen_rom_floorplan_nearhbm_r2.py']:
        hashes[str(p.relative_to(ROOT))]=sha(p)
    for name,cls,width,ends in data['buses']:
        if cls!='result_leaf': continue
        rec=dict(bus=name,width=width,ends=ends);records.append(rec)
        try:
            if width!=270 or len(ends)!=2: raise ValueError('result leaf must retain full 270-bit two-ended contract')
            sn,sp=next(e for e in ends if by[e[0]]['master']=='hfd_sm')
            tn,tp=next(e for e in ends if e[0]!=sn); s,t=by[sn],by[tn]
            if any(i['orient'] not in ('R0','MX','MY','R180') for i in (s,t)):raise ValueError('unsupported macro orientation')
            if sp!='r' or tp not in ('t0','t1'): raise ValueError('unexpected logical port association')
            if [s['w'],s['h']]!=[3075.84,1131.84]: raise ValueError('SM box must match exact successor master dimensions')
            p=ROOT/f"physical/hbm_accel_die_views/stations/{t['master']}/{t['master']}.lef"
            hashes[str(p.relative_to(ROOT))]=sha(p)
            w,h,pp=lef_pins(p.read_text())[t['master']]
            if abs(w-t['w'])>1e-6 or abs(h-t['h'])>1e-6: raise ValueError('gather box dimensions mismatch real LEF')
            source=[to_die(SimpleNamespace(**s),*srcpins[n],s['w'],s['h']) for n in names]
            sink=[to_die(SimpleNamespace(**t),*pp[f'{tp}[{i}]'][0],w,h) for i in range(270)]
            sb=[s['x'],s['y'],s['x']+s['w'],s['y']+s['h']];tb=[t['x'],t['y'],t['x']+t['w'],t['y']+t['h']]
            groups=clustered_slices(source,sink,sb,tb);rec['groups']=groups
            for g in groups:
                for side,pins,inst in [('source',source,sn),('sink',sink,tn)]:
                    batches.setdefault((inst,g[side+'_face']),[]).append((rec,g,pins,side))
        except (ValueError,KeyError,FileNotFoundError,StopIteration) as e:
            rec['failure']=str(e)
    for key,items in sorted(batches.items(),key=lambda kv:(not kv[0][0].startswith('sm'),kv[0])):
        try:reservations.extend(pack_face_batch(items,free))
        except ValueError as e:
            for rec,g,pins,side in items:
                rec.setdefault('packing_failures',[]).append(dict(instance=key[0],face=key[1],side=side,reason=str(e)))
                rec['failure']=str(e)
    cluster_boxes=[];cluster_by_key={}
    for key,items in batches.items():
        bb=[g[side+'_station']['box_um'] for rec,g,pins,side in items if side+'_station' in g]
        if bb:
            cb=[min(b[0] for b in bb),min(b[1] for b in bb),max(b[2] for b in bb),max(b[3] for b in bb)]
            cluster_boxes.append(cb);cluster_by_key[key]=cb
    # Force each bundle outward before global transit; other endpoint arrays
    # are opaque to transit, so a shortest path cannot steal their local aisles.
    # All endpoint boxes have been reserved before any corridor path is probed.
    for rec in records:
        if 'failure' in rec: continue
        for g in rec['groups']:
            a=g['source_station'];b=g['sink_station']
            wire_clearance=2.16+len(g['bit_indices'])*.080/2
            macro_extra=max(0,12.16-wire_clearance)
            obstacles=[[q[0]-macro_extra,q[1]-macro_extra,q[2]+macro_extra,q[3]+macro_extra] for q in boxes]
            obstacles += [q for q in reservations if q!=a['box_um'] and q!=b['box_um']]
            try:
                options=[]
                transit_obstacles=obstacles[:len(boxes)]+cluster_boxes
                for side,station,inst in [('source',a,rec['ends'][0][0]),('sink',b,rec['ends'][1][0])]:
                    cb=cluster_by_key[(inst,g[side+'_face'])];pad=wire_clearance+2.16
                    x0,y0,x1,y1=cb[0]-pad,cb[1]-pad,cb[2]+pad,cb[3]+pad
                    x,y=station['centre_um']
                    candidates=[(x0,y),(x1,y),(x,y0),(x,y1),(x0,y0),(x0,y1),(x1,y0),(x1,y1)]
                    valid=[]
                    for escape in candidates:
                        try:
                            channel_path(escape,escape,transit_obstacles,data['outline'],wire_clearance)
                            leg=channel_path(station['centre_um'],escape,obstacles,data['outline'],wire_clearance)
                        except ValueError:continue
                        length=sum(abs(u[0]-v[0])+abs(u[1]-v[1]) for u,v in zip(leg,leg[1:]))
                        valid.append((length,escape,leg))
                    if not valid:raise ValueError('no legal endpoint-cluster escape along any exposed face')
                    options.append(valid)
                pairs=sorted((u[0]+v[0]+abs(u[1][0]-v[1][0])+abs(u[1][1]-v[1][1]),i,j)
                    for i,u in enumerate(options[0]) for j,v in enumerate(options[1]))
                for _,i,j in pairs:
                    u,v=options[0][i],options[1][j]
                    try:middle=channel_path(u[1],v[1],transit_obstacles,data['outline'],wire_clearance)
                    except ValueError:continue
                    path=u[2]+middle[1:]+list(reversed(v[2]))[1:]
                    g['endpoint_cluster_escape_um']=[u[1],v[1]]
                    break
                else:raise ValueError('no global route between legal endpoint-cluster escapes')
                lengths=[abs(x[0]-y[0])+abs(x[1]-y[1]) for x,y in zip(path,path[1:])]
                g.update(path_um=path,route_length_um=sum(lengths),required_tracks=len(g['bit_indices']),
                    assumed_wire_bundle_width_um=len(g['bit_indices'])*.080,wire_centre_clearance_um=wire_clearance,
                    candidate_station_count=1+sum(math.ceil(l/300) for l in lengths))
            except ValueError as e:g['failure']=str(e)
        if all('path_um' in g for g in rec['groups']):
            rec['latency_cycles']=max(g['candidate_station_count'] for g in rec['groups'])
            rec['balanced_register_bits']=270*rec['latency_cycles']
            for g in rec['groups']:g['balance_cycles']=rec['latency_cycles']-g['candidate_station_count']
    result=dict(schema='opentallas.hbm_retile_result_relay_probe.v1',status='candidate-not-hardware-or-global-routing-qualified',
        selected=False,source_sha256=hashes,outline_um=data['outline'],result_leaves=records,
        endpoint_boxes=reservations,assumed_endpoint_shape_um=[20,20],endpoint_gap_um=12,endpoint_area_um2=len(reservations)*400,
        wire_pitch_upper_um=.080,wire_edge_clearance_um=2.16,
        endpoint_pin_assumption='source d and sink q pins lie on the 20um station face nearest the endpoint; actual hardened pin match required',
        required_bits_per_cycle=sum(r['width'] for r in records),
        required_gates=['32 result leaves present with unchanged logical gather association',
          'real station RTL and dimensions/pins; exact fixed-stream valid,row,data,fault alignment',
          'shared intermediate station and balance-register placement',
          'simultaneous physical channel track capacity including x/control/weight traffic, clock and PDN',
          'original gather stream joins balanced against complete tree timing and composed token traversals',
          'routed SS/FF >=15ps, DRC0, final SM planned pins match routed LEF'])
    if len(records)==32 and all('latency_cycles' in r for r in records):
        latency=max(r['latency_cycles'] for r in records)
        result['candidate_all_result_leaves_balanced_cycles']=latency
        result['candidate_balanced_result_register_bits']=32*270*latency
        result['balancing_scope']='proposed result-leaf entrance alignment only; real gather, command/control and downstream timing not established'
        for r in records:r['additional_leaf_balance_cycles']=latency-r['latency_cycles']
    result['optimistic_cut_capacity']=cut_capacity(records,boxes+reservations,data['outline'])
    if len(records)!=32:result['incomplete_result_leaf_inventory']=len(records)
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(leaves=len(records),endpoint_boxes=len(reservations),leaf_failures=sum('failure' in r for r in records),
       path_failures=sum('failure' in g for r in records for g in r.get('groups',[])),routed_leaf_probes=sum('latency_cycles' in r for r in records),out=str(out))))

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--placement',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();run(a.placement,a.out)
