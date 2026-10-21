#!/usr/bin/env python3
"""Grow the actual shipping 0N/frame clock/reset/return cone without compiling.

Use the bind's recorded master files for port directions. This inventory is
explicitly not a functional module closure or a simulation kit. Source RTL is
copied unchanged, and the existing cut grower owns all boundary discovery.
"""
import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--shipping-root',type=Path,required=True)
    p.add_argument('--inventory',type=Path,required=True)
    p.add_argument('--compiler-root',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    inv=json.loads(a.inventory.read_text());r=a.shipping_root
    bind=r/'bind/bind';pb=json.loads((bind/'port_bind.json').read_text())
    assert pb['die_sha256']==inv['die_sha256']
    for rel,rec in inv['sources'].items():assert digest(r/'src'/rel)==rec['sha256']
    portkit=a.out/'port_inventory';src=portkit/'src';src.mkdir(parents=True)
    paths={};choices={}
    for master,rec in pb['masters'].items():
        path=Path(rec['rtl'])
        if not path.is_absolute():path=r/'src'/path
        assert path.is_file(),(master,path)
        actual=digest(path)
        rel='recorded/'+actual+'/'+path.name
        target=src/rel;target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists():target.write_bytes(path.read_bytes())
        paths[rel]=dict(path=rel,sha256=actual,shipping_path=str(path))
        choices[master]=dict(file=rel,source='original immutable port_bind masters.rtl')
    kit=dict(sha='553741303',files=list(paths.values()),variant_choices=choices,
        defines=pb['defines'],status='PORT_DIRECTIONS_ONLY_NO_FUNCTIONAL_CLOSURE',
        original_port_bind_sha256=digest(bind/'port_bind.json'))
    (portkit/'kit.json').write_text(json.dumps(kit,indent=1)+'\n')
    # Use the actual bind's parser, while retaining the current cut grower.
    parser=r/'src/tools/die_port_bind.py'
    spec=importlib.util.spec_from_file_location('shipping_die_port_bind',parser)
    B=importlib.util.module_from_spec(spec);spec.loader.exec_module(B)
    sys.path.insert(0,str(a.compiler_root/'tools/s81_dv'))
    import dv_slice_cut as cut
    cut.K.load_dpb=lambda repo,ref:B
    selected=a.out/'selected_instances.txt'
    selected.write_text('\n'.join(inv['selected_instances'])+'\n')
    cut.main(['--die-v',str(bind/'die.v'),'--kit',str(portkit),'--insts',str(selected),
        '--out',str(a.out/'cut'),'--name','s0N_aggregate','--repo',str(a.compiler_root)])
    files={str(f.relative_to(a.out)):digest(f) for f in a.out.rglob('*') if f.is_file()}
    (a.out/'source_cone.json').write_text(json.dumps(dict(
        schema='opentallas.s81.shipping_aggregate_cone.v1',status='STRUCTURAL_SOURCE_CONE_ONLY',
        die_sha256=inv['die_sha256'],inventory_sha256=digest(a.inventory),files=files,
        cut_grower_sha256=digest(Path(cut.__file__)),parser_sha256=digest(parser),
        functional_closure_qualified=False,landing_flight_model_applied=False,
        runtime_clocks_qualified=False,producer_trace_bound=False),indent=1)+'\n')


if __name__=='__main__':main()
