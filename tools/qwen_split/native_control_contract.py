"""Bind the die controller graph to its real static successor and assigned pins.

Assignments describe a NEW unclosed parent. They never reuse the old master's
physical evidence. Missing production endpoints are enumerated, never tied off.
"""
import hashlib
from pathlib import Path
from qwen_split.source_pin_plan import rtl_ports, snap

ROOT=Path(__file__).resolve().parents[2]
MASTER='qfd_tt_ctlm_static_s'
SOURCE='rtl/qwen_sys/static_schedule_20261014/qfd_tt_ctlm_static_s.sv'
CLOCKS=('ck_head','ck_tree','ck_xpf','ck_me_sched')


def apply(model):
    owner=next(i for i in model['insts'] if i.name=='tt_ctlm')
    if owner.master!='qfd_tt_ctlm':
        raise ValueError('native controller transition requires the explicit historical master')
    owner.master=MASTER
    owner.w,owner.h=777.6,1814.4  # fresh actual contract outline, no legacy24nm shave
    removed=[]
    buses=[]
    for b,c,n,es in model['buses']:
        if b in ('tt_xd','tt_xr'):
            removed.append(b);continue
        es=[q for i,p in es for q in ([(i,k) for k in CLOCKS]
             if i=='tt_ctlm' and p=='ck' and c=='clock_trunk' else [(i,p)])]
        buses.append((b,c,n,es))
    model['buses']=buses
    aliases={f'uf_l{k}':('uf',[k])for k in range(4)}
    model.setdefault('port_join',{})[MASTER]=aliases
    ports=rtl_ports(ROOT/SOURCE,MASTER)
    connected={p for b,c,n,es in buses for i,p in es if i=='tt_ctlm'}
    connected={aliases.get(p,(p,[]))[0] for p in connected}
    tied={p for i,p,n,v in model.get('ties',[])if i=='tt_ctlm'}
    missing=sorted(p for p,(n,d)in ports.items()if d=='input' and p not in connected|tied)
    unknown=sorted(connected-set(ports))
    if unknown:
        raise ValueError(f'native controller graph has non-source endpoints: {unknown}')
    model['native_control_contract']=dict(master=MASTER,source=SOURCE,
        source_sha256=hashlib.sha256((ROOT/SOURCE).read_bytes()).hexdigest(),
        retired_master='qfd_tt_ctlm',removed_obsolete_buses=removed,
        source_ports={p:dict(bits=n,direction=d)for p,(n,d)in ports.items()},
        clocks=list(CLOCKS),missing_input_endpoints=missing,
        unread_outputs=sorted(p for p,(n,d)in ports.items()if d=='output'and p not in connected),
        XPF_TRANSPORT_EDGES=None,
        physical_evidence='NEW assigned parent pins only; no routed view, child roots, insertion or compensated phase inherited',
        qualified=False)
    return model['native_control_contract']


def install_master(M,model,Master):
    if 'native_control_contract'not in model:return
    inst=next(i for i in model['insts']if i.name=='tt_ctlm')
    ports=rtl_ports(ROOT/SOURCE,MASTER)
    old=M.get('qfd_tt_ctlm') or M[MASTER]
    q=Master(MASTER,inst.w,inst.h,7,'Actual static controller ABI; NEW assigned unclosed parent')
    faces={f:[]for f in 'WENS'}
    for p,(n,d)in ports.items():
        if p in CLOCKS or p=='rsi':f='N'
        elif p.startswith(('c0','c1','c2','f0','f1','f2','lc','mer','rf','sel','uf')):f='W'
        elif p in ('ib','xpf','xflt'):f='S'
        elif p in old.ports and old.ports[p][0] in ('face','pins'):f=old.ports[p][2]
        else:f='E'
        faces[f].append((p,n))
    for f,items in faces.items():
        length=q.w if f in 'NS'else q.h
        used=sum((n-1)*.096+.024+2.16 for p,n in items)
        if used>length-8.64:raise ValueError(f'{MASTER} {f} pins exceed actual outline')
        cur=(length-used)/2
        for p,n in items:
            positions=[snap(cur+.096*k)for k in range(n)]
            q.ports[p]=('pins',n,f,'M5'if f in'NS'else'M4',positions,1)
            q.order.append(p);cur=positions[-1]+2.184
    model['native_control_contract']['assigned_ports']={p:dict(bits=sp[1],face=sp[2],layer=sp[3],positions_um=list(sp[4]),direction=ports[p][1])for p,sp in q.ports.items()}
    # A scalar fault from each actual upper leaf lands on a distinct uf bit.
    from qwen_split.direct_up4 import partition_master
    rects=[]
    for p,sp in q.ports.items():
        _,n,f,L,positions,_=sp
        for k,z in enumerate(positions):
            r={'W':(0,z-.012,.192,z+.012),'E':(q.w-.192,z-.012,q.w,z+.012),
               'S':(z-.012,0,z+.012,.192),'N':(z-.012,q.h-.192,z+.012,q.h)}[f]
            rects.append((p if n==1 else f'{p}[{k}]',L,r))
    partition_master(q,model['port_join'][MASTER],rects)
    M.pop('qfd_tt_ctlm',None)  # retired abstract cannot contaminate pin/case validation
    M[MASTER]=q
