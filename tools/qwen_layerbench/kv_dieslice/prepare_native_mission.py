#!/usr/bin/env python3
"""Prepare the owned native KV source with one physical mission START.

The source netlist gains a functional input so the binder can map HOST
mission_start to the published local registered START tap. No source data path
is changed. Bootstrap role classification is supplied separately by CLOCK.
"""
import argparse,gzip,json,re
from pathlib import Path
from native_host_start_gate import patch
from native_astk_source import close as close_astk
from native_boot_ages import dispatch as ages_dispatch, control as ages_control
import native_host_boot_abi as boot_abi_host

def prepare(tree):
    tree=Path(tree).resolve();base=tree/'physical/die_plan/qwen_kvsys';d=base/'bind/kv45'
    # KV-TOK 10-26 boot ABI: the native dispatcher's AGES first; the HOST loader table takes it (one source, checked)
    ctl=tree/'rtl/qwen_sys/static_kv_die_20261017'
    for name,fn in [('qkd_kv_ctl_nc32_face.sv',ages_dispatch),('qkd_kvs_ctl_nc32.sv',ages_control)]:
        path=ctl/name
        if path.exists():path.write_text(fn(path.read_text()))
    boot_ages=boot_abi_host.dispatcher_ages((ctl/'qkd_kvs_ctl_nc32.sv').read_text())
    host=d/'qkd_host_root_admission_obsx_bo1_c45.sv'
    host.write_text(boot_abi_host.c45(patch(host.read_text())))
    obsx=tree/'rtl/qwen_sys/kv_host_obs_20261019/qkd_host_root_admission_obsx.sv'
    obsx.write_text(boot_abi_host.obsx(obsx.read_text()))
    src=d/'die_bound_native.v.gz';text=gzip.open(src,'rt').read()
    old='module qfd_die (pad_die_id, pad_por_n, pad_refclk);'
    new='module qfd_die (pad_die_id, pad_por_n, pad_refclk, mission_start_global);\n  input wire mission_start_global;'
    if text.count(old)!=1:raise ValueError('expected one original native die header')
    text=text.replace(old,new)
    rx=r'qkd_host_root_admission_obsx_bo1_c45\s*#\((.*?)\)\s+host\s*\('
    m=re.search(rx,text,re.S)
    if not m:raise ValueError('expected native HOST instance')
    hp=boot_abi_host.host_instance_params(m.group(1)+', .REQUIRE_MISSION_START(1)',boot_ages)
    replacement='qkd_host_root_admission_obsx_bo1_c45 #('+hp+') host (.mission_start(mission_start_global), '
    lp=boot_abi_host.loader_params(obsx.read_text(),host.read_text(),{'BOOT_AGES':boot_ages})
    *_,errs=boot_abi_host.check_texts((ctl/'qkd_kvs_ctl_nc32.sv').read_text(),(ctl/'qkd_kv_ctl_nc32_face.sv').read_text(),
        (tree/'rtl/qwen_sys/host_20261013/qkd_host_program_loader_target.sv').read_text(),lp)
    if errs:raise ValueError('boot ABI mismatch (dispatcher / HOST loader / image): '+'; '.join(errs))
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
    phys=[c for c in p['partition_types']['kv3_sys_c']['contents'] if c.get('module')=='ot_qkvd_ucie_x64_phy']
    if len(phys)!=1:raise ValueError('expected one actual SYS_C UCIe PHY')
    c=phys[0]
    c['bump_ports']=[dict(pin='link_v',dir='output',width=1),dict(pin='link_flit',dir='output',width=583),dict(pin='far_v',dir='input',width=1),dict(pin='far_flit',dir='input',width=583)]
    planpath.write_text(json.dumps(p,separators=(',',':'))+'\n')
    astk=d/'qkd_astk_ctl_s_g0.sv'
    if astk.exists():astk.write_text(close_astk(astk.read_text(),base/'cores/harden/astk_timing_regs.py'))
    return str(out)

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('owned_tree');a=ap.parse_args();print(prepare(a.owned_tree))
