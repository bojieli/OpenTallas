#!/usr/bin/env python3
"""Prepare the owned native KV source with one physical mission START.

The source netlist gains a functional input so the binder can map HOST
mission_start to the published local registered START tap. No source data path
is changed. Bootstrap role classification is supplied separately by CLOCK.
"""
import argparse,gzip,json,re
from pathlib import Path
from native_host_start_gate import patch

def prepare(tree):
    tree=Path(tree).resolve();base=tree/'physical/die_plan/qwen_kvsys';d=base/'bind/kv45'
    host=d/'qkd_host_root_admission_obsx_bo1_c45.sv'
    host.write_text(patch(host.read_text()))
    src=d/'die_bound_native.v.gz';text=gzip.open(src,'rt').read()
    old='module qfd_die (pad_die_id, pad_por_n, pad_refclk);'
    new='module qfd_die (pad_die_id, pad_por_n, pad_refclk, mission_start_global);\n  input wire mission_start_global;'
    if text.count(old)!=1:raise ValueError('expected one original native die header')
    text=text.replace(old,new)
    rx=r'qkd_host_root_admission_obsx_bo1_c45\s*#\((.*?)\)\s+host\s*\('
    m=re.search(rx,text,re.S)
    if not m:raise ValueError('expected native HOST instance')
    replacement='qkd_host_root_admission_obsx_bo1_c45 #('+m.group(1)+', .REQUIRE_MISSION_START(1)) host (.mission_start(mission_start_global), '
    text=text[:m.start()]+replacement+text[m.end():]
    out=d/'die_bound_native_mission.v.gz'
    with gzip.open(out,'wt') as f:f.write(text)
    recipe=json.loads((d/'asbuilt_f5_g0_flat.json').read_text())
    recipe['base']=str(tree)
    recipe['netlist']=[str(out)]
    recipe['note']='Native source mission START; bootstrap roles and fresh landing/image qualification still required.'
    (d/'asbuilt_mission_pass0.json').write_text(json.dumps(recipe,indent=1)+'\n')
    planpath=base/'die_plan.json';p=json.loads(planpath.read_text())
    p.setdefault('reset',{}).update(start='broadcast',start_port='mission_start_global')
    c=next(c for c in p['partition_types']['kv3_sys_c']['contents'] if c.get('inst')=='ucie_rom')
    c['bump_ports']=[dict(pin='link_v',dir='output',width=1),dict(pin='link_flit',dir='output',width=583),dict(pin='far_v',dir='input',width=1),dict(pin='far_flit',dir='input',width=583)]
    planpath.write_text(json.dumps(p,separators=(',',':'))+'\n')
    return str(out)

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('owned_tree');a=ap.parse_args();print(prepare(a.owned_tree))
