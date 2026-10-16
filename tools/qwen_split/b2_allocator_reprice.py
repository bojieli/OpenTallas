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
    ap.add_argument('--prepare-only',action='store_true')
    ap.add_argument('--compact-selector',action='store_true',help='actual4used selector bits; requires new NL2 s4 source')
    ap.add_argument('--production',action='store_true',help='actual banked halftrain/controller/NB6VM interfaces; still unqualified candidate frames')
    a=ap.parse_args(); NUP=8 if a.production else 4; QW=64 if a.production else 128; RW=192 if a.production else 384;SEL_W=4 if a.compact_selector else 26;SEL='sel4'if a.compact_selector else'sel'
    a.out.mkdir(parents=True,exist_ok=True)
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
    source_receipts=[];frames={};aliases={};notes=[];constant_bindings=[]
    def frame(master,path,w,h,faceof):
        pp=rtl_ports(a.source_root/path,master)
        q=v.Master(master,w,h,7,'NEW b2 source-bound candidate pin frame, unqualified')
        faces={f:[]for f in 'WENS'}
        for p,(n,d)in pp.items():faces[faceof(p)].append((p,n))
        for f,items in faces.items():
            # Real adjacent port/halfband bits must line up by name. RTL order
            # has TY before CW; that order crosses two 2048-bit bundles.
            if master=='qfd_port_half_b2'and f=='S':items.sort(key=lambda z:0 if z[0]=='cw0'else 1)
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
        pm='qfd_port_half_b2';lm='qfd_sp_halfband_lanes_b2_l2'if a.production else'qfd_sp_halfband_lanes';um=('qfd_band_upper_b2_l2_s4'if a.compact_selector else'qfd_band_upper_b2_l2')if a.production else'qfd_band_upper_b2'
        sm='qfd_res_train_half_b2'if a.production else'qfd_res_ser_half_b2'
        frame(pm,'rtl/qwen_split/qfd_port_half_b2.sv',1036.8,2462.4,
              lambda p:'W'if p.startswith('bw')else'S'if p in('cw0','ty')else'N'if p.startswith('ck')or p in('rst_n','rq')else'E')
        frame(lm,'rtl/physical/ot_qwen_halfband_lanes_slots_b2_l2.sv'if a.production else'rtl/physical/ot_qwen_halfband_lanes_slots.sv',881.28,648.,
              lambda p:'N'if p in('tw','ty')else'S'if p in('ck','rst_n')or p.startswith('ck_l')else'E')
        frame(sm,'rtl/qwen_split/qfd_res_train_half_b2.sv'if a.production else'rtl/qwen_split/qfd_res_ser_half_b2.sv',777.6,518.4 if a.production else 324.,
              lambda p:'S'if p=='rq'else'N'if p.startswith('ck')or p=='rst_n'else'E')
        frame(um,('rtl/qwen_split/qfd_band_upper_b2_l2_s4.sv'if a.compact_selector else'rtl/qwen_split/qfd_band_upper_b2_l2.sv')if a.production else'rtl/qwen_split/qfd_band_upper_b2.sv',86.4,205.2 if a.production else 410.4,
              lambda p:'W'if p in('pw','pw_v','lf')else'N'if p in('clk','rst_n')else'E')
        # Exact numeric aliases; no centroid stand-ins for missing pin groups.
        alias(pm,'cw_data','cw0',range(2048))
        for l in range(NUP):
            alias(lm,f'pw_l{l}_d',f'pw_l{l}',range(QW));alias(lm,f'pw_l{l}_v',f'pw_l{l}',[QW])
            alias(lm,f'f_up_l{l}','f_up',[l])
            if a.production:
                alias(lm,f'tt_l{l}_data',f'tt_l{l}',range(RW))
                alias(lm,f'tt_l{l}_use',f'tt_l{l}',[RW]);alias(lm,f'tt_l{l}_v',f'tt_l{l}',[RW+1])
            else:alias(lm,f'tt_l{l}','tt',[128*l+j+512*k for k in range(3)for j in range(128)])
        if not a.production:alias(lm,'tt_uv','tt',[1536,1537])
        for hb in range(6):
            alias(um,f'pw_b{hb}','pw',range(QW*hb,QW*(hb+1)))
            alias(um,f'pv_b{hb}','pw_v',[hb]);alias(um,f'lf_b{hb}','lf',[hb])
        new=[];port_by={};lane_by={};ser_by={}
        for hb in range(6):
            b,h=divmod(hb,2);oldp=by[f'sp_port_tiles_{b}'+('_f1'if h else'')]
            p=copy.copy(oldp);p.master=pm
            flip=by[f'sp_port_tiles_{b}'].orient=='MX'
            p.orient=('R180'if flip else'MY')if h else('MX'if flip else'R0')
            l=copy.copy(by[f'sp_band_lanes_{b}']);l.name=f'sp_halfband_{hb}';l.master=lm;l.w,l.h=881.28,648.
            l.x=p.x+(p.w-l.w)/2;l.y=p.y+p.h+43.2 if flip else p.y-43.2-l.h;l.orient=p.orient
            s=copy.copy(by[f'sp_res_ser_{b}']);s.name=f'sp_halfres_{hb}';s.master=(f'qfd_res_train_half_b2_{hb}'if a.production else sm);s.w,s.h=777.6,518.4 if a.production else 324.
            s.x=p.x+(p.w-s.w)/2;s.y=p.y-86.4-s.h if flip else p.y+p.h+86.4;s.orient=p.orient
            port_by[hb]=p;lane_by[hb]=l;ser_by[hb]=s;new.extend((p,l,s))
        # Wider/taller upper outlines must find real free homes, not overlap peers.
        obs=[i for i in m['insts']if i.name not in targets]
        for l in range(NUP):
            u=copy.copy(by[f'tt_up4_leaf{l%4}']);u.name=f'tt_up4_leaf{l}';u.x+=(l%4)*43.2 if a.production else 0;u.y+=(l//4)*226.8;u.master=um;u.w,u.h=86.4,(205.2 if a.production else 410.4)
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
            if not a.production and any(i in leaves for i,p in es)and not bid.startswith(('pword_','tt_lf','tt_ty')):
                newdata.append((bid,cl,n,es));continue
        for hb in range(6):
            b,h=divmod(hb,2);p,l,s=port_by[hb],lane_by[hb],ser_by[hb]
            newdata.extend([add(f'b2_tw_{hb}',2048,(p.name,'cw_data'),(l.name,'tw')),
                            add(f'b2_ty_{hb}',2048,(l.name,'ty'),(p.name,'ty')),
                            add(f'b2_rq_{hb}',2213,(p.name,'rq'),(s.name,'rq'))])
            for u in range(NUP):
                un=f'tt_up4_leaf{u}'
                newdata.extend([add(f'b2_pword_{hb}_l{u}',QW,(l.name,f'pw_l{u}_d'),(un,f'pw_b{hb}')),
                                add(f'b2_pword_{hb}_v{u}',1,(l.name,f'pw_l{u}_v'),(un,f'pv_b{hb}')),
                                add(f'b2_lf_{hb}_l{u}',1,(l.name,f'f_up_l{u}'),(un,f'lf_b{hb}'))])
        for u in range(NUP):
            newdata.append(add(f'b2_return_l{u}',RW,(f'tt_up4_leaf{u}','tt_ty'),(lane_by[0].name,f'tt_l{u}_data'if a.production else f'tt_l{u}')))
            if a.production:
                newdata.extend([add(f'b2_return_use{u}',1,(f'tt_up4_leaf{u}','tt_use'),(lane_by[0].name,f'tt_l{u}_use')),
                                add(f'b2_return_v{u}',1,(f'tt_up4_leaf{u}','tt_v'),(lane_by[0].name,f'tt_l{u}_v'))])
        if not a.production:
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
                elif i in leaves and a.production:
                    k=int(i.removeprefix('tt_up4_leaf'));ee.extend((f'tt_up4_leaf{u}',pn)for u in range(k,NUP,4))
                elif i in sers:
                    b=int(i.rsplit('_',1)[1]);ee.extend((ser_by[2*b+h].name,'rst_n'if cl=='reset'else(pn if a.production else'ck'))for h in range(2))
                else:ee.append((i,pn))
            cc.append((bid,cl,n,list(dict.fromkeys(ee))))
        control=cc
        # Data tc/am/rb/LC interfaces need NEW controller and VM producers/consumers;
        # deliberately leave them out instead of pricing fictitious source pins.
        notes=['cw valid/fault completeness and central cross-half status checking remain OPEN',
               'tc/am/rb/LC and serializer command paths await actual new controller/VM source interfaces; excluded from partial price',
               'all macro obstacles retained; other data-bus relay reservations excluded',
               'new outlines and pins are explicit candidate grants, not closed views']

        if a.production:
            cm='qfd_tt_ctlm_b2';vm='qfd_sp_vector_memory_b2_partitioned_ro6_pin_e3';im='qfd_res_train_issue_b2'
            wrapper_source='rtl/qwen_split/qfd_res_train_half_b2_wrappers.sv'
            for hb in range(6):
                mn=f'qfd_res_train_half_b2_{hb}'
                wrapper_body=(a.source_root/wrapper_source).read_text().split('module '+mn+'(',1)[1].split('endmodule',1)[0]
                for param,value in (('BAND',hb),('NB',6),('D',2),('MAX_TRAIN',8),('MUT',0)):
                    if not re.search(r'\.'+param+r'\(\s*'+str(value)+r'\s*\)',wrapper_body):raise ValueError(f'{mn} actual {param} identity drift')
                pp=rtl_ports(a.source_root/wrapper_source,mn)
                if pp!=rtl_ports(a.source_root/'rtl/qwen_split/qfd_res_train_half_b2.sv',sm):raise ValueError('halftrain wrapper ABI drift')
                q=copy.deepcopy(M[sm]);q.name=mn;M[mn]=q;frames[mn]=copy.deepcopy(frames[sm])
                source_receipts.append(dict(master=mn,source=wrapper_source,sha256=hashlib.sha256((a.source_root/wrapper_source).read_bytes()).hexdigest(),BAND=hb,ports=pp))
                for k in range(24):alias(mn,f'ck_bank{k}','ck_bank',[k])

            oldcm=by['tt_ctlm'].master;oldvm=by['sp_vector_memory'].master;oldim=by['res_train_issue'].master
            cmold=M[oldcm];vmold=M[oldvm];imold=M[oldim]
            def side(p,old,clock=False):
                if p.startswith(('ck','native_ck','return_ck','read_control_ck','write_ck','relay_ck'))or p in('rst_n','rsi'):return'N'
                if old and p in old.ports and old.ports[p][0]in('face','pins'):return old.ports[p][2]
                return'E'
            def cside(p):
                mm=re.fullmatch(r'(tc|am|lc|rf|mer)([0-5])',p)
                return('E'if int(mm[2])%2 else'W')if mm else side(p,cmold)
            frame(cm,'rtl/qwen_sys/static_schedule_20261014/qfd_tt_ctlm_b2.sv',by['tt_ctlm'].w,by['tt_ctlm'].h,cside)
            frame(vm,'rtl/qwen_sys/vm_nox_20261014/qfd_sp_vector_memory_b2_partitioned_ro6_pin_e3.sv',by['sp_vector_memory'].w,by['sp_vector_memory'].h,
                  lambda p:('S'if re.fullmatch(r'rb[0-5]',p)else side(p,vmold)))
            frame(im,'rtl/qwen_split/qfd_res_train_issue_b2.sv',by['res_train_issue'].w,by['res_train_issue'].h,lambda p:side(p,imold))
            by['tt_ctlm'].master=cm;by['sp_vector_memory'].master=vm;by['res_train_issue'].master=im
            # Preserve every existing real numeric fragment of unchanged ports;
            # controller c0/c1/c2 are now W-side tc0/tc2/tc4 copies.
            for old,newmn in ((oldcm,cm),(oldvm,vm),(oldim,im)):
                for an,(real,idx)in oldjoins.get(old,{}).items():
                    mm=re.fullmatch(r'c([0-2])',real)
                    if old==oldcm and mm:real='tc'+str(2*int(mm[1]))
                    if real in M[newmn].ports:alias(newmn,an,real,idx)
            def map_endpoint(ep):
                i,p=ep
                if i=='tt_ctlm':
                    mm=re.fullmatch(r'c([0-2])',p)
                    if mm:p='tc'+str(2*int(mm[1]))
                return(i,p)
            # Current producer command outputs are real fields; explicitly
            # fan them out here, then replace with the actual registered tree.
            for hb in range(6):
                p,l,r=port_by[hb],lane_by[hb],ser_by[hb]
                newdata.extend([
                  add(f'b2_tc_{hb}',341,('tt_ctlm',f'tc{hb}'),(p.name,'tc')),
                  add(f'b2_am_{hb}',52,(p.name,'am'),('tt_ctlm',f'am{hb}')),
                  add(f'b2_lc_{hb}',26,('tt_ctlm',f'lc{hb}'),(l.name,'c')),
                  add(f'b2_rb_{hb}',551,(r.name,'rb'),('sp_vector_memory',f'rb{hb}')),
                  add(f'b2_rf_{hb}',1,(r.name,'fault'),('tt_ctlm',f'rf{hb}'))])
            for u in range(NUP):
                alias(cm,f'uf_l{u}','uf',[u])
                newdata.append(add(f'b2_uf{u}',1,(f'tt_up4_leaf{u}','fault'),('tt_ctlm',f'uf_l{u}')))
            if a.compact_selector:alias(cm,SEL,'sel',[10,11,23,24])
            newdata.append(('b2_selector','tree_spine',SEL_W,[('tt_ctlm',SEL)]+[(f'tt_up4_leaf{u}',SEL)for u in range(NUP)]))
            from qwen_split.command_distribution import FIELDS
            for f,n in FIELDS:
                newdata.append((f'b2_rsi_{f}','spine_local',n,[('res_train_issue',f)]+[(ser_by[hb].name,f)for hb in range(6)]))
            # Actual independent registered producer copies preserve full
            # TC/IB outputs, eliminating their old multi-sink tapped nets.
            for f,n in (('me_go',1),('me_tiles',18),('me_ts',24),('me_split',4),('me_oen',1),('tag_v',1),('tag_last',1)):
                newdata.append(add(f'b2_source_{f}',n,('tt_ctlm','rsi_'+f),('res_train_issue',f)))
            m.setdefault('relay_equal_groups',{})['b2_source_me']=[f'b2_source_{f}'for f in ('me_go','me_tiles','me_ts','me_split','me_oen')]
            m.setdefault('relay_equal_groups',{})['b2_source_tag']=['b2_source_tag_v','b2_source_tag_last']
            # Status compares actual six native valid/fault producers; it is
            # a diagnostic fault producer, never a scheduler or data substitute.
            st=copy.copy(by['tt_ctlm']);st.name='b2_word_status';st.master='qfd_b2_word_status';st.w=st.h=43.2;st.orient='R0'
            st.x=round(by['tt_ctlm'].x-64.8,3);st.y=round(by['tt_ctlm'].y+by['tt_ctlm'].h/2,3)
            if any(i.x<st.x+st.w and i.x+i.w>st.x and i.y<st.y+st.h and i.y+i.h>st.y for i in m['insts']):
                raise ValueError('actual status candidate home overlaps; assign a real free home')
            m['insts'].append(st)
            frame(st.master,'rtl/qwen_split/qfd_b2_word_status.sv',43.2,43.2,
                  lambda p:'W'if p in('word_v','word_fault','result_v')else'N'if p in('ck','rst_n')else'E')
            for hb in range(6):
                alias(pm,'cw_valid','cw0',[2048]);alias(pm,'cw_fault','cw0',[2049])
                alias(st.master,f'valid{hb}','word_v',[hb]);alias(st.master,f'fault{hb}','word_fault',[hb]);alias(st.master,f'result{hb}','result_v',[hb])
                newdata.extend([add(f'b2_status_v{hb}',1,(port_by[hb].name,'cw_valid'),(st.name,f'valid{hb}')),
                                add(f'b2_status_f{hb}',1,(port_by[hb].name,'cw_fault'),(st.name,f'fault{hb}'))])
            # Actual dedicated output is captured alongside restored RQ; it is not a second net on RQ[2212].
            for hb in range(6):newdata.append(add(f'b2_status_result{hb}',1,(port_by[hb].name,'result_status_v'),(st.name,f'result{hb}')))
            m.setdefault('relay_equal_groups',{})['b2_result_status']=[f'b2_status_result{hb}'for hb in range(6)]
            newdata.append(add('b2_status_fault',1,(st.name,'fault'),('tt_ctlm','b2_status_fault')))
            m.setdefault('relay_equal_groups',{})['b2_status']=[f'b2_status_{kind}{hb}'for hb in range(6)for kind in('v','f')]
            status_clock_added=status_reset_added=False
            cc=[]
            for bid,cl,n,es in control:
                ee=list(es)
                if cl=='clock_trunk'and('tt_ctlm','ck_tree')in es:
                    ee.append((st.name,'ck'));status_clock_added=True
                if cl=='reset'and any(i=='tt_ctlm'for i,p in es):
                    ee.append((st.name,'rst_n'));status_reset_added=True
                cc.append((bid,cl,n,ee))
            if not(status_clock_added and status_reset_added):raise ValueError('status requires actual controller clock/reset source')
            control=cc
            notes=['actual banked halftrain/controller/NB6VM source ABI, NEW candidate pin/outline grants only',
                   'all macro obstacles retained; other data-bus relay reservations excluded',
                   'native sourcecopy/fanout/AM arithmetic stage calibration and actual leaf clocks remain OPEN']
            # Old sources of LD/ME enable/faults that are not retired targets
            # remain outside this subsystem price; enumerate them explicitly.
            notes.append('NEW native VM leaf clock XY/insertion witness OPEN; provisional boundary clock pin assignment is not timing evidence')
            # Every actual VM/controller/issuer clock bit gets an explicit
            # endpoint on its former source clock net, never an old448 alias.
            cc=[];expanded_vectors=set()
            for bid,cl,n,es in control:
                ee=[]
                for i,p in es:
                    if cl=='clock_trunk'and i in('tt_ctlm','sp_vector_memory','res_train_issue'):
                        mn={'tt_ctlm':cm,'sp_vector_memory':vm,'res_train_issue':im}[i]
                        if p in M[mn].ports:ee.append((i,p))
                        if p=='ck'and i not in expanded_vectors:
                            expanded_vectors.add(i)
                            for cp,sp in list(M[mn].ports.items()):
                                if sp[1]==1 or not cp.startswith(('native_ck','return_ck','read_control_ck','write_ck','relay_ck')):continue
                                for k in range(sp[1]):
                                    apn=f'{cp}_entry{k}';alias(mn,apn,cp,[k]);ee.append((i,apn))
                    else:ee.append(map_endpoint((i,p)))
                cc.append((bid,cl,n,list(dict.fromkeys(ee))))
            control=cc
        if a.production:
            for hb in range(6):
                constant_bindings.append(dict(instance=port_by[hb].name,port='hb',bits=3,value=hb,source='captured physical halfband identity'))
                constant_bindings.append(dict(instance=lane_by[hb].name,port='b0',bits=1,value=int(hb==0),source='only HB0 owns native tree return'))
                for u in range(NUP):
                    if hb:constant_bindings.append(dict(instance=lane_by[hb].name,port=f'tt_l{u}',bits=194,value=0,source='source b0=0 ignores upper return'))
        data=newdata
        # Existing selector bundle is a wire concatenation of two distinct
        # source ports, not a new unregistered control input.
        uq=M[um]
        if any(p==SEL for bid,cl,n,es in data for i,p in es if i in leaves):
            xy=[]
            for real in ('sel_e','tv_e'):
                sp=uq.ports[real]
                xy.extend([((uq.w-.096)if sp[2]=='E'else .096,z)for z in sp[4]])
            uq.ports[SEL]=('xy',SEL_W,'M4',xy,1);uq.order.append(SEL)
            m.setdefault('port_split',{}).setdefault(um,{})[SEL]=[['sel_e',SEL_W//2],['tv_e',SEL_W//2]]
        for mn,aa in aliases.items():
            # Partition real pin rectangles into exact numeric fragments.
            q=M[mn];rects=v.pin_rects(q,1,{p:sp[1]for p,sp in q.ports.items()})
            # Overlapping aliases are only used by disconnected outputs/returns;
            # one alias per connected physical bit is required below.
            active={p for bid,cl,n,es in data+control for i,p in es if next((q.master for q in m['insts']if q.name==i),None)==mn}
            aa={k:val for k,val in aa.items()if k not in('uv','uv_pair','tt_uv')and k in active}
            partition_master(q,aa,rects)
    m['buses']=data+control
    if a.mode=='b2'and a.production:
        from qwen_split.command_distribution import apply as distribute,install_master as install_fork
        distribute(m,[ser_by[hb].name for hb in range(6)])
        distribute(m,[f'tt_up4_leaf{u}'for u in range(NUP)],issuer='tt_ctlm',fielddefs=((SEL,SEL_W),),master=f'qfd_static_selector_fork{SEL_W}',source_file=f'rtl/qwen_split/qfd_static_selector_fork{SEL_W}.sv',prefix='selector',clock_port='ck_tree',reset_port='rsi')
        install_fork(M,m,v.Master,v.pin_rects)
        data=[bb for bb in m['buses']if bb[1]not in('clock_trunk','reset')]
    original_bids={b[0] for b in m['buses']}
    groups={k:list(bs) for k,bs in m.get('relay_equal_groups',{}).items()
            if set(bs)<=original_bids}
    if a.mode=='b2':
        for hb in range(6):
            groups[f'b2_word_{hb}']=[f'b2_pword_{hb}_{kind}{u}'for u in range(NUP)for kind in ('l','v')]
        groups['b2_return']=([f'b2_return_{kind}{u}'for u in range(NUP)for kind in('l','use','v')]if a.production else[f'b2_return_l{u}'for u in range(4)]+['b2_return_use','b2_return_v'])
        if a.production:
            # Homogeneous restored source stations produce each six-half event
            # together. Preserve their relative ages through the allocator.
            for family in ('tc','am','lc','rq','rb'):
                groups['b2_'+family]=[f'b2_{family}_{hb}'for hb in range(6)]
    m['relay_equal_groups']=groups
    m.pop('r21_relays',None)
    # Freeze source pin frames before the allocator wraps the master family.
    def fixed(model,k=1,port_bits=None):return dict(M)
    v.masters=fixed
    selected={i for b,c,n,es in data for i,p in es}
    instmap={i.name:i for i in m['insts']}
    for bid,c,n,es in data+control:
        for i,p in es:
            q=M[instmap[i].master]
            if p not in q.ports:raise ValueError(f'{bid}: missing actual pin {i}.{p}')
            if q.ports[p][1]!=n:raise ValueError(f'{bid}: {i}.{p} width {q.ports[p][1]} !={n}')
    # Audit source ABI bits rather than treating a valid referenced endpoint as
    # complete composition. Missing straps/ties/clocks stay explicit OPEN.
    receipts_by={r['master']:r for r in source_receipts}
    input_coverage=[]
    allbus=data+control
    for inst in m['insts']:
        rec=receipts_by.get(inst.master)
        if not rec:continue
        actual=rec['ports'];covered={p:set()for p,(n,d)in actual.items()if d=='input'}
        for bid,cl,n,es in allbus:
            for name,p in es:
                if name!=inst.name:continue
                if p in aliases.get(inst.master,{}):real,idx=aliases[inst.master][p]
                elif p in('sel','sel4')and 'sel_e'in actual:
                    for rp in ('sel_e','tv_e'):covered[rp].update(range(actual[rp][0]))
                    continue
                elif p in actual:real,idx=p,range(actual[p][0])
                else:continue
                if real in covered:covered[real].update(idx)
        for tie in constant_bindings:
            if tie['instance']==inst.name:covered[tie['port']].update(range(tie['bits']))
        missing={p:sorted(set(range(actual[p][0]))-got)for p,got in covered.items()if len(got)!=actual[p][0]}
        input_coverage.append(dict(instance=inst.name,master=inst.master,
            total_input_bits=sum(actual[p][0]for p in covered),connected_input_bits=sum(map(len,covered.values())),
            unassigned_input_bits=missing,status='OPEN'if missing else'CONNECTED_SOURCE_ABI_NOT_PHYSICAL_PROOF'))
    local_pin_audit=[]
    def source_pin_xy(inst,port,k):
        fr=frames[inst.master];sp=fr['ports'][port];face,pos=sp[2],sp[4][k]
        x,y=(pos,fr['h']-.096)if face=='N'else(pos,.096)if face=='S'else(.096,pos)if face=='W'else(fr['w']-.096,pos)
        if inst.orient in ('MY','R180'):x=fr['w']-x
        if inst.orient in ('MX','R180'):y=fr['h']-y
        return inst.x+x,inst.y+y
    if a.mode=='b2':
        for hb in range(6):
            for name,src,sp,dst,dp,n in (('tw',port_by[hb],'cw0',lane_by[hb],'tw',2048),('ty',lane_by[hb],'ty',port_by[hb],'ty',2048),('rq',port_by[hb],'rq',ser_by[hb],'rq',2213)):
                ds=[];dx=[]
                for k in range(n):
                    ax,ay=source_pin_xy(src,sp,k);bx,by=source_pin_xy(dst,dp,k)
                    ds.append(abs(ax-bx)+abs(ay-by));dx.append(abs(ax-bx))
                local_pin_audit.append(dict(halfband=hb,bus=name,bits=n,min_L1_um=min(ds),max_L1_um=max(ds),max_dx_um=max(dx),source_pin_grant_only=True))
                if name in ('tw','ty')and max(ds)>44:raise ValueError(f'actual named {name} bits cross local contact channel HB{hb}: {max(ds)}um')
    before=[dict(n=i.name,m=i.master,x=i.x,y=i.y,w=i.w,h=i.h,o=i.orient)for i in m['insts']]
    (a.out/'input.json').write_text(json.dumps(dict(insts=before,buses=data,control_buses=control,source_receipts=source_receipts,frames=frames,notes=notes,command_distribution=m.get('command_distribution'),distribution_trees=m.get('distribution_trees'),equal_groups=groups,input_coverage=input_coverage,constant_bindings=constant_bindings,local_pin_audit=local_pin_audit),indent=1)+'\n')
    if a.prepare_only:
        print(json.dumps(dict(status='SOURCE_GRAPH_PREPARED_UNQUALIFIED',instances=len(before),data_buses=len(data),equal_groups=len(groups),production=a.production)))
        return
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
            upper=max((f'b2_pword_{hb}_l{u}' for u in range(NUP)),key=S)
            chain=[bid,f'b2_tw_{hb}',upper]
        else:
            chain=[bid]
            if h:chain.append(f'pfrag_{b}_port_tiles_{b}_f1')
            chain.append(f'tw_{b}')
            chain.append(max((f'pword_{b}_l{u}' for u in range(NUP)),key=S))
        # Every name must exist in the frozen source graph before using default1.
        original={bb[0] for bb in data}
        if any(k not in original for k in chain):raise ValueError(f'price chain missing exact bus {chain}')
        prices.append(dict(bword=bid,halfband=hb,buses=chain,stages=[S(k)for k in chain],transport_hops=sum(S(k)for k in chain)))
    prices.sort(key=lambda x:-x['transport_hops'])
    distribution_ages={}
    for prefix,rec in m.get('distribution_trees',{}).items():
        paths={}
        for sink in rec['sinks']:
            for field,n in rec['fields']:
                endpoint=(sink,field);path=[]
                while endpoint[0]!=('res_train_issue'if prefix=='command'else'tt_ctlm'):
                    incoming=[b for b in data if tuple(b[3][-1])==endpoint]
                    if len(incoming)!=1:raise ValueError(f'nonunique actual registered path {endpoint}')
                    b=incoming[0];path.insert(0,b[0]);src=tuple(b[3][0])
                    if src[0].startswith(prefix+'_fork_'):endpoint=(src[0],'a_'+field)
                    else:endpoint=src
                paths[sink+'.'+field]=dict(buses=path,stages=[S(b)for b in path],transport_capture_edges=sum(S(b)for b in path),additional_external_register_edges=sum(S(b)for b in path)-1)
        distribution_ages[prefix]=paths
    round_trip=[]
    if a.production:
        R=max(S(f'b2_return_{kind}{u}')-1 for u in range(NUP)for kind in('l','use','v'))
        for hb in range(6):
            F=max(S(f'b2_pword_{hb}_{kind}{u}')-1 for u in range(NUP)for kind in('l','v'))
            total=F+R
            round_trip.append(dict(halfband=hb,forward_external_edges=F,actual_return_external_edges=R if hb==0 else None,
                HB0_roundtrip_edges=total if hb==0 else None,parent_lnk=total//2 if hb==0 and total%2==0 else None,
                pending='real pad edge required before integralL'if hb==0 and total%2 else'nonreturn half postscale/capture calibration OPEN'if hb else'check L<=54 and selector at LC+3+F; no normal-operation proof'))
    result=dict(mode=a.mode,production_interfaces=a.production,status='PARTIAL_REAL_ALLOCATOR_DIAGNOSTIC_NOT_NATIVE_DIE',source_receipts=source_receipts,
                notes=notes,equal_groups=groups,stage_of=st,distribution_ages=distribution_ages,round_trip_contract=round_trip,input_coverage=input_coverage,local_pin_audit=local_pin_audit,relays=m.get('r21_relays',{}),
                unequal_groups={k:{bb:st.get(bb,1)for bb in bs}for k,bs in groups.items()if len({st.get(bb,1)for bb in bs})!=1},
                reduction_transport_paths=prices,
                measured_scope='registered wire hops from bword producer to upper input only; excludes source arithmetic latencies and incomplete native result/control paths',
                omitted=('other data relay contention, source arithmetic/sourcecopy/AM calibration, actual leaf clock homes and physical/native qualification'if a.production else'tc/am/rb/LC/new controller and VM source interfaces and other data relay contention'))
    (a.out/'result.json').write_text(json.dumps(result,indent=1)+'\n')
    print(json.dumps({k:val for k,val in result.items()if k not in('source_receipts','stage_of')},indent=1))
if __name__=='__main__':main()
