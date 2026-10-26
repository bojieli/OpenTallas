#!/usr/bin/env python3
"""Expand the native B2 VM's wiring-only wrapper into real die leaves.

The bit ranges below are exactly the NC=4/RG=2/WG=2 ot_vms_slice assignments.
No historical hfd_hgi_vms timing macro is emitted. Long seams remain explicit.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def leaf(path):
    t=path.read_text()
    w,h=map(float,re.search(r'\bSIZE ([\d.]+) BY ([\d.]+)',t).groups())
    ports={}
    for m in re.finditer(r'\n\s*PIN (\S+)\n(.*?)\n\s*END \1[ \t]*(?=\n|$)',t,re.S):
        n,b=m.groups()
        if 'USE POWER' in b or 'USE GROUND' in b: continue
        base=re.sub(r'\[\d+\]$','',n)
        direction=re.search(r'\bDIRECTION (\S+)',b)[1].lower()
        r=re.search(r'\bRECT\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)',b)
        if not r: raise ValueError(f'{path}: pin {n} has no RECT')
        a,c,d,e=map(float,r.groups())
        idx=int(re.search(r'\[(\d+)\]$',n)[1]) if '[' in n else 0
        p=ports.setdefault(base,dict(direction=direction,bits={}))
        p['bits'][idx]=[(a+d)/2,(c+e)/2]
    for n,p in ports.items():
        if sorted(p['bits'])!=list(range(len(p['bits']))): raise ValueError(f'{path} {n}: noncontiguous pin bits')
        p['width']=len(p['bits'])
    blocked={}
    blocks=[m[1] for m in re.finditer(r'\n\s*PIN (?:VDD|VSS)\n(.*?)\n\s*END (?:VDD|VSS)[ \t]*(?=\n|$)',t,re.S)]
    ob=re.search(r'\n\s*OBS\n(.*?)\n\s*END[ \t]*(?=\n)',t,re.S)
    if ob:blocks.append(ob[1])
    for body in blocks:
        ly=None
        for line in body.splitlines():
            mm=re.search(r'\bLAYER (M\d+)\s*;',line)
            if mm:ly=mm[1]
            mm=re.search(r'\bRECT\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)',line)
            if mm and ly:blocked.setdefault(ly,[]).append(tuple(map(float,mm.groups())))
    return w,h,ports,blocked


def main(a):
    layout=json.loads(a.pg_manifest.read_text())
    boundary={}
    def port(n,d,w,role='data'): boundary[n]=dict(direction=d,width=w,role=role)
    for n,d,w in [('clk','input',1),('rst_n','input',1),('sid','input',2),('cq','input',1352),('cr','output',1096),
                  ('rq','input',272),('rq_cr','output',16),('rr','output',4112),('wq','input',4496),
                  ('wq_cr','output',16),('wq_done','output',16),('dq','input',2248),('dq_done','output',8),
                  ('vcb','input',2130),('vcb_cr','output',1),('kq_done','output',8),
                  ('cw_in','input',2224),('cw_in_cr','output',2),('cw_out','output',2224),('cw_out_cr','input',2),
                  ('ccw_in','input',2224),('ccw_in_cr','output',2),('ccw_out','output',2224),('ccw_out_cr','input',2),
                  ('bank_status','output',144),('hub_status','output',3),('mirror_busy','output',2)]:
        port(n,d,w,'clock' if n=='clk' else 'reset' if n=='rst_n' else 'data')
    children=[]; pins={}; records={};obstacles={}
    for p in layout['leaves']:
        kind=p['kind'];view=a.root/f'physical/ref_tile/vms_{kind}/views/ot_vms_{kind}'
        lef=view/f'ot_vms_{kind}.lef'
        w,h,ps,obs=leaf(lef)
        n=p['instance'];pins[n]=ps;records[n]=p
        obstacles[n]=obs
        lint=view/'child_lint.json'
        lr=json.loads(lint.read_text()) if lint.exists() else {}
        libs={c:str((view/f'ot_vms_{kind}_{c}.lib').relative_to(a.root)) for c in ('tt','ff','ss')}
        children.append(dict(instance=n,logical_module=f'ot_vms_{kind}',view_lef=str(lef.relative_to(a.root)),
                             view_lib=libs,xy_um=[p['x'],p['y']],orientation='R0',w_um=w,h_um=h,pg_top=p['top_pg'],
                             closure_status='real view; child-lint '+lr.get('verdict','unavailable')+'; authoritative verdict required',
                             source_sha256={str(lef.relative_to(a.root)):sha(lef)},ports={k:{'width':v['width'],'direction':v['direction']} for k,v in ps.items()}))
    connections=[];binding=[]
    def ep(n,p,l=0,w=1):
        check=boundary[p]['width'] if n=='$boundary' else pins[n][p]['width']
        if l<0 or w<1 or l+w>check: raise ValueError(f'{n}/{p}[{l}+:{w}] exceeds actual {check}-bit port')
        return dict(instance=n,port=p,lsb=l,width=w)
    def wire(n,*ends,kind='data'):
        if len({e['width'] for e in ends})!=1: raise ValueError(f'{n}: differing widths')
        connections.append(dict(net=n,endpoints=list(ends),kind=kind))
        for e in ends:
            if e['instance']=='$boundary':
                for c in ends:
                    if c['instance']!='$boundary': binding.append(dict(parent_port=e['port'],parent_lsb=e['lsb'],width=e['width'],child_instance=c['instance'],child_port=c['port'],child_lsb=c['lsb']))
    def ext(parent,n,p,w,l=0,cl=0): wire(f'ext_{parent}_{n}_{cl}',ep('$boundary',parent,l,w),ep(n,p,cl,w),kind=boundary[parent]['role'])
    for n in pins:
        ext('clk',n,'clk',1);ext('rst_n',n,'rst_n',1)
        if 'sid' in pins[n]: ext('sid',n,'sid',2)
    ext('cq','u_hub','cq',1352);ext('cr','u_hub','cr',1096)
    wire('hq',ep('u_rcl','hq',0,338),ep('u_hub','cq',1352,338))
    wire('hr',ep('u_hub','cr',1096,274),ep('u_rcl','hr',0,274))
    ext('hub_status','u_hub','status',3)
    ext('vcb','u_star','vcb',2130);ext('vcb_cr','u_star','vcb_cr',1)
    constants=[]
    for b in range(8):
        n=f'g_bank[{b}].u_bank'
        constants.append(dict(instance=n,port='bid',width=3,value=b))
        for g in range(2):
            for par,cp,stride in [('rq','rq',17),('rq_cr','rq_cr',1),('rr','rr',257),('wq','wq',281),('wq_cr','wq_cr',1),('wq_done','wq_done',1)]:
                ext(par,n,cp,stride,(g*8+b)*stride,g*stride)
        ext('dq',n,'dq',281,b*281);ext('dq_done',n,'dq_done',1,b);ext('kq_done',n,'kq_done',1,b);ext('bank_status',n,'status',18,b*18)
        for hp,bp,w in [('pq','pq',285),('pq_cr','pq_cr',1),('pr','pr',266)]: wire(f'{hp}_{b}',ep('u_hub',hp,b*w,w),ep(n,bp,0,w))
        wire(f'eg_{b}',ep(n,'eg',0,276),ep('u_cw','eg',b*276,276),ep('u_ccw','eg',b*276,276))
        for j,stop in enumerate(('u_cw','u_ccw')):
            wire(f'eg_cr{j}_{b}',ep(stop,'eg_cr',b,1),ep(n,'eg_cr',j,1))
            for sp,bp,w in [('xq','xq' if j==0 else 'xq2',276),('xq_cr','xq_cr' if j==0 else 'xq2_cr',1),('xq_done','xq_done' if j==0 else 'xq2_done',1)]: wire(f'{bp}_{b}',ep(stop,sp,b*w,w),ep(n,bp,0,w))
        wire(f'kq_{b}',ep('u_star','kq',b*281,281),ep(n,'kq',0,281))
        wire(f'kq_cr_{b}',ep(n,'kq_cr',0,1),ep('u_star','kq_cr',b,1))
    for j,stop in enumerate(('u_cw','u_ccw')):
        d='cw' if j==0 else 'ccw'
        constants.append(dict(instance=stop,port='dir',width=1,value=j))
        for parent,child,w in [(d+'_in','l_in',2224),(d+'_in_cr','l_in_cr',2),(d+'_out','l_out',2224),(d+'_out_cr','l_out_cr',2)]: ext(parent,stop,child,w)
        ext('mirror_busy',stop,'mirror_busy',1,j)
        for sp,hp,w in [('pi','cwi' if j==0 else 'cci',290),('pi_cr','cwi_cr' if j==0 else 'cci_cr',1),('cco','cco0' if j==0 else 'cco1',264)]: wire(hp,ep(stop,sp,0,w),ep('u_hub',hp,0,w))
        for sp,rp,w in [('rce',f'rce{j}',288),('rce_cr',f'rce{j}_cr',1),('ri',f'ri{j}',266),('ri_cr',f'ri{j}_cr',1)]: wire(rp,ep(stop,sp,0,w),ep('u_rcl',rp,0,w))
    for first,second,label in [('u_cw','u_ccw','01'),('u_ccw','u_cw','10')]:
        for p,q,w in [('wko','wki',3),('wko_cr','wki_cr',1),('ack_o','ack_i',1)]: wire(p+label,ep(first,p,0,w),ep(second,q,0,w))
    def xy(e,bit):
        p=records[e['instance']];r=pins[e['instance']][e['port']]['bits'][e['lsb']+bit]
        return p['x']+r[0],p['y']+r[1]
    long=[];cuts=[]
    for axis,pos in [('x',layout['outline_um'][0]/2),('y',layout['outline_um'][1]/2)]:
        idx=0 if axis=='x' else 1;demand=0;terms=[]
        for c in connections:
            es=[e for e in c['endpoints'] if e['instance']!='$boundary']
            if len(es)<2 or c['kind'] in ('clock','reset'):continue
            nb=sum(min(xy(e,i)[idx] for e in es)<pos<=max(xy(e,i)[idx] for e in es) for i in range(es[0]['width']))
            if nb: demand+=nb;terms.append(dict(net=c['net'],bits=nb))
        # Count real PG/OBS intervals on the lower die layer, not a solid
        # occupied box. M7/M8/M9 parent power and 5% spare remain reserved.
        span=layout['outline_um'][1] if axis=='x' else layout['outline_um'][0]
        per_layer=[]
        for ly,pitch,reserve in ((('M6',.064,.05),('M8',.08,.05+2*.09803921568627451)) if axis=='x' else
                                 (('M7',.064,.05+2*.544/4.896),('M9',.08,.05+2*.09803921568627451))):
            intervals=[]
            for n,obs in obstacles.items():
                p=records[n];ox,oy=p['x'],p['y'];margin=.048 if ly in ('M6','M7') else .06
                for x0,y0,x1,y1 in obs.get(ly,[]):
                    r=[x0+ox,y0+oy,x1+ox,y1+oy]
                    if r[idx]-margin<=pos<=r[idx+2]+margin:
                        intervals.append((max(0,r[1-idx]-margin),min(span,r[3-idx]+margin)))
            merged=[]
            for lo,hi in sorted(intervals):
                if merged and lo<=merged[-1][1]:merged[-1][1]=max(merged[-1][1],hi)
                else:merged.append([lo,hi])
            blocked=sum(hi-lo for lo,hi in merged)
            avail=max(0,math.floor((span-blocked)/pitch*(1-reserve)))
            per_layer.append(dict(layer=ly,pitch_um=pitch,blocked_um=blocked,pg_and_spare_reserved=reserve,tracks=avail))
        capacity=sum(r['tracks'] for r in per_layer)
        cuts.append(dict(axis=axis,pos_um=pos,demand_bits=demand,usable_tracks=capacity,ratio=demand/capacity,
                         capacity_grade='actual PG/OBS intersections + explicit parent PG and spare; prototype only',layers=per_layer,terms=terms))
    for c in connections:
        es=[e for e in c['endpoints'] if e['instance']!='$boundary']
        if len(es)<2 or c['kind'] in ('clock','reset'):continue
        dist=max(abs(xy(es[0],i)[0]-xy(e,i)[0])+abs(xy(es[0],i)[1]-xy(e,i)[1]) for i in range(es[0]['width']) for e in es[1:])
        if dist>500:long.append(dict(net=c['net'],max_manhattan_um=dist,minimum_added_stages=math.ceil(dist/500)-1,bits=es[0]['width']))
    sources=[a.root/'rtl/hbm_accel/generic/vm/b2'/f'ot_vms_{k}.sv' for k in ('slice','bank','hub','rstop','rcl','star')]
    rec=dict(schema='opentallas.hbm.native_component.v1',component='vm',logical_module='ot_vms_slice',source_commit=a.source_commit,
             source_sha256={str(p.relative_to(a.root)):sha(p) for p in sources},parameters=dict(NC=4,RG=2,WG=2,RRS=[3,3],WRS=[3,3]),
             outline_um=layout['outline_um'],boundary_ports=boundary,children=children,connections=connections,boundary_binding=binding,
             constants=constants,unused_outputs=[dict(instance='u_star',port='epoch',width=4,reason='native slice cb_epoch is unused')],
             replicated_instances=['hb_vms_SW','hb_vms_SE','hb_vms_NW','hb_vms_NE'],cut_ledger=cuts,long_seams=long,
             unresolved=['Exact leaf views fit and actual PG is measured, but placement is a PG prototype.',
                         'Long internal packet/ring/wide seams need registered credit transport with an exact/throughput composition gate.',
                         'Historical f_lgc/vmap bundle bridge must be replaced by explicit native port bindings in the die consumer components.'],
             closed=False,hard_parent_created=False,final_signoff_eligible=False)
    a.out.mkdir(parents=True,exist_ok=True)
    (a.out/'component.json').write_text(json.dumps(rec,indent=2)+'\n')
    print(json.dumps(dict(children=len(children),connections=len(connections),boundary_bindings=len(binding),long_seams=len(long),cuts=[{k:v for k,v in c.items() if k!='terms'} for c in cuts])))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True);p.add_argument('--pg-manifest',type=Path,required=True)
    p.add_argument('--source-commit',required=True);p.add_argument('--out',type=Path,required=True)
    main(p.parse_args())
