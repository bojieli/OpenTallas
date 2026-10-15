#!/usr/bin/env python3
"""2-D pre-route wire-area screen using actual case pin centroids.

This is analytical demand, NEVER routed congestion. Both Manhattan L choices
are screened independently; neither is a router prediction. A window's demand
is sum(bits * wire length in window); its capacity is usable track-length
(area / pitch, with published PDN derates). The VM envelope blocks ALL layers.
Optional --grt maps actual OpenROAD violation bboxes onto the same windows.
"""
import argparse, collections, hashlib, json, math, re
from pathlib import Path
from bind_real import macros, pins
import os
VM=(13284.,17051.04,18122.4,19597.68)
if os.environ.get('OT_WINDOW_VM'):   # split compute die: the trimmed VM rectangle (conservatively still a full blockage)
    VM=tuple(float(q) for q in os.environ['OT_WINDOW_VM'].split(','))
PITCH={'H':[(.048,.5),(.064,.75),(.080,.75)],
       'V':[(.048,.5),(.064,.75),(.080,.75)]}

def overlap(a,b):
    return max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))

def union_area(rects,win):
    rs=[(max(r[0],win[0]),max(r[1],win[1]),min(r[2],win[2]),min(r[3],win[3])) for r in rects if overlap(r,win)>0]
    xs=sorted({x for r in rs for x in (r[0],r[2])}); total=0
    for a,b in zip(xs,xs[1:]):
        spans=sorted((r[1],r[3]) for r in rs if r[0]<b and r[2]>a)
        end=-math.inf; length=0
        for lo,hi in spans:
            length+=max(0,hi-max(lo,end)); end=max(end,hi)
        total+=(b-a)*length
    return total

def segment(a,b,step):
    axis=0 if a[1]==b[1] else 1; lo,hi=sorted((a[axis],b[axis])); fixed=math.floor(a[1-axis]/step)
    for k in range(math.floor(lo/step), math.floor(hi/step)+1):
        n=max(0,min(hi,(k+1)*step)-max(lo,k*step))
        if n: yield ((k,fixed) if axis==0 else (fixed,k)), ('H' if axis==0 else 'V'), n

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--case',type=Path,required=True); ap.add_argument('--model',type=Path,required=True)
    ap.add_argument('--step',type=float,default=260); ap.add_argument('--out',type=Path,required=True); ap.add_argument('--grt',type=Path)
    a=ap.parse_args(); model=json.loads(a.model.read_text()); inst={i['n']:i for i in model['insts']}
    macro_blocks=macros((a.case/'elements.lef').read_text())
    mp={m:pins(b[2]) for m,b in macro_blocks.items()}
    vm_obs=collections.defaultdict(list); layer=None
    block=macro_blocks.get('qfd_sp_vector_memory',(None,None,''))[2]
    for ln in block.split('\n  OBS',1)[-1].splitlines():
        lm=re.search(r'LAYER (M\d+)\s*;',ln)
        if lm: layer=lm[1]
        rm=re.search(r'RECT ([-\d. ]+)\s*;',ln)
        if rm and layer: vm_obs[layer].append(tuple(map(float,rm[1].split())))
    vm_inst=inst.get('sp_vector_memory')
    vm_obs_fraction={}
    if vm_inst:
        vw=(0,0,vm_inst['w'],vm_inst['h'])
        vm_obs_fraction={f'M{k}':union_area(vm_obs[f'M{k}'],vw)/(vm_inst['w']*vm_inst['h']) for k in range(1,10)}
    ep=collections.defaultdict(list); missing=[]
    text=(a.case/'die.v').read_text()
    for m in re.finditer(r'^\s+(\w+) (\S+) \((.*?)\);',text,re.M):
        master,name,body=m.groups()
        if name not in inst: continue
        i=inst[name]
        for p,expr in re.findall(r'\.(\S+?)\(([^()]*)\)',body):
            d=mp.get(master,{}).get(p)
            if not d: missing.append([name,p]); continue
            # Case placement uses R0; reject unhandled transforms instead of inventing coordinates.
            if i.get('orient','R0') not in ('R0','N'): raise ValueError('unsupported orientation '+str(i))
            ep[expr].append((i['x']+d['cx'],i['y']+d['cy']))
    demand=[collections.defaultdict(collections.Counter) for _ in range(2)]
    intrusions=[[],[]]; crossing_detail=[[],[]]; unknown=[]; same=[]
    for bus,cls,bits,names in model['buses']:
        pts=list(dict.fromkeys(ep.get('n_'+bus,[])))
        if len(pts)<2: unknown.append(bus); continue
        if len(pts)>2: same.append(bus)
        # Star estimates explicitly retain multi-terminal nets; not a Steiner solution.
        for dst in pts[1:]:
            src=pts[0]
            for choice,bend in enumerate(((dst[0],src[1]),(src[0],dst[1]))):
                for u,v in ((src,bend),(bend,dst)):
                    r=(min(u[0],v[0]),min(u[1],v[1]),max(u[0],v[0]),max(u[1],v[1]))
                    through=(u[1]==v[1] and VM[1]<u[1]<VM[3] and min(u[0],v[0])<VM[2] and max(u[0],v[0])>VM[0]) or (u[0]==v[0] and VM[0]<u[0]<VM[2] and min(u[1],v[1])<VM[3] and max(u[1],v[1])>VM[1])
                    if through:
                        intrusions[choice].append(bus)
                        crossing_detail[choice].append(dict(bus=bus,cls=cls,endpoint_instances=names[:8],endpoint_instance_count=len(names),vm_owned_endpoint='sp_vector_memory' in names,segment=[u,v]))
                    for cell,d,n in segment(u,v,a.step): demand[choice][cell][d]+=bits*n
    blocks=[(i['x'],i['y'],i['x']+i['w'],i['y']+i['h']) for i in inst.values() if i['w']*i['h']>40000]
    hard=[(i['x'],i['y'],i['x']+i['w'],i['y']+i['h']) for i in inst.values() if i['w']*i['h']>40000 and (i['m'].startswith(('qfd_tile','ot_hbm','qfd_io_serdes','qfd_io_ucie','qkd_pll','qfd_clkrx')))]
    overlaps=[dict(i,overlap_um2=overlap((i['x'],i['y'],i['x']+i['w'],i['y']+i['h']),VM)) for i in inst.values() if i['n']!='sp_vector_memory' and overlap((i['x'],i['y'],i['x']+i['w'],i['y']+i['h']),VM)>0]
    rows=[]
    for cell in set(demand[0])|set(demand[1]):
        x,y=cell; r=(x*a.step,y*a.step,(x+1)*a.step,(y+1)*a.step); area=a.step*a.step
        free=[area-union_area(blocks+[VM],r),area-union_area(hard+[VM],r),area-overlap(VM,r)]
        for d in 'HV':
            cap=sum(f/p*der for f,(p,der) in zip(free,PITCH[d]))
            ds=[v[cell][d] for v in demand]; ratios=[(q/cap if cap else None) for q in ds]
            rows.append(dict(rect_um=r,direction=d,capacity_track_um=cap,demand_bit_um=ds,util=ratios,blocked_demand=cap==0 and any(ds)))
    rows.sort(key=lambda r:max((v if v is not None else (math.inf if q else 0)) for v,q in zip(r['util'],r['demand_bit_um'])),reverse=True)
    out=dict(schema='opentallas.qwen-tp8.window-analytical.v1',source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (a.model,a.case/'die.v',a.case/'elements.lef')},step_um=a.step,vm_required_full_M1_M9_blockage=VM,vm_actual_lef_obstruction_fraction=vm_obs_fraction,vm_non_owned_instance_overlaps=overlaps,vm_crossing_detail=crossing_detail,vm_transit_classes=[dict(collections.Counter(v['cls'] for v in details if not v['vm_owned_endpoint'])) for details in crossing_detail],route_models=['horizontal_first_star','vertical_first_star'],capacity_note='M4/5 50%, M6/7 and M8/9 75%; large blocks reserve M4/5, clusters/hard IP reserve M6/7. This screen does not certify actual LEF obstruction or routing legality.',bus_count=len(model['buses']),resolved_bus_count=len(model['buses'])-len(unknown),missing_pins=missing,missing_pin_count=len(missing),unknown_bus_count=len(unknown),unknown_buses=unknown[:30],multiterminal_star_count=len(same),vm_intrusions={str(c):sorted(set(v)) for c,v in enumerate(intrusions)},windows_over_060=[sum((r['util'][c] or 0)>.6 or (r['capacity_track_um']==0 and r['demand_bit_um'][c]>0) for r in rows) for c in (0,1)],hottest_windows=rows[:60])
    if a.grt:
        # Actual overflow sum is apportioned by bbox area, independent of analytical demand.
        actual=collections.Counter(); vt='unknown'; ov=None
        for ln in a.grt.read_text().splitlines():
            if ln.strip().startswith('violation type:'): vt=ln.split(':',1)[1].strip()
            elif ln.strip().startswith('comment:'):
                q=re.search(r'congestion:(\d+)',ln); ov=int(q.group(1)) if q else None
            elif ln.strip().startswith('bbox') and ov is not None:
                r=tuple(map(float,re.findall(r'-?\d+\.?\d*',ln.split('=')[1])[:4])); ar=(r[2]-r[0])*(r[3]-r[1])
                if ar<=0: raise ValueError('zero-area GRT bbox')
                for x in range(math.floor(r[0]/a.step),math.floor(r[2]/a.step)+1):
                    for y in range(math.floor(r[1]/a.step),math.floor(r[3]/a.step)+1):
                        win=(x*a.step,y*a.step,(x+1)*a.step,(y+1)*a.step); actual[(x,y,vt)]+=ov*overlap(r,win)/ar
                ov=None
        out['actual_grt']=dict(source=str(a.grt),overflow=sum(actual.values()),windows=[dict(cell=k[:2],violation=k[2],overflow=v) for k,v in actual.most_common(60)])
    a.out.write_text(json.dumps(out,indent=1)+'\n'); print(json.dumps({k:out[k] for k in ('missing_pin_count','unknown_bus_count','windows_over_060')}))
if __name__=='__main__': main()
