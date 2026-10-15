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
    def module(name,path,top):
        p=ROOT/path
        parsed=views.L.parse_module(path,top)['ports']
        modules[name]=dict(master=top,source=path,ports={k:dict(direction=d,bits=w) for k,(d,w) in parsed.items()})
        sources[path]=hashlib.sha256(p.read_bytes()).hexdigest()
    for q, rec in abi['quadrants'].items():
        module('hb_vms_'+q,VM_SOURCE,rec['master'])
        actual=modules['hb_vms_'+q]['ports']
        expected={p['name']:dict(direction=p['direction'],bits=p['bits']) for p in rec['ports']}
        assert actual==expected,(q,'source/ABI drift')
        module('delivery_'+q,DELIVERY,'ot_hbm_svc_static_vm_delivery')
    module('hb_ckgen','rtl/hbm_accel/control/hfd_ckgen.sv','hfd_ckgen')
    edges=[]; connected=set()
    def edge(name,src,dst):
        sm,sp=src; dm,dp=dst
        a=modules[sm]['ports'][sp];b=modules[dm]['ports'][dp]
        assert a['direction']=='output' and b['direction']=='input' and a['bits']==b['bits'],(name,a,b)
        edges.append(dict(name=name,bits=a['bits'],source=list(src),sink=list(dst),
                          clock='stream',ready_or_credit=False))
        connected.update((tuple(src),tuple(dst)))
    qs=('SW','SE','NE','NW')
    for i,q in enumerate(qs):
        edge('ring_cw_'+q,('hb_vms_'+q,'cw_out'),('hb_vms_'+qs[(i+1)%4],'cw_in'))
        edge('ring_ccw_'+q,('hb_vms_'+q,'ccw_out'),('hb_vms_'+qs[(i-1)%4],'ccw_in'))
        edge('service_dq_'+q,('delivery_'+q,'dq'),('hb_vms_'+q,'dq'))
    roots=[]
    for name,mod in modules.items():
        if name=='hb_ckgen':continue
        for port,rec in mod['ports'].items():
            if port=='clk' or port.startswith('clk_'):
                assert rec['direction']=='input'
                for bit in range(rec['bits']):
                    roots.append(dict(instance=name,port=port,bit=bit,source=['hb_ckgen','pll_stream'],
                                      physical_insertion_reference=None,status='NEEDS_REAL_CTS_VIEW'))
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
            elif name.startswith('delivery_'):
                owner='actual PHY service band / compiler block command source'
            elif port in ('kq','kq_done'):
                owner='actual static COLL parent / VM writer'
            else:
                owner='actual VM programme SRAM calendar issuer'
            unresolved.append(dict(instance=name,port=port,**rec,required_owner=owner,status='UNBOUND_FAIL'))
    out.mkdir(parents=True,exist_ok=True)
    generated=[]
    # Same source-exact widths as the new eight ring edges and four staging
    # edges. A common-clock station is actual flop RTL, never an abstract stub.
    # Physical location, hop count and timing are deliberately NOT inferred.
    for width in sorted({e['bits'] for e in edges}):
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
    report=dict(schema='opentallas.hbm.actual-v15-source-contract.v1',status='FAIL_UNBOUND_NATIVE_PORTS',
                source_sha256=sources,abi_sha256=hashlib.sha256(abi_path.read_bytes()).hexdigest(),
                instances=modules,known_actual_edges=edges,clock_roots=roots,
                registered_station_masters=generated,unbound_ports=unresolved,
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
    raise SystemExit(0 if args.inventory else bool(report['unbound_count']))
