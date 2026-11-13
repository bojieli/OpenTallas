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

def run(work,old_skew=False):
    work=Path(work).resolve();work.mkdir(parents=True,exist_ok=True)
    source=[ROOT/s for s in B.SRCS2 if not s.endswith('tb_qfd_dv2.sv')]
    source += [ROOT/s for s in (HERE/'tt_ctlm_dv_sources.f').read_text().splitlines() if s]
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
        p=ROOT/'rtl/qwen_dv/qfd_dv_slice2.sv';text=p.read_text()
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
    with (work/'build.log').open('w')as log:subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
    r=subprocess.run([str(build/'Vstatus')],cwd=ROOT,capture_output=True,text=True)
    (work/'run.log').write_text(r.stdout+r.stderr);print(r.stdout)
    expected='FAIL'if old_skew else 'PASS'
    ok=r.returncode==0 and 'COLLECTIVE_STATUS '+expected in r.stdout
    result=dict(component='qfd_dv_slice2 -> qfd_tt_ctlm_dv',old_skew=old_skew,expected=expected,verdict='PASS'if ok else 'FAIL',added_cycles=0,global_qualification=False)
    (work/'result.json').write_text(json.dumps(result,indent=2)+'\n');return 0 if ok else 1

if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--work',required=True);a.add_argument('--old-skew',action='store_true');v=a.parse_args();sys.exit(run(v.work,v.old_skew))
