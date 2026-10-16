#!/usr/bin/env python3
"""Small Icarus component bench, full53-source quarter, no array build."""
import hashlib
import json
from pathlib import Path
import subprocess
from area_model_1417 import ROOT, checked_write, LOCK

OUT=ROOT/'results/arch/s81_vm_area_1417'
def run(cmd,log):
    assert json.loads(LOCK.read_text())['owner'] in ('claude','codex')
    r=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
    assert json.loads(LOCK.read_text())['owner'] in ('claude','codex')
    (OUT/log).write_text(r.stdout+r.stderr)
    return r

records=[]
for base in (0,8,16,24):
    for variant,define in [('gold',None),('selector','S81_AREA_MUT_SELECTOR'),('data','S81_AREA_MUT_DATA')]:
        stem=f'stripe_b{base}_{variant}'
        cmd=['iverilog','-g2012','-s','tb',f'-Ptb.BASE={base}','-o',str(OUT/f'{stem}.vvp')]
        if define:cmd+=['-D'+define]
        cmd+=['tools/s81_vm/area_stripe_candidate.sv','tools/s81_vm/area_stripe_bench.sv']
        cmd += [f'rtl/dsrom_sys/s81_ph/vm/{s}.sv' for s in
                ['dsfd_vm_static_wdispatch128','dsfd_vm_static_wstage128','dsfd_vm_static_write_capture128']]
        r=run(cmd,f'{stem}_compile.log');assert r.returncode==0,r.stderr
        for mode in (range(5) if variant=='gold' else (0,)):
            r=run(['vvp',str(OUT/f'{stem}.vvp'),f'+mode={mode}'],f'{stem}_mode{mode}.log')
            records.append(dict(base=base,variant=variant,mode=mode,exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr))
            print(stem,mode,r.returncode,r.stdout.strip())
            assert (r.returncode==0)==(variant=='gold')
sources={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in
         ['tools/s81_vm/area_stripe_candidate.sv','tools/s81_vm/area_stripe_bench.sv','tools/s81_vm/area_stripe_gate.py']+
         [f'rtl/dsrom_sys/s81_ph/vm/{s}.sv' for s in
                ['dsfd_vm_static_wdispatch128','dsfd_vm_static_wstage128','dsfd_vm_static_write_capture128']]}
checked_write(OUT/'stripe_proof.json',dict(
    status='ISOLATED_FULL53SOURCE_QUARTER_EXACTNESS_ONLY_NOT_INTEGRATED_OR_PHYSICALLY_QUALIFIED',
    model='8x16bit payload stripes +26bit metadata stripe +registered shared selector',
    clock_scope='Separate leaf pins; simulation ties only. No insertion/relatedclock evidence.',
    age='Source pin atE0 ->registered drain atE5+lane, compared with existingE3+lane; +2streamedges',
    checks='20 gold cases across4BASE:3slotburst,II1lane0,duplicate,invalidlane,emptydrain,reset;8 mutant failures',
    sources=sources,records=records))
