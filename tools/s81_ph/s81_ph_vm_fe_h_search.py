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


def search(height, seed, sweeps, assigned_capture=None, width=1520.064, fsr_pitch=388.8, control_weight=128, master_pins=None, initial_placements=None, strict_reach=False, pin_escape_margin=0.0, cut_weight=0.0, cut_target=0.5, fixed=()):
    F.H = height
    F.W = width
    if master_pins: F.load_actual_master_pins(master_pins)
    p = F.Plan('A')
    F.reposition(p, {f'fsr{i}': (fsr_pitch*i,p.inst[f'fsr{i}'][2]) for i in range(4)})
    if initial_placements:
        proposed=json.loads(Path(initial_placements).read_text())
        F.reposition(p,{n:(v['x'],v['y']) for n,v in proposed['instances'].items()},
                     proposed.get('derive_external_pins',False))
    names=list(p.inst); idx={n:i for i,n in enumerate(names)}
    if assigned_capture:
        F.assign_capture(p, assigned_capture)
    initial=np.array([[v[1],v[2]] for v in p.inst.values()]); xy=initial.copy()
    size=np.array([[F.MP[v[0]][0],F.MP[v[0]][1]] for v in p.inst.values()])
    # Capture launch pins anchor CLT; FXS are independent hard children whose
    # positions must be solved from their real CLT/relay/status pin reaches.
    movable=[i for i,n in enumerate(names) if not n.startswith(('clt','fsr')) and n not in fixed]
    # ---- cut model (claude s81-grpA r6, --cut-weight): FULL vertical / horizontal cut profiles on the replay's gcell grid.
    # demand: every hop's bits span the columns (rows) between its two pin centroids; capacity: free-parent tracks minus the
    # leaves' blockage (leaf: M6 H / 0.85 M7 V; dsfd_vm_fsr: 0), 80 % usable -- the replay's numbers.  Penalty per candidate:
    # sum over columns and rows of relu(demand / capacity - cut_target)^2.
    G=F.G; nx=int(np.ceil(F.W/G)); ny=int(np.ceil(F.H/G)); cxs=(np.arange(nx)+.5)*G; cys=(np.arange(ny)+.5)*G
    hcap0, vcap0 = F.H_FREE*G*F.USABLE, F.V_FREE*G*F.USABLE
    def blk(i):
        m=p.inst[names[i]][0]
        return ((F.H_FREE-0.0)*G*F.USABLE, (F.V_FREE-0.0)*G*F.USABLE) if m=='dsfd_vm_fsr' else ((F.H_FREE-F.H_LEAF)*G*F.USABLE, (F.V_FREE-F.V_LEAF)*G*F.USABLE)
    def foot(i, pos):
        # pos (k, 2) -> (k, nx) H-capacity loss of each column, (k, ny) V-capacity loss of each row
        w,h=size[i]; bh,bv=blk(i)
        ox=np.clip(np.minimum(pos[:,0,None]+w,(np.arange(nx)+1)*G)-np.maximum(pos[:,0,None],np.arange(nx)*G),0,G)/G
        oy=np.clip(np.minimum(pos[:,1,None]+h,(np.arange(ny)+1)*G)-np.maximum(pos[:,1,None],np.arange(ny)*G),0,G)/G
        return ox*(h/G)*bh, oy*(w/G)*bv
    colcap=np.full(nx, hcap0*ny); rowcap=np.full(ny, vcap0*nx)
    for i in range(len(names)):
        fc,fr=foot(i, xy[i:i+1]); colcap-=fc[0]; rowcap-=fr[0]
    cen=[]
    for cls,a,b,aa,bb in p.hops:
        ia,ib=idx.get(a,-1),idx.get(b,-1)
        ca=np.mean([[r[0],r[1]] for r in aa],axis=0); cb=np.mean([[r[0],r[1]] for r in bb],axis=0)
        cen.append((ia,ib,ca,cb,len(aa),cls))
    cinc=[[] for n in names]
    for e in cen:
        if e[0]>=0: cinc[e[0]].append(e)
        if e[1]>=0 and e[1]!=e[0]: cinc[e[1]].append(e)
    def ends(e, pos_i=None, i=None):
        ia,ib,ca,cb,nb,cls=e
        da=(xy[ia]-initial[ia]) if ia>=0 else np.zeros(2); db=(xy[ib]-initial[ib]) if ib>=0 else np.zeros(2)
        A=np.broadcast_to(ca+da,(1 if pos_i is None else len(pos_i),2)).copy(); B=np.broadcast_to(cb+db,A.shape).copy()
        if pos_i is not None:
            dd=pos_i-xy[i]
            if ia==i: A+=dd
            if ib==i: B+=dd
        if (ia<0 or ib<0) and cls not in ('f_cap','f_cap_status'):
            if ia<0: A[:,0]=B[:,0]
            else: B[:,0]=A[:,0]
        return A,B,nb
    def span(A,B,nb):
        lo,hi=np.minimum(A[:,0],B[:,0]),np.maximum(A[:,0],B[:,0]); dc=((cxs[None,:]>lo[:,None])&(cxs[None,:]<hi[:,None]))*nb
        lo,hi=np.minimum(A[:,1],B[:,1]),np.maximum(A[:,1],B[:,1]); dr=((cys[None,:]>lo[:,None])&(cys[None,:]<hi[:,None]))*nb
        return dc,dr
    demc=np.zeros(nx); demr=np.zeros(ny)
    for e in cen:
        dc,dr=span(*ends(e)); demc+=dc[0]; demr+=dr[0]
    def cut_pen(i, cands):
        dc=np.broadcast_to(demc,(len(cands),nx)).copy(); dr=np.broadcast_to(demr,(len(cands),ny)).copy()
        for e in cinc[i]:
            o_c,o_r=span(*ends(e)); n_c,n_r=span(*ends(e,cands,i)); dc+=n_c-o_c; dr+=n_r-o_r
        fo_c,fo_r=foot(i,xy[i:i+1]); fn_c,fn_r=foot(i,cands)
        cc=colcap[None,:]+fo_c-fn_c; rc=rowcap[None,:]+fo_r-fn_r
        return (np.maximum(dc/np.maximum(cc,1)-cut_target,0)**2).sum(axis=1)+(np.maximum(dr/np.maximum(rc,1)-cut_target,0)**2).sum(axis=1), dc, dr, cc, rc
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
        value=area.sum(axis=1)*1000+(area>1e-9).sum(axis=1)*1e12
        for ia,ib,proj,bits,cls in incident[i]:
            da=xy[ia]-initial[ia] if ia>=0 else np.zeros(2)
            db=xy[ib]-initial[ib] if ib>=0 else np.zeros(2)
            base=da-db
            candidate_delta=candidates-xy[i]
            diff=base[None,:]+candidate_delta*(1 if i==ia else -1)
            # Unassigned external client pins follow their proposed leaf x.
            if (ia<0 or ib<0) and cls not in ('f_cap','f_cap_status'):diff[:,0]=0
            reach=np.max(diff@signs.T+proj,axis=1)
            excess=np.maximum(reach-(500-pin_escape_margin),0)
            if strict_reach:
                value+=(excess>1e-6)*1e10
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
            scores=score(i,c)
            if cut_weight>0:
                cp,dc,dr,cc,rc=cut_pen(i,c); scores=scores+cut_weight*cp
            k=int(np.argmin(scores))
            if cut_weight>0:
                demc[:]=dc[k]; demr[:]=dr[k]; colcap[:]=cc[k]; rowcap[:]=rc[k]
            xy[i]=c[k]
        if sweep%5==0 or sweep==sweeps-1:
            history.append({'sweep':sweep,'local_objective':float(sum(score(i,xy[i:i+1])[0] for i in movable)),
                            'full_v_cut_model':round(float((demc/np.maximum(colcap,1)).max()),3),'full_h_cut_model':round(float((demr/np.maximum(rowcap,1)).max()),3)})
            print('sweep',sweep,history[-1],flush=True)
    F.reposition(p,{n:tuple(xy[i]) for i,n in enumerate(names)},True)
    placements=p.check_place();hops=p.check_hops()
    return {'schema':'opentallas.s81_vm_fe_h.search.v1','variant':'A','height':height,'width':width,'fsr_pitch':fsr_pitch,'slot_adopted':False,'control_weight':control_weight,'seed':seed,'sweeps':sweeps,
            'derive_external_pins':True,'source_sha256':hashlib.sha256(F.SRC.encode()).hexdigest(),
            'actual_capture_assignment':assigned_capture,'actual_pin_receipts':F.PIN_RECEIPTS,'initial_placements':initial_placements,'strict_reach_objective':strict_reach,'cut_weight':cut_weight,'cut_target':cut_target,'fixed':list(fixed),'heuristic_pin_escape_reserve_um':pin_escape_margin,
            'placement_violations':placements,'hops_over_500':{k:v['len_max'] for k,v in hops.items() if v['len_max']>500},
            'history':history,'limits':{'hop_um':500,'cut':.60},'closure_claim':False,
            'required_followup':'Replay full cut and actual per-pair reach checker; assign native FE client pins and source clocks.',
            'instances':{n:{'master':m,'x':x,'y':y,'w':F.MP[m][0],'h':F.MP[m][1]} for n,(m,x,y) in p.inst.items()}}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--height',type=float,default=889.92);ap.add_argument('--seed',type=int,default=1);ap.add_argument('--sweeps',type=int,default=50);ap.add_argument('--out',required=True);ap.add_argument('--assigned-capture');ap.add_argument('--width',type=float,default=1520.064);ap.add_argument('--fsr-pitch',type=float,default=388.8);ap.add_argument('--control-weight',type=int,default=128);ap.add_argument('--master-pins')
    ap.add_argument('--initial-placements',help='explicit source candidate placement; FSR anchors follow this request')
    ap.add_argument('--strict-reach',action='store_true',help='penalize every bit-pair reach violation before soft wire length; full replay remains required')
    ap.add_argument('--pin-escape-margin',type=float,default=0.0,help='reserve geometry margin in search only; exact normal-escape replay still determines reach')
    ap.add_argument('--cut-weight',type=float,default=0.0,help='claude s81-grpA r6: full-cut profile penalty weight (0 = the old reach-only search)')
    ap.add_argument('--cut-target',type=float,default=0.5); ap.add_argument('--fixed',default='',help='comma list of instances kept where the initial placement has them')
    a=ap.parse_args();r=search(a.height,a.seed,a.sweeps,a.assigned_capture,a.width,a.fsr_pitch,a.control_weight,a.master_pins,a.initial_placements,a.strict_reach,a.pin_escape_margin,a.cut_weight,a.cut_target,tuple(x for x in a.fixed.split(',') if x));Path(a.out).write_text(json.dumps(r,indent=2)+'\n');print('PLACEMENT_SEARCH',len(r['placement_violations']),'overlaps/outline;',r['hops_over_500']);
