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
    ap.add_argument('--full-graph',action='store_true',help='preserve unrelated die buses and allocator contention; source/physical qualification is separate')
    ap.add_argument('--compact-selector',action='store_true',help='actual four used selector bits; requires source-specific NL2 s4 and fork4')
    ap.add_argument('--production',action='store_true',help='actual banked halftrain/controller/NB6VM interfaces; still unqualified candidate frames')
    ap.add_argument('--emit-trial',type=Path,help='after allocation write the PHYSICAL-TRIAL die netlist here (b2_graph.physical_trial_netlist; never functional)')
    a=ap.parse_args(); NUP=8 if a.production else 4; QW=64 if a.production else 128; RW=192 if a.production else 384
    a.out.mkdir(parents=True,exist_ok=True)
    import die_top_lint as D
    import qwen_rom_fulldie_b3r2 as G
    from qwen_split.source_pin_plan import rtl_ports,snap
    from qwen_split.direct_up4 import partition_master
    os.environ['OT_RELAY_SKIP']='1'
    D.QWEN_RECIPE='tp8b';D._QW.clear();D.QSRC=None
    v,m=D.load_qwen()[:2]
    from qwen_split.b2_graph import prepare
    prepared=prepare(v,m,a.source_root,production=a.production,mode=a.mode,full_graph=a.full_graph,compact_selector=a.compact_selector)
    M=prepared['M'];data=prepared['data'];control=prepared['control']
    source_receipts=prepared['source_receipts'];frames=prepared['frames'];notes=prepared['notes']
    constant_bindings=prepared['constant_bindings'];groups=prepared['groups']
    input_coverage=prepared['input_coverage'];local_pin_audit=prepared['local_pin_audit']
    before=[dict(n=i.name,m=i.master,x=i.x,y=i.y,w=i.w,h=i.h,o=i.orient)for i in m['insts']]
    (a.out/'input.json').write_text(json.dumps(dict(insts=before,buses=data,control_buses=control,source_receipts=source_receipts,frames=frames,notes=notes,full_graph=a.full_graph,bus_preservation=m.get('b2_bus_preservation'),command_distribution=m.get('command_distribution'),distribution_trees=m.get('distribution_trees'),equal_groups=groups,input_coverage=input_coverage,constant_bindings=constant_bindings,local_pin_audit=local_pin_audit),indent=1)+'\n')
    if a.prepare_only:
        print(json.dumps(dict(status='SOURCE_GRAPH_PREPARED_UNQUALIFIED',instances=len(before),data_buses=len(data),equal_groups=len(groups),production=a.production)))
        return
    os.environ.pop('OT_RELAY_SKIP');os.environ['OT_RELAY_GATE']='warn'
    os.environ['OT_RELAY_DUMP']=str(a.out/'allocator_dump.json')
    G._relays(v,m)
    st=m.get('r21_stage_of',{})
    if a.emit_trial:
        if not(a.full_graph and a.production and a.mode=='b2'):raise SystemExit('--emit-trial needs --full-graph --production --mode b2')
        from qwen_split.b2_graph import physical_trial_netlist
        physical_trial_netlist(m,1,a.emit_trial,'qfd_die',v.write_netlist,prepared,a.source_root)
    if a.full_graph:
        from qwen_split.b2_graph import canonical_graph
        (a.out/'allocator_graph.json').write_text(json.dumps(canonical_graph(m),sort_keys=True,indent=1)+'\n')
        (a.out/'allocator_stage_of.json').write_text(json.dumps(st,sort_keys=True,indent=1)+'\n')
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
    result=dict(mode=a.mode,production_interfaces=a.production,full_graph=a.full_graph,status='FULL_SOURCE_GRAPH_ALLOCATOR_DIAGNOSTIC_NOT_TIMING_QUALIFIED'if a.full_graph else'PARTIAL_REAL_ALLOCATOR_DIAGNOSTIC_NOT_NATIVE_DIE',source_receipts=source_receipts,
                notes=notes,equal_groups=groups,stage_of=st,distribution_ages=distribution_ages,round_trip_contract=round_trip,input_coverage=input_coverage,local_pin_audit=local_pin_audit,relays=m.get('r21_relays',{}),
                unequal_groups={k:{bb:st.get(bb,1)for bb in bs}for k,bs in groups.items()if len({st.get(bb,1)for bb in bs})!=1},
                reduction_transport_paths=prices,
                measured_scope='registered wire hops from bword producer to upper input only; excludes source arithmetic latencies and incomplete native result/control paths',
                omitted=('compiled controller/issuer temporal calibration, physical child clocks and native die qualification'if a.full_graph else'other data relay contention, source arithmetic/sourcecopy/AM calibration, actual leaf clock homes and physical/native qualification'if a.production else'tc/am/rb/LC/new controller and VM source interfaces and other data relay contention'))
    (a.out/'result.json').write_text(json.dumps(result,indent=1)+'\n')
    print(json.dumps({k:val for k,val in result.items()if k not in('source_receipts','stage_of')},indent=1))
if __name__=='__main__':main()
