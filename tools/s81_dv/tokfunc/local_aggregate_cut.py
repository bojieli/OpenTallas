#!/usr/bin/env python3
"""End the shipping cone at actual slice ri_e; preserve all X/RT/clock/reset paths."""
import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--shipping-root',type=Path,required=True)
    p.add_argument('--source-cone',type=Path,required=True)
    p.add_argument('--compiler-root',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    prior=json.loads((a.source_cone/'cut/slice_insts.json').read_text())
    names=set(prior['how'])
    dropped=sorted(n for n in names if re.fullmatch(r'(?:st_xrW_0N_l[0-3]_\d+|ld_xrW_0N_l[0-3]|fwd_xrW_0N_l[0-3])',n))
    assert len([n for n in dropped if n.startswith('ld_')])==4
    selected=names-set(dropped)
    assert all(n in selected for n in ['u_s_0N','u_f_0L10','u_f_0L12','u_f_0L13','u_f_0R10','u_f_0R12','u_f_0R13'])
    insts=a.out/'local_instances.txt';insts.write_text('\n'.join(sorted(selected))+'\n')
    parser=a.shipping_root/'src/tools/die_port_bind.py'
    spec=importlib.util.spec_from_file_location('shipping_local_cut_parser',parser)
    B=importlib.util.module_from_spec(spec);spec.loader.exec_module(B)
    sys.path.insert(0,str(a.compiler_root/'tools/s81_dv'))
    import dv_slice_cut as cut
    cut.K.load_dpb=lambda repo,ref:B
    cut.CLOCK_PORT_RE=re.compile(r'^(?:clk|ck(?:_[A-Za-z0-9]+)*|cr|cr_s|CLK|xk|xok)$')
    cut.main(['--die-v',str(a.shipping_root/'bind/bind/die.v'),
        '--kit',str(a.source_cone/'port_inventory'),'--insts',str(insts),'--no-grow',
        '--out',str(a.out/'cut'),'--name','s0N_aggregate','--repo',str(a.compiler_root),
        '--land-plan',str(a.shipping_root/'land_plan_g8.json'),'--land-model'])
    ports=json.loads((a.out/'cut/slice_ports.json').read_text())['ports']
    raw={f'i__w_xrW_0N_l{k}_lnd':ports[f'i__w_xrW_0N_l{k}_lnd'] for k in range(4)}
    assert all(v['dir']=='input' and v['width']==276 for v in raw.values())
    result=dict(schema='opentallas.s81.local_ri_e_aggregate_cone.v1',status='SOURCE_CUT_ONLY_NO_EXECUTION',
        original_cone_sv_sha256=sha(a.source_cone/'cut/s0N_aggregate.sv'),
        source_die_sha256=sha(a.shipping_root/'bind/bind/die.v'),
        local_cone_sv_sha256=sha(a.out/'cut/s0N_aggregate.sv'),dropped=dropped,
        boundary='four actual u_s_0N.ri_e landed-net inputs; upstream control/packet transport deliberately outside component cut',
        raw_pin_ports=raw,changed_master_bodies=False,synthetic_frame_input=False,
        frame_X_XK_XO_return_transport_preserved=True,
        wire_flight_model='existing dv_flight_sim per production landing K/window, including explicitly marked model rows; no physical phase qualification',
        physical_phase_qualified=False,global_epoch_bound=False,
        clock_inputs={n:v for n,v in ports.items() if v.get('kind')=='clock'})
    (a.out/'local_cone.json').write_text(json.dumps(result,indent=1)+'\n')


if __name__=='__main__':main()
