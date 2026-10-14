#!/usr/bin/env python3
"""Finite placement search on every actual planned bit pin; never a closure gate.

The replay checker judges every hop and every cut. External client pins derived
here are a proposed slot table, pending native die assignment. Capture x/pitch
and CLOSED fsr outlines stay anchored. No routing layer or timing limit changes.
"""
import argparse, hashlib, json, time
from pathlib import Path
import numpy as np
import s81_ph_vm_fe_h_floorplan as F


def search(height, seed, sweeps, assigned_capture=None, width=1520.064, fsr_pitch=388.8, control_weight=128, master_pins=None):
    F.H = height
    F.W = width
    if master_pins: F.load_actual_master_pins(master_pins)
    p = F.Plan('A')
    F.reposition(p, {f'fsr{i}': (fsr_pitch*i,p.inst[f'fsr{i}'][2]) for i in range(4)})
    names=list(p.inst); idx={n:i for i,n in enumerate(names)}
    if assigned_capture:
        F.assign_capture(p, assigned_capture)
    initial=np.array([[v[1],v[2]] for v in p.inst.values()]); xy=initial.copy()
    size=np.array([[F.MP[v[0]][0],F.MP[v[0]][1]] for v in p.inst.values()])
    movable=[i for i,n in enumerate(names) if not n.startswith(('clt','fxs','fsr'))]
    signs=np.array([[1,1],[1,-1],[-1,1],[-1,-1]])
    edges=[]; incident=[[] for n in names]
    for cls,a,b,aa,bb in p.hops:
        ia,ib=idx.get(a,-1),idx.get(b,-1)
        av=np.array([[r[0],r[1]] for r in aa]);bv=np.array([[r[0],r[1]] for r in bb])
        e=(ia,ib,np.max((av-bv)@signs.T,axis=0),len(aa),cls)
        edges.append(e)
        if ia>=0:incident[ia].append(e)
        if ib>=0:incident[ib].append(e)
    rng=np.random.default_rng(seed)
    def score(i, candidates):
        # Obstruction rectangles include the actual 2.16um clearance.
        gap=2.16
        lx=np.maximum(candidates[:,0,None],xy[None,:,0]-gap)
        rx=np.minimum(candidates[:,0,None]+size[i,0],xy[None,:,0]+size[None,:,0]+gap)
        ly=np.maximum(candidates[:,1,None],xy[None,:,1]-gap)
        ry=np.minimum(candidates[:,1,None]+size[i,1],xy[None,:,1]+size[None,:,1]+gap)
        area=np.maximum(rx-lx,0)*np.maximum(ry-ly,0);area[:,i]=0
        value=area.sum(axis=1)*1000
        for ia,ib,proj,bits,cls in incident[i]:
            da=xy[ia]-initial[ia] if ia>=0 else np.zeros(2)
            db=xy[ib]-initial[ib] if ib>=0 else np.zeros(2)
            base=da-db
            candidate_delta=candidates-xy[i]
            diff=base[None,:]+candidate_delta*(1 if i==ia else -1)
            # Unassigned external client pins follow their proposed leaf x.
            if (ia<0 or ib<0) and cls not in ('f_cap','f_cap_status'):diff[:,0]=0
            reach=np.max(diff@signs.T+proj,axis=1)
            excess=np.maximum(reach-500,0)
            value+=max(bits,control_weight)*(excess**2)*.2
            value+=reach*min(bits,64)*.002
        return value
    history=[]
    for sweep in range(sweeps):
        rng.shuffle(movable)
        for i in movable:
            # Full-slot samples plus a dense neighbourhood and current point.
            c=rng.uniform([0,0],[F.W-size[i,0],F.H-size[i,1]],(192,2))
            local=xy[i]+rng.normal(0, max(8,160*(1-sweep/max(sweeps,1))), (192,2))
            c=np.vstack([xy[i],c,local]);c[:,0]=np.round(c[:,0]/2.16)*2.16;c[:,1]=np.round(c[:,1]/8.64)*8.64
            c=np.maximum(c,0);c=np.minimum(c,[F.W-size[i,0],F.H-size[i,1]])
            scores=score(i,c);xy[i]=c[int(np.argmin(scores))]
        if sweep%5==0:
            history.append({'sweep':sweep,'local_objective':float(sum(score(i,xy[i:i+1])[0] for i in movable))})
    F.reposition(p,{n:tuple(xy[i]) for i,n in enumerate(names)},True)
    placements=p.check_place();hops=p.check_hops()
    return {'schema':'opentallas.s81_vm_fe_h.search.v1','variant':'A','height':height,'width':width,'fsr_pitch':fsr_pitch,'slot_adopted':False,'control_weight':control_weight,'seed':seed,'sweeps':sweeps,
            'derive_external_pins':True,'source_sha256':hashlib.sha256(F.SRC.encode()).hexdigest(),
            'actual_capture_assignment':assigned_capture,'actual_pin_receipts':F.PIN_RECEIPTS,
            'placement_violations':placements,'hops_over_500':{k:v['len_max'] for k,v in hops.items() if v['len_max']>500},
            'history':history,'limits':{'hop_um':500,'cut':.60},'closure_claim':False,
            'required_followup':'Replay full cut and actual per-pair reach checker; assign native FE client pins and source clocks.',
            'instances':{n:{'master':m,'x':x,'y':y,'w':F.MP[m][0],'h':F.MP[m][1]} for n,(m,x,y) in p.inst.items()}}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--height',type=float,default=889.92);ap.add_argument('--seed',type=int,default=1);ap.add_argument('--sweeps',type=int,default=50);ap.add_argument('--out',required=True);ap.add_argument('--assigned-capture');ap.add_argument('--width',type=float,default=1520.064);ap.add_argument('--fsr-pitch',type=float,default=388.8);ap.add_argument('--control-weight',type=int,default=128);ap.add_argument('--master-pins')
    a=ap.parse_args();r=search(a.height,a.seed,a.sweeps,a.assigned_capture,a.width,a.fsr_pitch,a.control_weight,a.master_pins);Path(a.out).write_text(json.dumps(r,indent=2)+'\n');print('PLACEMENT_SEARCH',len(r['placement_violations']),'overlaps/outline;',r['hops_over_500']);
