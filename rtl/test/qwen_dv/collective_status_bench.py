#!/usr/bin/env python3
"""Real slice2 -> CTLM status contract; run through ot-run on a fleet host.

Terminal->idle, contiguous/bubbled returns and adjacent message boundaries must
reach the real controller as correctly aligned landing/last/rank metadata.  The
old-skew control reintroduces the original metadata bug in a private source copy.
This is a component test, not a selected die programme or timing qualification.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE))
import dv_bench2 as B

def run(work,old_skew=False,variant="base"):
    work=Path(work).resolve();work.mkdir(parents=True,exist_ok=True)
    source=[ROOT/s for s in B.SRCS2 if not s.endswith('tb_qfd_dv2.sv')]
    source += [ROOT/s for s in (HERE/'tt_ctlm_dv_sources.f').read_text().splitlines() if s]
    variants={'base':'qfd_dv_slice2.sv','rsafe':'qfd_dv_slice2_rsafe.sv','landed-rsafe':'qfd_dv_slice2_landed_rsafe.sv','lpf-rsafe':'qfd_dv_slice2_lpf_parts_rsafe.sv','lpc-rsafe':'qfd_dv_slice2_lpf_parts_rsafe.sv'}
    producer=ROOT/'rtl/qwen_dv'/variants[variant]
    if variant in ('rsafe','landed-rsafe'):
        source=[producer if p.name=='qfd_dv_slice2.sv' else p for p in source]
    if variant!='base':source.append(ROOT/'rtl/qwen_dv/qfd_dv_reset_tree.sv')
    if variant=='landed-rsafe':
        source += [ROOT/'rtl/qwen_dv/qfd_dv_su8_landed.sv',ROOT/'rtl/qwen_dv/qfd_dv_su_lane_landed.sv',ROOT/'rtl/common/landed_parent/ot_pl_stream_land.sv',ROOT/'rtl/common/landed_parent/ot_pl_land.sv']
        source += [ROOT/s for s in B.XSRCS]
    if variant=='lpc-rsafe':source.append(producer)
    if variant=='lpf-rsafe':
        # This preserved reset-safe core predates ARF/RP.  Use its actual
        # source-era wrapper, rather than deleting parameters from today's one.
        wrapper=work/'qfd_dv_slice2_e_lpf_4ec4aa5f2e.sv'
        wrapper.write_bytes(subprocess.check_output(['git','-C',str(ROOT),'show','4ec4aa5f2e:rtl/qwen_dv/qfd_dv_slice2_e_lpf.sv']))
        source += [producer,wrapper]
        source += [ROOT/s for s in B.XSRCS]
    source=list(dict.fromkeys(source))
    # B's standard functional SRAM model already defines this physical master.
    # Keep one complete functional definition, never a logic black box.
    seen=set();selected=[]
    for p in source:
        masters=set(re.findall(r'^module\s+(\w+)',p.read_text(),re.M))
        if masters and masters<=seen:
            continue
        if masters&seen:
            raise RuntimeError('mixed duplicate module source '+str(p))
        seen.update(masters);selected.append(p)
    if old_skew:
        p=producer;text=p.read_text()
        a='wire [2:0] st_ar_rank = ar_v ? ar_q[515:513] : ar_rank;'
        b='wire st_ar_last = ar_v ? ar_q[512] : ar_last;'
        if text.count(a)!=1 or text.count(b)!=1:raise RuntimeError('old-skew control source guard')
        text=text.replace(a,'wire [2:0] st_ar_rank = ar_rank;').replace(b,'wire st_ar_last = ar_last;')
        mutant=work/'slice2_old_skew.sv';mutant.write_text(text)
        selected=[mutant if s==p else s for s in selected]
    tb=HERE/'tb_qfd_collective_status.sv'
    (work/'inputs.json').write_text(json.dumps({str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [tb]+selected},indent=2)+'\n')
    build=work/'obj'
    cmd=['verilator','--binary','--timing','--top-module','tb_qfd_collective_status','--prefix','Vstatus','-O2','-j','8','-Wno-fatal','-Wno-lint','-Wno-style','-Wno-TIMESCALEMOD','--Mdir',str(build),str(tb)]+[str(p)for p in selected]
    if variant=='lpf-rsafe':cmd.append('-DSTATUS_LPF')
    if variant=='landed-rsafe':cmd.append('-DSTATUS_LANDED')
    if variant=='lpc-rsafe':cmd.append('-DSTATUS_LPC')
    with (work/'build.log').open('w')as log:subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
    r=subprocess.run([str(build/'Vstatus')],cwd=ROOT,capture_output=True,text=True)
    (work/'run.log').write_text(r.stdout+r.stderr);print(r.stdout)
    expected='FAIL'if old_skew else 'PASS'
    ok=r.returncode==0 and 'COLLECTIVE_STATUS '+expected in r.stdout
    result=dict(component='qfd_dv_slice2 -> qfd_tt_ctlm_dv',old_skew=old_skew,variant=variant,warm_reset=True,expected=expected,verdict='PASS'if ok else 'FAIL',added_cycles=0,global_qualification=False)
    (work/'result.json').write_text(json.dumps(result,indent=2)+'\n');return 0 if ok else 1

if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--work',required=True);a.add_argument('--old-skew',action='store_true');a.add_argument('--variant',choices=['base','rsafe','landed-rsafe','lpf-rsafe','lpc-rsafe'],default='base');v=a.parse_args();sys.exit(run(v.work,v.old_skew,v.variant))
