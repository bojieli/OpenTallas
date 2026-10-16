"""Source-bound b2 topology shared by die emission and allocator diagnostics.

New frames are candidates. This module establishes source connectivity only;
physical timing and the compiler round-trip calibration are separate gates.
"""
import copy, hashlib, re
from pathlib import Path

def prepare(v, m, source_root, *, production=True, mode='b2', full_graph=False, compact_selector=False):
    from qwen_split.source_pin_plan import rtl_ports, snap
    from qwen_split.direct_up4 import partition_master
    source_root=Path(source_root)
    NUP=8 if production else 4
    QW=64 if production else 128
    RW=192 if production else 384
    SEL_W=4 if compact_selector else 26
    SEL="sel4"if compact_selector else"sel"
    original_buses=copy.deepcopy(m['buses'])
    M=v.masters(m,1);by={i.name:i for i in m['insts']}
    oldjoins=copy.deepcopy(m.get('port_join',{}))
    ports={f'sp_port_tiles_{b}{s}'for b in range(3)for s in ('','_f1')}
    lanes={f'sp_band_lanes_{b}'for b in range(3)}
    sers={f'sp_res_ser_{b}'for b in range(3)}
    leaves={f'tt_up4_leaf{k}'for k in range(4)}
    targets=ports|lanes|sers|leaves
    if full_graph:targets.add("up4_sel_station")
    # Clock and reset topology stays complete; data allocation is subsystem-only.
    data=[b for b in m['buses']if b[1] not in ('clock_trunk','reset')and any(i in targets for i,p in b[3])]
    control=[b for b in m['buses']if b[1]in('clock_trunk','reset')]
    source_receipts=[];frames={};aliases={};notes=[];constant_bindings=[]
    def frame(master,path,w,h,faceof):
        pp=rtl_ports(source_root/path,master)
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
        source_receipts.append(dict(master=master,source=path,sha256=hashlib.sha256((source_root/path).read_bytes()).hexdigest(),ports=pp))
        frames[master]=dict(w=w,h=h,ports=copy.deepcopy(q.ports))
        return q
    def alias(master,name,real,indices):aliases.setdefault(master,{})[name]=(real,list(indices));return name
    def add(name,n,src,dst):return(name,'tree_spine',n,[src,dst])
    if mode=='b2':
        pm='qfd_port_half_b2';lm='qfd_sp_halfband_lanes_b2_l2'if production else'qfd_sp_halfband_lanes';um=('qfd_band_upper_b2_l2_s4'if compact_selector else'qfd_band_upper_b2_l2')if production else'qfd_band_upper_b2'
        sm='qfd_res_train_half_b2'if production else'qfd_res_ser_half_b2'
        frame(pm,'rtl/qwen_split/qfd_port_half_b2.sv',1036.8,2462.4,
              lambda p:'W'if p.startswith('bw')else'S'if p in('cw0','ty')else'N'if p.startswith('ck')or p in('rst_n','rq')else'E')
        frame(lm,'rtl/physical/ot_qwen_halfband_lanes_slots_b2_l2.sv'if production else'rtl/physical/ot_qwen_halfband_lanes_slots.sv',881.28,648.,
              lambda p:'N'if p in('tw','ty')else'S'if p in('ck','rst_n')or p.startswith('ck_l')else'E')
        frame(sm,'rtl/qwen_split/qfd_res_train_half_b2.sv'if production else'rtl/qwen_split/qfd_res_ser_half_b2.sv',777.6,518.4 if production else 324.,
              lambda p:'S'if p=='rq'else'N'if p.startswith('ck')or p=='rst_n'else'E')
        frame(um,('rtl/qwen_split/qfd_band_upper_b2_l2_s4.sv'if compact_selector else'rtl/qwen_split/qfd_band_upper_b2_l2.sv')if production else'rtl/qwen_split/qfd_band_upper_b2.sv',86.4,205.2 if production else 410.4,
              lambda p:'W'if p in('pw','pw_v','lf')else'N'if p in('clk','rst_n')else'E')
        if production:
            # Q-B2 10-16: a CLOSED upper view (qfd_band_upper_b2_l2_s4 s4r2) is the physical truth: redraw the die
            # master exactly as that abstract (outline + every pin), as bind_real will bind it.
            from types import SimpleNamespace
            from qwen_split.closed_view import view_dir,install_master as view_install
            if view_dir(um) is not None:
                upath=('rtl/qwen_split/qfd_band_upper_b2_l2_s4.sv'if compact_selector else'rtl/qwen_split/qfd_band_upper_b2_l2.sv')
                rec_=view_install(M,m,v.Master,SimpleNamespace(name=um,w=86.4,h=205.2),um,rtl_ports(source_root/upath,um),
                                  partition_master,note='closed upper view')
                frames[um]=dict(w=86.4,h=205.2,ports=copy.deepcopy(M[um].ports),view=rec_['view'])
                notes.append(f'{um}: die frame = closed view {rec_["view"]}')
        # Exact numeric aliases; no centroid stand-ins for missing pin groups.
        alias(pm,'cw_data','cw0',range(2048))
        for l in range(NUP):
            alias(lm,f'pw_l{l}_d',f'pw_l{l}',range(QW));alias(lm,f'pw_l{l}_v',f'pw_l{l}',[QW])
            alias(lm,f'f_up_l{l}','f_up',[l])
            if production:
                alias(lm,f'tt_l{l}_data',f'tt_l{l}',range(RW))
                alias(lm,f'tt_l{l}_use',f'tt_l{l}',[RW]);alias(lm,f'tt_l{l}_v',f'tt_l{l}',[RW+1])
            else:alias(lm,f'tt_l{l}','tt',[128*l+j+512*k for k in range(3)for j in range(128)])
        if not production:alias(lm,'tt_uv','tt',[1536,1537])
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
            s=copy.copy(by[f'sp_res_ser_{b}']);s.name=f'sp_halfres_{hb}';s.master=(f'qfd_res_train_half_b2_{hb}'if production else sm);s.w,s.h=777.6,518.4 if production else 324.
            s.x=p.x+(p.w-s.w)/2;s.y=p.y-86.4-s.h if flip else p.y+p.h+86.4;s.orient=p.orient
            port_by[hb]=p;lane_by[hb]=l;ser_by[hb]=s;new.extend((p,l,s))
        # Wider/taller upper outlines must find real free homes, not overlap peers.
        obs=[i for i in m['insts']if i.name not in targets]
        for l in range(NUP):
            u=copy.copy(by[f'tt_up4_leaf{l%4}']);u.name=f'tt_up4_leaf{l}';u.x+=(l%4)*43.2;u.y+=(l//4)*226.8;u.master=um;u.w,u.h=86.4,(205.2 if production else 410.4)
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
            if not production and any(i in leaves for i,p in es)and not bid.startswith(('pword_','tt_lf','tt_ty')):
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
            newdata.append(add(f'b2_return_l{u}',RW,(f'tt_up4_leaf{u}','tt_ty'),(lane_by[0].name,f'tt_l{u}_data'if production else f'tt_l{u}')))
            if production:
                newdata.extend([add(f'b2_return_use{u}',1,(f'tt_up4_leaf{u}','tt_use'),(lane_by[0].name,f'tt_l{u}_use')),
                                add(f'b2_return_v{u}',1,(f'tt_up4_leaf{u}','tt_v'),(lane_by[0].name,f'tt_l{u}_v'))])
        if not production:
            newdata.extend([add('b2_return_use',1,('tt_up4_leaf0','tt_use'),(lane_by[0].name,'tt_use_alias')),
                            add('b2_return_v',1,('tt_up4_leaf0','tt_v'),(lane_by[0].name,'tt_v_alias'))])
            alias(lm,'tt_use_alias','tt',[1536]);alias(lm,'tt_v_alias','tt',[1537])
        m['insts']=[i for i in m['insts']if i.name not in targets]+new
        cc=[]
        for bid,cl,n,es in control:
            ee=[]
            for i,pn in es:
                if full_graph and i=='up4_sel_station':continue
                if i in lanes:
                    b=int(i.rsplit('_',1)[1]);ee.extend((lane_by[2*b+h].name,pn)for h in range(2))
                elif i in leaves and production:
                    k=int(i.removeprefix('tt_up4_leaf'));ee.extend((f'tt_up4_leaf{u}',pn)for u in range(k,NUP,4))
                elif i in sers:
                    b=int(i.rsplit('_',1)[1]);ee.extend((ser_by[2*b+h].name,'rst_n'if cl=='reset'else(pn if production else'ck'))for h in range(2))
                else:ee.append((i,pn))
            cc.append((bid,cl,n,list(dict.fromkeys(ee))))
        control=cc
        # Data tc/am/rb/LC interfaces need NEW controller and VM producers/consumers;
        # deliberately leave them out instead of pricing fictitious source pins.
        notes=['cw valid/fault completeness and central cross-half status checking remain OPEN',
               'tc/am/rb/LC and serializer command paths await actual new controller/VM source interfaces; excluded from partial price',
               'all macro obstacles retained; other data-bus relay reservations excluded',
               'new outlines and pins are explicit candidate grants, not closed views']

        if production:
            cm='qfd_tt_ctlm_b2';vm='qfd_sp_vector_memory_b2_partitioned_ro6_pin_e3';im='qfd_res_train_issue_b2'
            wrapper_source='rtl/qwen_split/qfd_res_train_half_b2_wrappers.sv'
            for hb in range(6):
                mn=f'qfd_res_train_half_b2_{hb}'
                wrapper_body=(source_root/wrapper_source).read_text().split('module '+mn+'(',1)[1].split('endmodule',1)[0]
                for param,value in (('BAND',hb),('NB',6),('D',2),('MAX_TRAIN',8),('MUT',0)):
                    if not re.search(r'\.'+param+r'\(\s*'+str(value)+r'\s*\)',wrapper_body):raise ValueError(f'{mn} actual {param} identity drift')
                pp=rtl_ports(source_root/wrapper_source,mn)
                if pp!=rtl_ports(source_root/'rtl/qwen_split/qfd_res_train_half_b2.sv',sm):raise ValueError('halftrain wrapper ABI drift')
                q=copy.deepcopy(M[sm]);q.name=mn;M[mn]=q;frames[mn]=copy.deepcopy(frames[sm])
                source_receipts.append(dict(master=mn,source=wrapper_source,sha256=hashlib.sha256((source_root/wrapper_source).read_bytes()).hexdigest(),BAND=hb,ports=pp))
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
            if compact_selector:
                alias(cm,SEL,'sel',[10,11,23,24])
                # Only bits 10/11/23/24 have mapped NL2 consumers. The other 22 bits of the
                # actual controller OUTPUT stay unloaded open nets (writer), never fake ports.
                cport=next(r for r in source_receipts if r['master']==cm)['ports'].get('sel')
                if tuple(cport or ())!=(26,'output'):raise ValueError(f'{cm}.sel must be the actual 26-bit output, got {cport}')
                m.setdefault('port_join_open_outputs',{}).setdefault(cm,{})['sel']=26
            newdata.append(('b2_selector','tree_spine',SEL_W,[('tt_ctlm',SEL)]+[(f'tt_up4_leaf{u}',SEL)for u in range(NUP)]))
            from qwen_split.command_distribution import FIELDS
            for f,n in FIELDS:
                newdata.append((f'b2_rsi_{f}','spine_local',n,[('res_train_issue',f)]+[(ser_by[hb].name,f)for hb in range(6)]))
            # Actual independent registered producer copies preserve full
            # TC/IB outputs, eliminating their old multi-sink tapped nets.
            for f,n in (('me_go',1),('me_tiles',18),('me_ts',24),('me_split',4),('me_oen',1),('tag_v',1),('tag_last',1)):
                newdata.append(add(f'b2_source_{f}',n,('tt_ctlm','rsi_'+f),('res_train_issue',f)))
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
        if production:
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
        if full_graph:
            if not production or mode!='b2':raise ValueError('full graph requires production b2 source')
            data,preservation=restore_unrelated_buses(original_buses,data,targets,map_endpoint)
            m['b2_bus_preservation']=preservation
            audit_preservation(original_buses,data+control,targets,map_endpoint)
        # Netlist and LEF writers must reconstruct actual numeric RTL ports;
        # the allocator's synthetic fragments are never new source ports.
        for mn,aa in aliases.items():
            m.setdefault('port_join',{}).setdefault(mn,{}).update(aa)
        if production:
            m.setdefault('port_split',{}).setdefault(um,{})[SEL]=[('sel_e',SEL_W//2),('tv_e',SEL_W//2)]
        for mn,aa in aliases.items():
            # Partition real pin rectangles into exact numeric fragments.
            q=M[mn];rects=v.pin_rects(q,1,{p:sp[1]for p,sp in q.ports.items()})
            # Overlapping aliases are only used by disconnected outputs/returns;
            # one alias per connected physical bit is required below.
            active={p for bid,cl,n,es in data+control for i,p in es if next((q.master for q in m['insts']if q.name==i),None)==mn}
            aa={k:val for k,val in aa.items()if k not in('uv','uv_pair','tt_uv')and k in active}
            partition_master(q,aa,rects)
    m['buses']=data+control
    if mode=='b2'and production:
        from qwen_split.command_distribution import apply as distribute,install_master as install_fork
        distribute(m,[ser_by[hb].name for hb in range(6)])
        distribute(m,[f'tt_up4_leaf{u}'for u in range(NUP)],issuer='tt_ctlm',fielddefs=((SEL,SEL_W),),master=f'qfd_static_selector_fork{SEL_W}',source_file=f'rtl/qwen_split/qfd_static_selector_fork{SEL_W}.sv',prefix='selector',clock_port='ck_tree',reset_port='rsi')
        install_fork(M,m,v.Master,v.pin_rects)
        for rec in m.get('distribution_trees',{}).values():
            source_receipts.append(dict(master=rec['master'],source=rec['source'],
                sha256=hashlib.sha256((source_root/rec['source']).read_bytes()).hexdigest(),
                ports=rtl_ports(source_root/rec['source'],rec['master'])))
        data=[bb for bb in m['buses']if bb[1]not in('clock_trunk','reset')]
        control=[bb for bb in m['buses']if bb[1]in('clock_trunk','reset')]
    if full_graph:audit_control_preservation(original_buses,m['buses'],targets)
    original_bids={b[0] for b in m['buses']}
    groups={k:list(bs) for k,bs in m.get('relay_equal_groups',{}).items()
            if set(bs)<=original_bids}
    if mode=='b2':
        for hb in range(6):
            groups[f'b2_word_{hb}']=[f'b2_pword_{hb}_{kind}{u}'for u in range(NUP)for kind in ('l','v')]
        groups['b2_return']=([f'b2_return_{kind}{u}'for u in range(NUP)for kind in('l','use','v')]if production else[f'b2_return_l{u}'for u in range(4)]+['b2_return_use','b2_return_v'])
        if production:
            # Homogeneous restored source stations produce each six-half event
            # together. Preserve their relative ages through the allocator.
            for family in ('tc','am','lc','rq','rb'):
                groups['b2_'+family]=[f'b2_{family}_{hb}'for hb in range(6)]
            groups['b2_source_me']=[f'b2_source_{p}'for p in ('me_go','me_tiles','me_ts','me_split','me_oen')]
            groups['b2_source_tag']=['b2_source_tag_v','b2_source_tag_last']
    m['relay_equal_groups']=groups
    m.pop('r21_relays',None)
    if full_graph:
        notes=[n for n in notes if 'other data-bus relay reservations excluded'not in n]
        notes.append('all unrelated data/control buses retained; actual full-graph allocator and compiled phase proof remain separate gates')
        live={i.name for i in m['insts']}
        # Modify the captured ties list in place: the generator writer holds it.
        m.setdefault('ties',[])[:]=[t for t in m.get('ties',[])if t[0]in live and t[0]not in targets]
        m['ties'].extend((t['instance'],t['port'],t['bits'],t['value'])for t in constant_bindings)
        m['b2_source_receipts']=source_receipts
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
                if p in m.get('port_join',{}).get(inst.master,{}):real,idx=m['port_join'][inst.master][p]
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
    if mode=='b2':
        for hb in range(6):
            for name,src,sp,dst,dp,n in (('tw',port_by[hb],'cw0',lane_by[hb],'tw',2048),('ty',lane_by[hb],'ty',port_by[hb],'ty',2048),('rq',port_by[hb],'rq',ser_by[hb],'rq',2213)):
                ds=[];dx=[]
                for k in range(n):
                    ax,ay=source_pin_xy(src,sp,k);bx,by=source_pin_xy(dst,dp,k)
                    ds.append(abs(ax-bx)+abs(ay-by));dx.append(abs(ax-bx))
                local_pin_audit.append(dict(halfband=hb,bus=name,bits=n,min_L1_um=min(ds),max_L1_um=max(ds),max_dx_um=max(dx),source_pin_grant_only=True))
                if name in ('tw','ty')and max(ds)>44:raise ValueError(f'actual named {name} bits cross local contact channel HB{hb}: {max(ds)}um')
    return dict(M=M,data=data,control=control,source_receipts=source_receipts,
                frames=frames,notes=notes,constant_bindings=constant_bindings,
                groups=groups,input_coverage=input_coverage,local_pin_audit=local_pin_audit)

# These inputs move from shared old-controller taps to independent registered
# source copies. Only these endpoint removals are authorized by the b2 source.
ISSUER_COPIES=frozenset(('me_go','me_tiles','me_ts','me_split','me_oen','tag_v','tag_last'))

def restore_unrelated_buses(original, replacement, targets, endpoint_map=lambda x:x):
    """Keep every unrelated bus; trim only the seven explicitly replaced taps.

    A bus with an unclassified retired endpoint is handled by the caller's
    target replacement. All other buses retain their name, class, width, order,
    driver and consumers, except the seven source-copy consumers above.
    """
    kept=[];removed_taps=[]
    for bid,cl,n,eps in original:
        if cl in ('clock_trunk','reset') or any(i in targets for i,p in eps):
            continue
        ee=[]
        for ep in eps:
            if ep[0]=='res_train_issue'and ep[1]in ISSUER_COPIES:
                removed_taps.append((bid,ep));continue
            ee.append(endpoint_map(ep))
        if not ee or ee[0]!=endpoint_map(eps[0]):
            raise ValueError(f'{bid}: cannot remove an unrelated driver')
        if len(ee)<2 and any(b==bid for b,e in removed_taps):
            # Every former consumer moved to its registered source copy.
            continue
        kept.append((bid,cl,n,ee))
    ids={b[0]for b in replacement}
    if len(ids)!=len(replacement):raise ValueError('duplicate b2 replacement bus ID')
    clashes=ids&{b[0]for b in kept}
    if clashes:raise ValueError(f'b2 overwrote unrelated buses {sorted(clashes)}')
    return kept+replacement,dict(unrelated_buses=len(kept),replaced_source_taps=removed_taps)


def audit_preservation(original, final, targets, endpoint_map=lambda x:x):
    expected,_=restore_unrelated_buses(original,[],targets,endpoint_map)
    by={b[0]:b for b in final}
    missing=[b[0]for b in expected if by.get(b[0])!=b]
    if missing:raise ValueError(f'b2 changed or dropped unrelated buses: {missing[:12]}')
    return len(expected)


def bind_changed_sources(die_v, receipts, source_root):
    """Check emitted source instances at actual RTL widths, with no stub fallback."""
    from die_port_bind import parse_die, expr_bits
    from qwen_split.source_pin_plan import rtl_ports
    nets,_,_,insts=parse_die(die_v)
    contracts={}
    for r in receipts:
        p=Path(source_root)/r['source']
        if hashlib.sha256(p.read_bytes()).hexdigest()!=r['sha256']:
            raise ValueError(f"b2 source changed after graph construction: {r['source']}")
        contracts[r['master']]=rtl_ports(p,r['master'])
    count=0
    for master,name,params,conns in insts:
        if master not in contracts:continue
        if params:raise ValueError(f'{name}: expected parameter-free source wrapper')
        actual=contracts[master]
        if conns.dups:raise ValueError(f'{name}: duplicate RTL ports {conns.dups}')
        unknown=set(conns)-set(actual)
        if unknown:raise ValueError(f'{name}: synthetic ports leaked into die.v: {unknown}')
        for p,(width,direction)in actual.items():
            if p not in conns:
                if direction=='input':raise ValueError(f'{name}.{p}: missing actual producer')
                continue
            bits=expr_bits(conns[p],nets)
            if bits is None or len(bits)!=width:
                raise ValueError(f'{name}.{p}: actual source width {width}, emitted {None if bits is None else len(bits)}')
            if direction=='input'and any(x[0]in ('Z','UNRESOLVED','UNDECL')for x in bits):
                raise ValueError(f'{name}.{p}: unbound actual input bits')
        count+=1
    if not count:raise ValueError('no actual b2 source instances in die.v')
    return count


def apply(v, m, source_root=None):
    """Default-off full graph, called after baseline composition before relays.

    The actual compiler calibration is required by the writer. A missing
    producer is never filled with zero to make the source bind appear complete.
    """
    source_root=Path(source_root or Path(__file__).resolve().parents[2])
    import os
    prepared=prepare(v,m,source_root,full_graph=True,compact_selector=os.environ.get('OT_SPLIT_B2_COMPACT_SELECTOR')=='1')
    missing={r['instance']:r['unassigned_input_bits']for r in prepared['input_coverage']
             if any(p!='lnk'for p in r['unassigned_input_bits'])}
    if missing:raise ValueError(f'b2 full source graph has missing actual producers: {missing}')
    import os
    cp=os.environ.get('OT_SPLIT_B2_CALIBRATION')
    calibration=None
    if cp:
        from qwen_b2_join.phase_protocol import validate_calibration
        calibration=validate_calibration(cp,source_root,phase="before_allocator")
        install_calibrated_sources(m,prepared,calibration,source_root)
    writer=v.write_netlist
    def write_netlist(model,k,path,top='qfd_die'):
        if k!=1:raise ValueError('b2 actual source emission requires k=1')
        if calibration is None:
            if os.environ.get('OT_SPLIT_B2_PHYSICAL_TRIAL')!='1':
                raise ValueError('b2 emission needs actual per-half compiler/relay calibration; LNK is not zero')
            return physical_trial_netlist(model,k,path,top,writer,prepared,source_root)
        from qwen_b2_join.phase_protocol import validate_calibration
        # Current graph/age comparison is performed by the shared phase gate;
        # a valid older allocator result never authorizes this emitted die.
        validate_calibration(cp,source_root,current_graph=canonical_graph(model),
                             current_stage_of=model.get('r21_stage_of',{}))
        temporary=Path(str(path)+'.b2-unbound')
        try:
            writer(model,k,temporary,top)
            bind_changed_sources(temporary,prepared['source_receipts'],source_root)
            temporary.replace(path)
            sidecar=Path(str(temporary)+'.params.json')
            if sidecar.exists():sidecar.replace(str(path)+'.params.json')
        finally:
            temporary.unlink(missing_ok=True)
    v.write_netlist=write_netlist
    m['b2_full_graph']=dict(status='SOURCE_GRAPH_CANDIDATE_NOT_NATIVE_OR_PHYSICAL',
        preservation=m['b2_bus_preservation'],compiler_calibration='required at emission',
        source_receipts=prepared['source_receipts'])
    return m['b2_full_graph']


def physical_trial_netlist(model,k,path,top,writer,prepared,source_root):
    """OT_SPLIT_B2_PHYSICAL_TRIAL=1 (Q-B2 10-16): a die-PHYSICAL trial netlist before the functional phase calibration.

    Connectivity is the full b2 source graph (strict RTL bind below). The six halfband lnk straps are derived from THIS
    run's own allocator ages (allocator_ledger law, never zero-filled); the controller/issuer remain the generic sources.
    The sidecar <die.v>.b2_trial.json stamps it PHYSICAL_TRIAL_ONLY_NOT_FUNCTIONAL with every open structural issue.
    It routes and times the die; it is never a functional or release netlist (the production writer still refuses).
    """
    import json
    from qwen_b2_join.allocator_ledger import ledger,derive
    graph=canonical_graph(model);stage_of=model.get('r21_stage_of',{})
    halves,sel,ret,xpf=ledger(graph,stage_of)
    consts,issues=derive(halves,sel,ret,xpf)
    hl=consts['halfband_lnk']
    if not 0<=hl<=54:raise ValueError(f'physical trial: allocator-derived halfband lnk {hl} outside 0..54')
    if any(i.startswith('sp_halfband_')and p=='lnk'for i,p,n,v in model['ties']):raise ValueError('stale lnk straps present')
    model['ties'].extend((f'sp_halfband_{h}','lnk',6,hl)for h in range(6))
    temporary=Path(str(path)+'.b2-unbound')
    try:
        writer(model,k,temporary,top)
        n=bind_changed_sources(temporary,prepared['source_receipts'],source_root)
        temporary.replace(path)
        sidecar=Path(str(temporary)+'.params.json')
        if sidecar.exists():sidecar.replace(str(path)+'.params.json')
    finally:
        temporary.unlink(missing_ok=True)
    Path(str(path)+'.b2_trial.json').write_text(json.dumps(dict(status='PHYSICAL_TRIAL_ONLY_NOT_FUNCTIONAL',
        constants=consts,structural_issues=issues,changed_instances_bound=n,
        open='functional phase calibration (calibrated controller/issuer successors + route temporal gate) OPEN'),indent=1)+'\n')


def audit_control_preservation(original, final, targets):
    """Every original clock/reset net and unrelated endpoint must survive."""
    final_by={bid:(cl,n,es)for bid,cl,n,es in final}
    changed={'tt_ctlm','sp_vector_memory','res_train_issue'}
    for bid,cl,n,es in original:
        if cl not in ('clock_trunk','reset'):continue
        if bid not in final_by:raise ValueError(f'{bid}: dropped original control net')
        fc,fn,fe=final_by[bid]
        if (fc,fn)!=(cl,n):raise ValueError(f'{bid}: changed original control class or width')
        required={tuple(ep)for ep in es if ep[0]not in targets|changed}
        if not required<={tuple(ep)for ep in fe}:
            raise ValueError(f'{bid}: dropped unrelated clock/reset endpoint')


def install_calibrated_sources(model, prepared, calibration, source_root):
    """Install new parameter-free source identities without borrowing old views."""
    from qwen_split.source_pin_plan import rtl_ports
    M=prepared['M'];receipts=prepared['source_receipts']
    by={i.name:i for i in model['insts']}
    for role,instance in (('controller','tt_ctlm'),('issuer','res_train_issue')):
        record=calibration['calibrated_sources'][role]
        old=by[instance].master;new=record['module']
        path=Path(source_root)/record['path']
        if hashlib.sha256(path.read_bytes()).hexdigest()!=record['sha256']:
            raise ValueError(f'{role}: calibrated source changed')
        original=next(r for r in receipts if r['master']==old)
        ports=rtl_ports(path,new)
        if ports!=original['ports']:
            raise ValueError(f'{role}: calibrated successor changed actual source port ABI')
        if new==old:raise ValueError(f'{role}: calibrated successor must have new source identity')
        frame=copy.deepcopy(M[old]);frame.name=new
        frame.note='NEW source-bound calibrated candidate; no physical view inheritance'
        M[new]=frame;by[instance].master=new
        for key in ('port_join','port_split','port_join_open_outputs'):
            if old in model.get(key,{}):model[key][new]=copy.deepcopy(model[key][old])
        receipts[:]=[r for r in receipts if r['master']!=old]
        receipts.append(dict(master=new,source=record['path'],sha256=record['sha256'],ports=ports))
    half_values={f'sp_halfband_{h}':calibration['halves'][str(h)]['halfband_lnk']for h in range(6)}
    for name,value in half_values.items():
        if type(value)is not int or not 0<=value<=54:raise ValueError(f'{name}: actual halfband lnk out of implemented range')
    if any(i in half_values and p=='lnk'for i,p,n,value in model['ties']):
        raise ValueError('refusing duplicate or stale per-half LNK straps')
    model['ties'].extend((name,'lnk',6,value)for name,value in half_values.items())


def canonical_graph(model):
    """JSON-compatible physical-source graph identity, excluding derived reports."""
    import json
    graph=dict(instances=[{k:getattr(i,k)for k in ('name','master','x','y','w','h','orient')}
                       for i in model['insts']],buses=model['buses'],
               port_join=model.get('port_join',{}),port_split=model.get('port_split',{}),
               port_join_open_outputs=model.get('port_join_open_outputs',{}),
               ties=model.get('ties',[]))
    return json.loads(json.dumps(graph,sort_keys=True))
