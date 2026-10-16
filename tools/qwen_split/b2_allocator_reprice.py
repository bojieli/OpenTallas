#!/usr/bin/env python3
"""Real relay allocator diagnostic for the proposed b2 source interfaces.

Uses all die macro obstacles, exact source ABI, and explicit NEW candidate pin
frames. Other data-bus relay reservations and the unimplemented six-source VM /
controller join are excluded. No emitted die or physical/native qualification.
"""
import argparse, copy, hashlib, json, os, re, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'results/arch/qwen_tp8_1012')]

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-root',required=True,type=Path)
    ap.add_argument('--mode',choices=['baseline','b2'],required=True)
    ap.add_argument('--out',required=True,type=Path)
    a=ap.parse_args(); a.out.mkdir(parents=True,exist_ok=True)
    import die_top_lint as D
    import qwen_rom_fulldie_b3r2 as G
    from qwen_split.source_pin_plan import rtl_ports,snap
    from qwen_split.direct_up4 import partition_master
    os.environ['OT_RELAY_SKIP']='1'
    D.QWEN_RECIPE='tp8b';D._QW.clear();D.QSRC=None
    v,m=D.load_qwen()[:2]
    M=v.masters(m,1);by={i.name:i for i in m['insts']}
    oldjoins=copy.deepcopy(m.get('port_join',{}))
    ports={f'sp_port_tiles_{b}{s}'for b in range(3)for s in ('','_f1')}
    lanes={f'sp_band_lanes_{b}'for b in range(3)}
    sers={f'sp_res_ser_{b}'for b in range(3)}
    leaves={f'tt_up4_leaf{k}'for k in range(4)}
    targets=ports|lanes|sers|leaves
    # Clock and reset topology stays complete; data allocation is subsystem-only.
    data=[b for b in m['buses']if b[1] not in ('clock_trunk','reset')and any(i in targets for i,p in b[3])]
    control=[b for b in m['buses']if b[1]in('clock_trunk','reset')]
    source_receipts=[];frames={};aliases={};notes=[]
    def frame(master,path,w,h,faceof):
        pp=rtl_ports(a.source_root/path,master)
        q=v.Master(master,w,h,7,'NEW b2 source-bound candidate pin frame, unqualified')
        faces={f:[]for f in 'WENS'}
        for p,(n,d)in pp.items():faces[faceof(p)].append((p,n))
        for f,items in faces.items():
            length=w if f in 'NS'else h
            need=sum((n-1)*.096+.024+2.16 for p,n in items)
            if need>length-8.64:raise ValueError(f'{master}.{f} requires {need} um, has {length-8.64}')
            cur=(length-need)/2
            for p,n in items:
                ps=[snap(cur+k*.096)for k in range(n)]
                q.ports[p]=('pins',n,f,'M5'if f in'NS'else'M4',ps,1);q.order.append(p)
                cur=ps[-1]+2.184
        M[master]=q
        source_receipts.append(dict(master=master,source=path,sha256=hashlib.sha256((a.source_root/path).read_bytes()).hexdigest(),ports=pp))
        frames[master]=dict(w=w,h=h,ports=copy.deepcopy(q.ports))
        return q
    def alias(master,name,real,indices):aliases.setdefault(master,{})[name]=(real,list(indices));return name
    def add(name,n,src,dst):return(name,'tree_spine',n,[src,dst])
    if a.mode=='b2':
        pm='qfd_port_half_b2';lm='qfd_sp_halfband_lanes';um='qfd_band_upper_b2';sm='qfd_res_ser_half_b2'
        frame(pm,'rtl/qwen_split/qfd_port_half_b2.sv',1036.8,2462.4,
              lambda p:'W'if p.startswith('bw')else'S'if p in('cw0','ty')else'N'if p.startswith('ck')or p in('rst_n','rq')else'E')
        frame(lm,'rtl/physical/ot_qwen_halfband_lanes_slots.sv',881.28,648.,
              lambda p:'N'if p in('tw','ty')else'S'if p in('ck','rst_n')or p.startswith('ck_l')else'E')
        frame(sm,'rtl/qwen_split/qfd_res_ser_half_b2.sv',777.6,324.,
              lambda p:'S'if p=='rq'else'N'if p in('ck','rst_n')else'E')
        frame(um,'rtl/qwen_split/qfd_band_upper_b2.sv',86.4,410.4,
              lambda p:'W'if p in('pw','pw_v','lf')else'N'if p in('clk','rst_n')else'E')
        # Exact numeric aliases; no centroid stand-ins for missing pin groups.
        alias(pm,'cw_data','cw0',range(2048))
        for l in range(4):
            alias(lm,f'pw_l{l}_d',f'pw_l{l}',range(128));alias(lm,f'pw_l{l}_v',f'pw_l{l}',[128])
            alias(lm,f'f_up_l{l}','f_up',[l]);alias(lm,f'tt_l{l}','tt',[128*l+j+512*k for k in range(3)for j in range(128)])
        alias(lm,'tt_uv','tt',[1536,1537]);alias(um,'uv','tt_use',[0])
        for hb in range(6):
            alias(um,f'pw_b{hb}','pw',range(128*hb,128*(hb+1)))
            alias(um,f'pv_b{hb}','pw_v',[hb]);alias(um,f'lf_b{hb}','lf',[hb])
        new=[];port_by={};lane_by={};ser_by={}
        for hb in range(6):
            b,h=divmod(hb,2);oldp=by[f'sp_port_tiles_{b}'+('_f1'if h else'')]
            p=copy.copy(oldp);p.master=pm
            flip=by[f'sp_port_tiles_{b}'].orient=='MX'
            p.orient=('R180'if flip else'MY')if h else('MX'if flip else'R0')
            l=copy.copy(by[f'sp_band_lanes_{b}']);l.name=f'sp_halfband_{hb}';l.master=lm;l.w,l.h=881.28,648.
            l.x=p.x+(p.w-l.w)/2;l.y=p.y+p.h+43.2 if flip else p.y-43.2-l.h;l.orient=p.orient
            s=copy.copy(by[f'sp_res_ser_{b}']);s.name=f'sp_halfres_{hb}';s.master=sm;s.w,s.h=777.6,324.
            s.x=p.x+(p.w-s.w)/2;s.y=p.y-86.4-s.h if flip else p.y+p.h+86.4;s.orient=p.orient
            port_by[hb]=p;lane_by[hb]=l;ser_by[hb]=s;new.extend((p,l,s))
        # Wider/taller upper outlines must find real free homes, not overlap peers.
        obs=[i for i in m['insts']if i.name not in targets]
        for l in range(4):
            u=copy.copy(by[f'tt_up4_leaf{l}']);u.master=um;u.w,u.h=86.4,410.4
            home=None
            for radius in range(160):
                for dy in range(-radius,radius+1):
                    for dx in ({-radius,radius}if abs(dy)<radius else range(-radius,radius+1)):
                        x,y=u.x+dx*21.6,u.y+dy*21.6
                        if x<0 or y<0 or x+u.w>m['die']['w']or y+u.h>m['die']['h']:continue
                        if any(i.x<x+u.w and i.x+i.w>x and i.y<y+u.h and i.y+i.h>y for i in obs+new):continue
                        home=(x,y);break
                    if home:break
                if home:break
            if not home:raise ValueError('no legal upper candidate home')
            u.x,u.y=home;new.append(u)
        newdata=[]
        for bid,cl,n,es in data:
            if bid.startswith('bword_'):
                src,(pn,pin)=es;b=int(pn.split('_')[3]);hb=2*b+int(pn.endswith('_f1'))
                pin=f'bw{int(pin[2:])%8}' if re.fullmatch(r'bw[0-9]+',pin) else pin
                newdata.append(add(bid,n,src,(port_by[hb].name,pin)));continue
            # Selectors and controller faults retain source-exact existing pin slices.
            if any(i in leaves for i,p in es)and not bid.startswith(('pword_','tt_lf','tt_ty')):
                newdata.append((bid,cl,n,es));continue
        for hb in range(6):
            b,h=divmod(hb,2);p,l,s=port_by[hb],lane_by[hb],ser_by[hb]
            newdata.extend([add(f'b2_tw_{hb}',2048,(p.name,'cw_data'),(l.name,'tw')),
                            add(f'b2_ty_{hb}',2048,(l.name,'ty'),(p.name,'ty')),
                            add(f'b2_rq_{hb}',2213,(p.name,'rq'),(s.name,'rq'))])
            for u in range(4):
                un=f'tt_up4_leaf{u}'
                newdata.extend([add(f'b2_pword_{hb}_l{u}',128,(l.name,f'pw_l{u}_d'),(un,f'pw_b{hb}')),
                                add(f'b2_pword_{hb}_v{u}',1,(l.name,f'pw_l{u}_v'),(un,f'pv_b{hb}')),
                                add(f'b2_lf_{hb}_l{u}',1,(l.name,f'f_up_l{u}'),(un,f'lf_b{hb}'))])
        for u in range(4):newdata.append(add(f'b2_return_l{u}',384,(f'tt_up4_leaf{u}','tt_ty'),(lane_by[0].name,f'tt_l{u}')))
        # Qualified return uv requires both distinct source outputs; preserve exact bits.
        alias(um,'uv_pair','tt_use',[0])
        newdata.extend([add('b2_return_use',1,('tt_up4_leaf0','tt_use'),(lane_by[0].name,'tt_use_alias')),
                        add('b2_return_v',1,('tt_up4_leaf0','tt_v'),(lane_by[0].name,'tt_v_alias'))])
        alias(lm,'tt_use_alias','tt',[1536]);alias(lm,'tt_v_alias','tt',[1537])
        m['insts']=[i for i in m['insts']if i.name not in targets]+new
        cc=[]
        for bid,cl,n,es in control:
            ee=[]
            for i,pn in es:
                if i in lanes:
                    b=int(i.rsplit('_',1)[1]);ee.extend((lane_by[2*b+h].name,pn)for h in range(2))
                elif i in sers:
                    b=int(i.rsplit('_',1)[1]);ee.extend((ser_by[2*b+h].name,'rst_n'if cl=='reset'else'ck')for h in range(2))
                else:ee.append((i,pn))
            cc.append((bid,cl,n,list(dict.fromkeys(ee))))
        control=cc
        # Data tc/am/rb/LC interfaces need NEW controller and VM producers/consumers;
        # deliberately leave them out instead of pricing fictitious source pins.
        notes=['cw valid/fault completeness and central cross-half status checking remain OPEN',
               'tc/am/rb/LC and serializer command paths await actual new controller/VM source interfaces; excluded from partial price',
               'all macro obstacles retained; other data-bus relay reservations excluded',
               'new outlines and pins are explicit candidate grants, not closed views']
        data=newdata
        # Existing selector bundle is a wire concatenation of two distinct
        # source ports, not a new unregistered control input.
        uq=M[um]
        if any(p=='sel' for bid,cl,n,es in data for i,p in es if i in leaves):
            xy=[]
            for real in ('sel_e','tv_e'):
                sp=uq.ports[real]
                xy.extend([(0.,z) for z in sp[4]])
            uq.ports['sel']=('xy',26,'M4',xy,1);uq.order.append('sel')
        for mn,aa in aliases.items():
            # Partition real pin rectangles into exact numeric fragments.
            q=M[mn];rects=v.pin_rects(q,1,{p:sp[1]for p,sp in q.ports.items()})
            # Overlapping aliases are only used by disconnected outputs/returns;
            # one alias per connected physical bit is required below.
            aa={k:val for k,val in aa.items()if k not in('uv','uv_pair','tt_uv')}
            partition_master(q,aa,rects)
    m['buses']=data+control
    m['relay_equal_groups']={}
    m.pop('r21_relays',None)
    # Freeze source pin frames before the allocator wraps the master family.
    def fixed(model,k=1,port_bits=None):return dict(M)
    v.masters=fixed
    selected={i for b,c,n,es in data for i,p in es}
    instmap={i.name:i for i in m['insts']}
    for bid,c,n,es in data:
        for i,p in es:
            q=M[instmap[i].master]
            if p not in q.ports:raise ValueError(f'{bid}: missing actual pin {i}.{p}')
            if q.ports[p][1]!=n:raise ValueError(f'{bid}: {i}.{p} width {q.ports[p][1]} !={n}')
    before=[dict(n=i.name,m=i.master,x=i.x,y=i.y,w=i.w,h=i.h,o=i.orient)for i in m['insts']]
    (a.out/'input.json').write_text(json.dumps(dict(insts=before,buses=data,source_receipts=source_receipts,frames=frames,notes=notes),indent=1)+'\n')
    os.environ.pop('OT_RELAY_SKIP');os.environ['OT_RELAY_GATE']='warn'
    os.environ['OT_RELAY_DUMP']=str(a.out/'allocator_dump.json')
    G._relays(v,m)
    st=m.get('r21_stage_of',{})
    S=lambda name:st.get(name,1)
    prices=[]
    for bid,cl,n,es in data:
        if not re.fullmatch(r'bword_[0-9]+',bid):continue
        pn=es[-1][0];b=int(pn.split('_')[3]);h=int(pn.endswith('_f1'));hb=2*b+h
        if a.mode=='b2':
            upper=max((f'b2_pword_{hb}_l{u}' for u in range(4)),key=S)
            chain=[bid,f'b2_tw_{hb}',upper]
        else:
            chain=[bid]
            if h:chain.append(f'pfrag_{b}_port_tiles_{b}_f1')
            chain.append(f'tw_{b}')
            chain.append(max((f'pword_{b}_l{u}' for u in range(4)),key=S))
        # Every name must exist in the frozen source graph before using default1.
        original={bb[0] for bb in data}
        if any(k not in original for k in chain):raise ValueError(f'price chain missing exact bus {chain}')
        prices.append(dict(bword=bid,halfband=hb,buses=chain,stages=[S(k)for k in chain],transport_hops=sum(S(k)for k in chain)))
    prices.sort(key=lambda x:-x['transport_hops'])
    result=dict(mode=a.mode,status='PARTIAL_REAL_ALLOCATOR_DIAGNOSTIC_NOT_NATIVE_DIE',source_receipts=source_receipts,
                notes=notes,stage_of=st,relays=m.get('r21_relays',{}),
                reduction_transport_paths=prices,
                measured_scope='registered wire hops from bword producer to upper input only; excludes source arithmetic latencies and incomplete native result/control paths',
                omitted='tc/am/rb/LC/new controller and VM source interfaces and other data relay contention')
    (a.out/'result.json').write_text(json.dumps(result,indent=1)+'\n')
    print(json.dumps({k:val for k,val in result.items()if k not in('source_receipts','stage_of')},indent=1))
if __name__=='__main__':main()
