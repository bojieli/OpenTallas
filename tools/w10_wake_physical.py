#!/usr/bin/env python3
"""Full-goal modeled/exact W10 wake floorplan, with bounded physical resources."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from w10_frontend_main_exact import ROOT, RTL
from w10_wake_qualification import compare_cases, validate_model, verify_sources


def mapped_guard(netlist, mode):
    text = netlist.read_text()
    cells = re.findall(r'^\s+(\w+)\s+(\\?\S+)\s+\((.*?)\n\s*\);',text,re.M|re.S)
    icgs = [(n,dict(re.findall(r'\.(\w+)\(([^)]+)\)',ports))) for typ,n,ports in cells if typ=='ICGx1_ASAP7_75t_R']
    drivers = {}
    for typ,name,ports in cells:
        pins = dict(re.findall(r'\.(\w+)\(([^)]+)\)',ports))
        for pin in ('Y','Z','Q','QN'):
            if pin in pins:
                drivers[pins[pin].strip()] = (typ,name,pins)
    wakes=[]
    for name,pins in icgs:
        net=pins['ENA'].strip()
        for _ in range(5):
            if net not in drivers: raise ValueError('ICG enable has no bounded FF driver: '+net)
            typ,driver,dp=drivers[net]
            if typ.startswith('DFF'):
                wakes.append(driver);break
            inputs=[v.strip() for k,v in dp.items() if k not in ('Y','Z','Q','QN','VDD','VSS')]
            if len(inputs)!=1:raise ValueError('ICG enable still has combinational control cone: '+name)
            net=inputs[0]
        else:raise ValueError('unbounded ICG enable cone')
    macros = [n for typ,n,_ in cells if typ=='ot_rom_4096x274_m8']
    flops = sum(typ.startswith('DFF') for typ,_,_ in cells)
    if len(macros)!=4 or len(icgs)!=8 or len(set(wakes))!=8:
        raise ValueError('macro or distinct wake/gate count differs from full-size model')
    if mode=='column' and flops<88715*.8:
        raise ValueError('full column arithmetic endpoint count undersized')
    return dict(verdict='PASS_STRUCTURE_ONLY',macros=macros,icg_count=len(icgs),
                distinct_wake_flops=wakes,flop_count=flops,
                mapped_netlist_sha256=hashlib.sha256(netlist.read_bytes()).hexdigest())


def argv(mode, work, output):
    model=json.loads((ROOT/'results/uarch/w10_baseline_wake/fullgoal_bound.json').read_text())
    binding=model['mode_binding'][mode]
    sources=[p for p in RTL if not p.startswith('rtl/test/')]
    sources=[p.replace('ot_v41_rom_elem_w10.sv','ot_v41_rom_elem_wake_w10.sv') for p in sources]
    sources += ['rtl/v41rom/ot_v41_rom_elem_q_wake_w10.sv']
    sources += [f'physical/asap7_memory_macros/{n}/{n}_bb.v' for n in ['ot_rom_8192x274_m8','ot_rom_4096x274_m8']]
    params=dict(model['mode_binding']['common'],**{k:v for k,v in binding.items() if k!='top'})
    if mode=='q':
        params={k:v for k,v in params.items() if k in ['NB','FAST','PP','MTP','EARLY','FRONT_PAR','WAKE_REG']}
    shape=model['elements'][mode]['outline_um']
    col=mode=='column'
    cmd=[sys.executable,str(ROOT/'tools/w10_wake_flow.py'),'--view','asap7','--top',binding['top']]
    for p in sources:cmd += ['--source',p]
    cmd += ['--clock-period-ns','0.833','--clock-uncertainty-ns','0.06',
            '--clock-uncertainty-hold-ns','0.025','--io-delay-fraction','0.2',
            '--stages','pnr','--die-area','0','0',*[str(v) for v in shape],
            '--core-area',*(['2.16','2.16',str(shape[0]-2.16),str(shape[1]-2.16)] if col else ['0','0',*map(str,shape)]),
            '--place-density','0.5','--macro-place-halo','2','2',
            '--pin-region',('.*=bottom:151.44-851.44' if col else '^(clk|rst|cfg|go|x).*=bottom:135.54-375.3'),
            '--max-transition-ns','0.32','--slew-margin-percent','40','--hold-margin-ns','0',
            '--step-tcl',f'POST_MACRO_PLACE=physical/abi3/w10_wake_{mode}_place.tcl',
            '--step-tcl','POST_DETAIL_PLACE=physical/abi3/w10_wake_check_pg.tcl',
            '--orfs-var','PDN_TCL=/src/physical/abi3/w10_wake_pdn.tcl',
            '--nickname-tag',f'w10_wake_{mode}_r1','--keep-workdir',str(work),
            '--output',str(output),'--sdc-append','physical/abi3/w10_wake_pp_multicycle.sdc',
            '--macro-view','ot_rom_4096x274_m8=physical/asap7_memory_macros/ot_rom_4096x274_m8',
            '--pnr-stop-after','floorplan','--orfs-corner','WC',
            '--core-input-delay-min-ns','0.75' if col else '0.36',
            '--core-input-delay-max-ns','1.117' if col else '0.727',
            '--output-delay-min-ns','-0.95' if col else '-0.56',
            '--output-delay-max-ns','-0.583' if col else '-0.193']
    if not col:cmd += ['--pin-region','^(p|busy|fault).*=top:135.54-375.3']
    for k,v in params.items():cmd += ['--param',f'{k}={v}']
    return cmd


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--mode',choices=['column','q'],default='column')
    ap.add_argument('--work',type=Path,required=True)
    ap.add_argument('--output-dir',type=Path,required=True)
    a=ap.parse_args()
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():
        raise SystemExit('physical job requires a clean immutable pin')
    model=json.loads((ROOT/'results/uarch/w10_baseline_wake/fullgoal_bound.json').read_text())
    validate_model(model);verify_sources(model)
    qdir=ROOT/'results/uarch/w10_baseline_wake/qualification'
    summary=json.loads((qdir/'qualification.json').read_text())
    control=json.loads((qdir/'exact_r2.json').read_text());verify_sources(control)
    baseline=json.loads((ROOT/'results/uarch/w10_baseline_bb01_qualification/fastpp_front0.json').read_text());verify_sources(baseline)
    golden=json.loads((qdir/'golden_n4_r1.json').read_text())
    if summary['verdict']!='PASS_EXACT_PREPHYSICAL' or control['verdict']!='PASS' or compare_cases(baseline,golden)!=240:
        raise SystemExit('unqualified exact baseline wake')
    for p,h in golden['source_sha256'].items():
        local=qdir/'array_wake_binding.sv' if Path(p).is_absolute() else ROOT/p
        if hashlib.sha256(local.read_bytes()).hexdigest()!=h:raise SystemExit('golden source drift: '+p)
    a.output_dir.mkdir(parents=True,exist_ok=False)
    # Bound each ORFS container; do not rely on nproc or advertised worker RAM.
    bin_dir=a.output_dir/'bin';bin_dir.mkdir()
    docker=bin_dir/'docker'
    docker.write_text('#!/bin/sh\nif [ "$1" = run ]; then\n shift\n exec /usr/bin/docker run --cpus 4 --memory 14g --memory-swap 14g "$@"\nfi\nexec /usr/bin/docker "$@"\n')
    docker.chmod(0o755)
    env={**os.environ,'PATH':str(bin_dir)+':'+os.environ['PATH'],'OT_ORFS_NUM_CORES':'4'}
    cmd=argv(a.mode,a.work,a.output_dir/'floorplan.json')
    rec=dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
             mode=a.mode,command=cmd,state='RUNNING_FLOORPLAN',adopted=False,die_rebase_ready=False,
             constraints='unchanged baseline delays, period 0.833ns, SS/FF 60/25ps; no false paths',
             cpu_limit=4,memory_limit_gib=14)
    (a.output_dir/'job.json').write_text(json.dumps(rec,indent=2)+'\n')
    with (a.output_dir/'floorplan.log').open('w') as log:
        p=subprocess.run(cmd,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
    rec['returncode']=p.returncode
    rec['state']='FAILED_FLOORPLAN_NO_RETRY'
    if p.returncode==0:
        try:
            netlist=next((a.work/'orfs/results/asap7').glob('*/base/1_2_yosys.v'))
            rec['structure']=mapped_guard(netlist,a.mode)
            rec['state']='FLOORPLAN_AND_STRUCTURE_READY_NOT_SIGNOFF'
        except Exception as e:rec['guard_error']=str(e)
    (a.output_dir/'terminal.json').write_text(json.dumps(rec,indent=2)+'\n')
    print(json.dumps(rec,indent=2))
    return rec['state']!='FLOORPLAN_AND_STRUCTURE_READY_NOT_SIGNOFF'


if __name__=='__main__':raise SystemExit(main())
