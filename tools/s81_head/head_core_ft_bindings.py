#!/usr/bin/env python3
"""Explicit per-core HEAD functional clock entries; no synthetic provider nets.

Apply after head_native_plan_delta and the signed view/latency attachment.
Existing die infrastructure, if supplied, provides each FT output's real net.
Without that graph, emit requirements and keep whole-die generation fail-closed.
"""
import argparse,copy,json,os
from pathlib import Path

def apply(raw):
    out=copy.deepcopy(raw);t=out['partition_types']['hd_tile'];ck=t['clock']
    cores={h['inst']:h for h in t['hard_cores']};ft={p['name']:p for p in t.get('infra_ports',[])}
    taps=[p for p in ck.get('taps',[]) if p.get('kind')=='core']
    if len(taps)!=5 or len(cores)!=5:raise ValueError('exact five native HEAD cores/taps required')
    rows=[];seen=set()
    for k,tap in enumerate(taps):
        name=tap['name'];inst,pin=name.rsplit('.',1)
        if inst not in cores or pin!='ft_mstrap_i' or inst in seen:raise ValueError('core tap must name unique actual ft_mstrap_i')
        seen.add(inst);h=cores[inst];index=4 if 'elemB' in h['module'] else int(inst[-1])
        source=f'hci{index}_mesh_o';p=ft.get(source)
        if not p or p['dir']!='out' or p['kind']!='clock' or p['native_core']!=inst:raise ValueError('native FT mesh output missing/mismatched')
        if not tap.get('insertion_ps') or not tap.get('insertion_ff_ps'):raise ValueError('actual signed TT/FF insertion annotations required')
        rows.append(dict(port=f'clk_c{k}',source_port=source,core=inst,core_pin=pin,
            insertion_tt_ps=tap['insertion_ps'],insertion_ff_ps=tap['insertion_ff_ps'],
            mechanism='clock_taps.tcl OT_CORE_TAPS hangs exact macro clock pin on dedicated entry before CTS'))
    ck['core_taps']='early'
    infra=out.get('infrastructure');requirements=[]
    bindings={(b['part'],b['port']):b['net'] for b in (infra or {}).get('bindings',[])}
    supplied=[]
    for part in out['partitions']:
        if part['type']!='hd_tile':continue
        for row in rows:
            key=(part['name'],row['source_port']);net=bindings.get(key)
            requirements.append(dict(part=part['name'],source_port=row['source_port'],target_port=row['port'],net=net,
                provider_required=net is None))
            if net is not None:supplied.append(dict(part=part['name'],port=row['port'],net=net))
    if infra is not None:
        old=infra.setdefault('clock_tap_bindings',[]);oldmap={(b['part'],b['port']):b['net'] for b in old}
        for b in supplied:
            key=(b['part'],b['port'])
            if key in oldmap and oldmap[key]!=b['net']:raise ValueError('conflicting functional core clock binding')
            if key not in oldmap:old.append(b)
    return out,dict(schema='opentallas.head.core_ft_bindings.v1',core_taps=rows,requirements=requirements,
        missing_provider_nets=sum(r['provider_required'] for r in requirements),
        data_cycles_added=0,provider_graph_created=False,
        note='Source capability candidate: no dummy clock/reset ties, no unused-FT classification; actual routed provider and real signoff still required')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('plan',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    raw,r=apply(json.loads(a.plan.read_text()))
    for t in raw['partition_types'].values():
        for h in t.get('hard_cores',[]):
            if h.get('pins_file') and not Path(h['pins_file']).is_absolute():h['pins_file']=os.path.relpath((a.plan.parent/h['pins_file']).resolve(),a.out.parent.resolve())
    a.out.write_text(json.dumps(raw,indent=1)+'\n');a.out.with_suffix('.bindings.json').write_text(json.dumps(r,indent=1)+'\n')
    print(json.dumps({k:v for k,v in r.items() if k!='requirements'},indent=1))
if __name__=='__main__':main()
