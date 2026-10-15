#!/usr/bin/env python3
"""Generate actual v15 VM/staging contracts and common-clock station RTL.

Unknown producer/consumer ports remain explicit failures. This cannot emit a
native-complete die from legacy direction guesses or pin-only masters.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
import hbm_die_views as views
import hbm_die_station_gen as stations

ROOT = Path(__file__).resolve().parents[1]
VM_SOURCE = 'rtl/hbm_accel/generic/vm/static/hfd_hgi_vms_static.sv'
DELIVERY = 'rtl/hbm_accel/loader/service_native/ot_hbm_svc_static_vm_delivery.sv'


def generate(out):
    abi_path=ROOT/'results/arch/hbm_vm_static_1014/quadrant_abi.json'
    abi=json.loads(abi_path.read_text())
    modules={}; sources={}
    def module(name,path,top,params=None):
        p=ROOT/path
        parsed=views.L.parse_module(path,top,params or {})['ports']
        modules[name]=dict(master=top,source=path,params=params or {},ports={k:dict(direction=d,bits=w) for k,(d,w) in parsed.items()})
        sources[path]=hashlib.sha256(p.read_bytes()).hexdigest()
    for q, rec in abi['quadrants'].items():
        module('hb_vms_'+q,VM_SOURCE,rec['master'])
        actual=modules['hb_vms_'+q]['ports']
        expected={p['name']:dict(direction=p['direction'],bits=p['bits']) for p in rec['ports']}
        assert actual==expected,(q,'source/ABI drift')
        module('delivery_'+q,DELIVERY,'ot_hbm_svc_static_vm_delivery')
    module('hb_ckgen','rtl/hbm_accel/control/hfd_ckgen.sv','hfd_ckgen')
    service_contract=ROOT/'physical/hbm_accel_die_views/svc/v15/contract.json'
    service=None
    if service_contract.exists():
        service=json.loads(service_contract.read_text())
        for rec in service['instances']:
            top=rec['actual_module']
            module(rec['instance'],'physical/hbm_accel_die_views/svc/v15/rtl/'+top+'.sv',top)
            assert modules[rec['instance']]['ports']==service['actual_module_port_tables'][top]['ports']
        for q in abi['quadrants']:
            module('phy_'+q,'physical/asap7_memory_macros_v2/ot_hbm3e_phy_v41x_aw30_e8p5/ot_hbm3e_phy_v41x_aw30_e8p5_bb.v',
                   'ot_hbm3e_phy_v41x_aw30_e8p5')
    calendar_source='rtl/hbm_accel/generic/vm/static/hfd_hgi_vm_calendar_static.sv'
    if (ROOT/calendar_source).exists():
        for q in abi['quadrants']:
            module('calendar_'+q,calendar_source,'hfd_hgi_vm_calendar_'+q)
            for stage in range(3):
                module(f'lg_{q}_{stage}','rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_static_tap.sv',
                       'ot_hbm_vm_lg_static_tap',dict(READ_RETURN=10+4*stage,WRITE_RETURN=7+4*stage))
    status_source='rtl/hbm_accel/generic/vm/static/ot_vms_status4_static.sv'
    if (ROOT/status_source).exists():module('vm_status4',status_source,'ot_vms_status4_static')
    coll_source='rtl/hbm_accel/generic/collective/p2p/ot_hfd_coll_q_static.sv'
    if (ROOT/coll_source).exists():
        for q in abi['quadrants']:module('hb_coll_'+q,coll_source,'ot_hfd_coll_q3_static' if q=='SW' else 'ot_hfd_coll_q2_static')
    edges=[]; connected=set(); parts={}; logical_constants=[]
    def edge(name,src,dst):
        sm,sp=src; dm,dp=dst
        a=modules[sm]['ports'][sp];b=modules[dm]['ports'][dp]
        assert a['direction']=='output' and b['direction']=='input' and a['bits']==b['bits'],(name,a,b)
        edges.append(dict(name=name,bits=a['bits'],source=list(src),sink=list(dst),
                          clock='stream',ready_or_credit=False))
        connected.update((tuple(src),tuple(dst)))
    def slice_edge(name,src,dst,width):
        sm,sp,lo=src;dm,dp,dlo=dst
        a=modules[sm]['ports'][sp];b=modules[dm]['ports'][dp]
        assert a['direction']=='output' and b['direction']=='input'
        assert lo>=0 and lo+width<=a['bits'] and dlo>=0 and dlo+width<=b['bits'],(name,a,b,width)
        used=parts.setdefault((dm,dp),set())
        assert not used.intersection(range(dlo,dlo+width)),(name,'multiple drivers')
        edges.append(dict(name=name,bits=width,source=[sm,sp,lo,lo+width],sink=[dm,dp,dlo,dlo+width],
                          clock='stream',ready_or_credit=False))
        for end,low,rec in ((src,lo,a),(dst,dlo,b)):
            key=tuple(end[:2]);parts.setdefault(key,set()).update(range(low,low+width))
            if len(parts[key])==rec['bits']:connected.add(key)
    for q in abi['quadrants']:
        vm='hb_vms_'+q;cal='calendar_'+q;coll='hb_coll_'+q
        if cal in modules:
            for port,rec in modules[cal]['ports'].items():
                if rec['direction']=='output' and port in modules[vm]['ports']:
                    edge('calendar_'+q+'_'+port,(cal,port),(vm,port))
            for stage in range(3):
                tap=f'lg_{q}_{stage}'
                for port in ('read','write'):
                    slice_edge(f'{tap}_{port}_select',(cal,'lg_local_'+port,stage*8),(tap,'local_'+port,0),8)
                if stage==0:
                    slice_edge(tap+'_rq',(tap,'near_rq',0),(vm,'rq',0),136)
                    slice_edge(tap+'_wq',(tap,'near_wq',0),(vm,'wq',0),2248)
                    slice_edge(tap+'_rr',(vm,'rr',0),(tap,'near_rr',0),2056)
                    slice_edge(tap+'_w_done',(vm,'wq_done',0),(tap,'near_w_done',0),8)
                else:
                    near=f'lg_{q}_{stage-1}'
                    for suffix in ('rq','wq'):edge(tap+'_'+suffix,(tap,'near_'+suffix),(near,'far_'+suffix))
                    edge(tap+'_rr',(near,'far_rr'),(tap,'near_rr'))
                    edge(tap+'_wdone',(near,'far_w_done'),(tap,'near_w_done'))
                if stage==2:
                    for port in ('far_rq','far_wq'):
                        logical_constants.append(dict(sink=[tap,port],bits=modules[tap]['ports'][port]['bits'],
                            value=0,reason='actual three-tap topology termination; no fourth producer',
                            physical_tie_cells_qualified=False))
                        connected.add((tap,port))
        if 'vm_status4' in modules:
            # Source ABI sid order SW,SE,NW,NE; do not confuse with ring order.
            index=('SW','SE','NW','NE').index(q)
            slice_edge('status_'+q,(vm,'vmstat',0),('vm_status4','quadrant_status',19*index),19)
        if coll in modules:
            group=3 if q.startswith('S') else 5
            assert abi['quadrants'][q]['params']['RG']>group,(q,'COLL native read-group expansion missing')
            slice_edge('coll_vm_rq_'+q,(coll,'vm_rq',0),(vm,'rq',136*group),136)
            slice_edge('coll_vm_rr_'+q,(vm,'rr',2056*group),(coll,'vm_rr',0),2056)
            edge('coll_vm_kq_'+q,(coll,'vm_kq'),(vm,'kq'))
    qs=('SW','SE','NE','NW')
    for i,q in enumerate(qs):
        edge('ring_cw_'+q,('hb_vms_'+q,'cw_out'),('hb_vms_'+qs[(i+1)%4],'cw_in'))
        edge('ring_ccw_'+q,('hb_vms_'+q,'ccw_out'),('hb_vms_'+qs[(i-1)%4],'ccw_in'))
        if 'hb_coll_'+q in modules:
            edge('collective_cw_'+q,('hb_coll_'+q,'pr_cw_o'),('hb_coll_'+qs[(i+1)%4],'pr_cw_i'))
            edge('collective_ccw_'+q,('hb_coll_'+q,'pr_ccw_o'),('hb_coll_'+qs[(i-1)%4],'pr_ccw_i'))
        edge('service_dq_'+q,('delivery_'+q,'dq'),('hb_vms_'+q,'dq'))
    if service:
        for rec in service['instances']:
            name=rec['instance'];phy='phy_'+rec['quadrant'];pcs=rec['physical_pc_ids']
            assert pcs==list(range(pcs[0],pcs[-1]+1)),(name,'non-contiguous PC mapping needs explicit bit permutation')
            for field,width in service['phy']['pc_fields'].items():
                band=modules[name]['ports'][field];hard=modules[phy]['ports'][field]
                assert band['bits']==len(pcs)*width and hard['bits']==32*width
                assert {band['direction'],hard['direction']}=={'input','output'}
                band_end=[name,field];phy_end=[phy,field,pcs[0]*width,(pcs[-1]+1)*width]
                src,dst=(band_end,phy_end) if band['direction']=='output' else (phy_end,band_end)
                edges.append(dict(name=name+'_'+field,bits=len(pcs)*width,source=src,sink=dst,
                                  clock='hbm',ready_or_credit=field in ('k_rdy','kr_rdy'),
                                  allowed_exception='actual HBM PHY/controller boundary only'))
                connected.add((name,field))
        for q in abi['quadrants']:
            pcs=[p for rec in service['instances'] if rec['quadrant']==q for p in rec['physical_pc_ids']]
            assert sorted(pcs)==list(range(32)),(q,'duplicate or missing actual PHY PC')
            connected.update(('phy_'+q,f) for f in service['phy']['pc_fields'])
    roots=[]
    for name,mod in modules.items():
        if name=='hb_ckgen':continue
        for port,rec in mod['ports'].items():
            if port=='clk' or port.startswith('clk_'):
                assert rec['direction']=='input'
                for bit in range(rec['bits']):
                    roots.append(dict(instance=name,port=port,bit=bit,source=['hb_ckgen','pll_stream'],
                                      physical_insertion_reference=None,status='NEEDS_REAL_CTS_VIEW'))
                    if name.startswith(('svc_','phy_')):roots[-1]['source']=['hb_ckgen','pll_hbm']
                connected.add((name,port))
            if port=='rst_n':
                connected.add((name,port))
    unresolved=[]
    for name,mod in modules.items():
        for port,rec in mod['ports'].items():
            if (name,port) in connected:continue
            if name=='hb_ckgen':
                if port in ('refclk','por_n'):continue # actual declared external bump boundary
                if port.startswith(('pll_','por_')):continue # other actual die domains; outside this subnet
            if port in ('cq','cr','rq','rr','wq','wq_done'):
                owner='actual static client source migration'
            elif port in ('vmstat','bank_status','hub_status','mirror_busy','ring_fault'):
                owner='actual four-quadrant status aggregate and CP consumer'
            elif name.startswith(('delivery_','svc_','phy_')):
                owner='actual PHY service band / compiler block command source'
            elif port in ('kq','kq_done'):
                owner='actual static COLL parent / VM writer'
            else:
                owner='actual VM programme SRAM calendar issuer'
            missing=sorted(set(range(rec['bits']))-parts.get((name,port),set()))
            ranges=[]
            for bit in missing:
                if ranges and ranges[-1][1]==bit:ranges[-1][1]=bit+1
                else:ranges.append([bit,bit+1])
            unresolved.append(dict(instance=name,port=port,**rec,required_owner=owner,
                bound_bits=rec['bits']-len(missing),unbound_bits=len(missing),
                unbound_ranges_half_open=ranges,status='UNBOUND_FAIL'))
    out.mkdir(parents=True,exist_ok=True)
    generated=[]
    # Same source-exact widths as the new eight ring edges and four staging
    # edges. A common-clock station is actual flop RTL, never an abstract stub.
    # Physical location, hop count and timing are deliberately NOT inferred.
    for width in (2224,2248):
        master=f'hfd_stn_v15_cc{width}'
        def port(direction,bits):
            return dict(direction=direction,bits=bits,dir_segments=[[0,bits,'in' if direction=='input' else 'out']])
        rec=dict(master=master,ports=dict(ck=port('input',1),rst=port('input',1),a=port('input',width),b=port('output',width)))
        emitter,role=stations.build(rec,{})
        mutant,_=stations.build(rec,{},mutant=True)
        (out/(master+'.sv')).write_text(stations.module_text(rec,emitter))
        (out/(master+'_mutant.sv')).write_text(stations.module_text(rec,mutant))
        (out/(master+'_ports.json')).write_text(json.dumps(rec,indent=1)+'\n')
        generated.append(dict(master=master,bits=width,role=role,latency_cycles=1,
                              sinks_per_root=width,physical_qualified=False,bench_qualified=False))
    dependency_hashes={}
    for directory in ('rtl/hbm_accel/generic/vm/static','rtl/hbm_accel/loader/service_native'):
        for dep in sorted((ROOT/directory).glob('*.sv')):
            dependency_hashes[str(dep.relative_to(ROOT))]=hashlib.sha256(dep.read_bytes()).hexdigest()
    report=dict(schema='opentallas.hbm.actual-v15-source-contract.v1',status='FAIL_UNBOUND_NATIVE_PORTS',
                source_sha256=sources,dependency_inventory_sha256=dependency_hashes,
                dependency_inventory_scope='all static VM/service RTL including benches; not a substitute for hierarchy elaboration',
                hierarchy_elaboration_required=True,
                service_qualification_rejections=service['qualification_rejections'] if service else [],
                abi_sha256=hashlib.sha256(abi_path.read_bytes()).hexdigest(),
                instances=modules,known_actual_edges=edges,clock_roots=roots,
                registered_station_masters=generated,logical_constant_requests=logical_constants,unbound_ports=unresolved,
                boundary_gaps=['actual 1.024ns PHY to 0.833333ns stream block CDC absent',
                               'actual mapped PHY address/endian/PC striping proof required',
                               'historical PC leaf rejected for address/clock semantics; actual block CDC replacement required'],
                unbound_count=len(unresolved),pin_only_placeholder_count=0,
                legacy_failures_disposition='77 legacy station failures remain historical; v15 validates actual source ports independently',
                qualification=dict(native_complete=False,pins=False,station_benches=False,clock_views=False,TT=False,FF=False,DRC=False),
                required_remaining=['actual client and programme command source joins','actual static COLL combined parent',
                                    'actual full service/SM/writeback composition','measured compact SM outline and all leaf views',
                                    'pin plans, physical registered stations and exact compiler stage counts','real-view die GRT0/TT/FF/DRC0'])
    (out/'contract.json').write_text(json.dumps(report,indent=1)+'\n')
    print(json.dumps(dict(actual_instances=len(modules),actual_edges=len(edges),clock_roots=len(roots),
                         unbound_ports=len(unresolved),station_masters=generated)))
    return report


def bench(out, report):
    tb=ROOT/'rtl/test/tb_hbm_v15_station.sv'
    tops=['hfd_stn_v15_cc2224','hfd_stn_v15_cc2248']
    receipt=dict(testbench_sha256=hashlib.sha256(tb.read_bytes()).hexdigest(),
                 scope='source station mechanism only; no physical pin or timing qualification',runs=[])
    for mutant in (None,*tops):
        tag=mutant or 'positive'
        exe=out/(tag+'.vvp')
        files=[out/(top+('_mutant' if top==mutant else '')+'.sv') for top in tops]
        cmd=['iverilog','-g2012','-s','tb','-o',str(exe),str(tb),*map(str,files)]
        subprocess.run(cmd,check=True,capture_output=True,text=True)
        run=subprocess.run(['vvp',str(exe)],capture_output=True,text=True)
        log=run.stdout+run.stderr
        (out/(tag+'.log')).write_text(log)
        if mutant:
            assert run.returncode!=0 and 'station mismatch cycle=' in log,(tag,run.returncode,log)
        else:
            assert run.returncode==0 and 'V15_STATION PASS' in log,(run.returncode,log)
        receipt['runs'].append(dict(name=tag,exit=run.returncode,log=log,
            source_sha256={str(f.name):hashlib.sha256(f.read_bytes()).hexdigest() for f in files}))
        exe.unlink()
    (out/'station_bench.json').write_text(json.dumps(receipt,indent=1)+'\n')
    for rec in report['registered_station_masters']:rec['bench_qualified']=True
    report['qualification']['station_benches']=True
    (out/'contract.json').write_text(json.dumps(report,indent=1)+'\n')


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--bench',action='store_true',help='run actual emitted station RTL and both bit-swap mutants')
    ap.add_argument('--inventory',action='store_true',help='allow explicit incomplete source inventory; default gate fails closed')
    args=ap.parse_args()
    report=generate(args.out)
    if args.bench:bench(args.out,report)
    raise SystemExit(0 if args.inventory else bool(report['unbound_count'] or report['boundary_gaps'] or report['logical_constant_requests']))
