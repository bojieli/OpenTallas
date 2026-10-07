#!/usr/bin/env python3
"""Export the retile's explicit clock sources and pin provenance before CTS.

Generated portals are planning inputs, never routed BPin evidence. The full
collective clock entries remain unbound until its native physical view exists.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import hbm_accel_die_fp as H
import hbm_die_clock_inputs as I
from budgets.extract_die import anchor
from budgets import clock_plan as P


def generate(sm_contract):
    contract_path=Path(sm_contract)
    sm=json.loads(contract_path.read_text())
    m=I.apply(H.build(H.R24SM3,network_probe=True))
    masters=H.masters(m)
    ports={name:{p:xy for p in master.ports if (xy:=anchor(master,p)) is not None}
           for name,master in masters.items() if hasattr(master,'ports')}
    H._init_real()
    real_clock_masters=set()
    lef_sources=[]
    for master,groups in H.real_ports(m).items():
        if groups.get('ck') != ['clk'] or master not in H.REAL:
            continue
        path=Path(H.REAL[master]); view=H.S.real_lef(str(path))
        instances=[i for i in m['insts'] if i.master==master]
        if any(abs(i.w-view['w'])>1e-6 or abs(i.h-view['h'])>1e-6 for i in instances):
            raise ValueError(f'clock LEF size mismatch: {master}')
        _,(x0,y0,x1,y1)=view['pins']['clk']
        ports.setdefault(master,{})['ck']=[(x0+x1)/2,(y0+y1)/2]
        real_clock_masters.add(master);lef_sources.append(path)
    sm_instances=[i for i in m['insts'] if i.master=='hfd_sm']
    if not all(abs(i.w-sm['die_um'][0])<1e-6 and abs(i.h-sm['die_um'][1])<1e-6 for i in sm_instances):
        raise ValueError('SM pin contract dimensions do not match placement')
    clk=sm['packets']['ck']
    if len(clk)!=1 or clk[0]['real_pin']!='clk' or clk[0]['direction']!='input':
        raise ValueError('SM clock pin contract is not an input singleton')
    ports['hfd_sm']['ck']=clk[0]['xy_um']
    # Old reduced collective portals do not bind the new native two-clock top.
    for pin in ('clk_stream','clk_link'):
        ports.get('hfd_coll',{}).pop(pin,None)
    d=dict(schema='opentallas.budgets.die_model.v1',die='hbm',tool=__file__,
        outline_um=[m['geo']['W'],m['geo']['H']],regions=H.clock_regions(m),
        insts=[[i.name,i.master,i.kind,getattr(i,'region',''),getattr(i,'domain',''),
            i.x,i.y,i.w,i.h,i.orient] for i in m['insts']],
        buses=m['buses'],ports=ports,top_input_ports=m['top_input_ports'],
        strict_clock_pins=True,real_masters=[],
        clock_pin_scope='planned portals only; routed BPin readback and receiver clock loads remain required',
        source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in
            [Path(__file__),Path(H.__file__),Path(I.__file__),contract_path]+lef_sources})
    d['by']={i[0]:i for i in d['insts']}
    trees,_=P.plan_groups(d)
    inventory=[]
    for tree,tr in trees.items():
        root=P.clock_root_xy(d,tr['root'])
        for inst,pin in tr['sinks']:
            xy,bound=P.C.port_xy(d,d['by'][inst],pin)
            inventory.append(dict(tree=tree,instance=inst,port=pin,
                planned_xy_um=list(xy) if bound else None,
                source=('native-full-collective-unbound' if inst=='hb_coll' else
                    'LEF-clk-pin-center-explicit-ck-alias' if d['by'][inst][1] in real_clock_masters else
                    'planned-SM-top-clock-portal' if d['by'][inst][1]=='hfd_sm' else
                    'generator-abstract-portal'),
                routed_pin_verified=False,
                entry_manhattan_um=sum(abs(a-b) for a,b in zip(root,xy)) if bound else None))
    try:
        P.validate_clock_pins(d,trees)
        verdict='PLANNING_PINS_BOUND_PHYSICAL_QUALIFICATION_OPEN'
        failure=None
    except ValueError as exc:
        verdict='BLOCKED_UNBOUND_CLOCK_PINS';failure=str(exc)
    del d['by']
    report=dict(status=verdict,failure=failure,selected=False,
        consumer_endpoints=len(inventory),unbound_endpoints=sum(i['planned_xy_um'] is None for i in inventory),
        domains={t:dict(period_ps=P.clock_period_ps(d,trees,t),root=tr['root'],sinks=len(tr['sinks'])) for t,tr in trees.items()},
        inventory=inventory,
        modeled_added_token_cycles=0,
        token_latency_scope='clock-entry wiring alone; no phase or added pipeline adoption',
        launch_gate='Do not launch this full-tree case until every clock endpoint has a defined pin. Planning CTS still cannot qualify routed physical closure.',
        power_gate='External generation, receiver input capacitance and CTS buffer power are unmeasured; no zero-cost source assumption.',
        source_sha256=d['source_sha256'])
    return d,report


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--sm-contract',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    d,r=generate(a.sm_contract)
    with gzip.open(out/'die_model_hbm.json.gz','wt') as f: json.dump(d,f,separators=(',',':'))
    (out/'inventory.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:r[k] for k in ('status','consumer_endpoints','unbound_endpoints','failure')}))
