#!/usr/bin/env python3
"""One changed-source minimum CP exact/connected gate; no stimulus repeats."""
from pathlib import Path
import json,subprocess,hashlib,resource
root=Path(__file__).resolve().parents[1]
out=root/'results/rtl/hbm_cp_phase_parallel_20261006/exact_r1'
out.mkdir(parents=True,exist_ok=True)
work=Path('/tmp/harvey-cp-phase-parallel-exact-r1');work.mkdir(exist_ok=True)
hashes={}
for kind,top in [('exact','tb_su_cp_grouped_owner'),('parent','tb_su_cp_parent_association')]:
    cmd=json.loads((root/f'results/rtl/hbm_cp_fast_frontier_20261006/exact_r1/{kind}_command.json').read_text())
    cmd.insert(2,f'-P{top}.PARALLEL_PHASE_VALIDATION_TEST=1')
    cmd[cmd.index('-o')+1]=str(work/(kind+'.vvp'))
    for name in cmd:
        if name.endswith('.sv'):hashes[name]=hashlib.sha256((root/name).read_bytes()).hexdigest()
    (out/(kind+'_command.json')).write_text(json.dumps(cmd,indent=2)+'\n')
    with (out/(kind+'_compile.log')).open('w') as f:subprocess.run(cmd,cwd=root,stdout=f,stderr=subprocess.STDOUT,check=True)
    with (out/(kind+'.log')).open('w') as f:subprocess.run(['vvp',str(work/(kind+'.vvp'))],cwd=root,stdout=f,stderr=subprocess.STDOUT,check=True)
    print((out/(kind+'.log')).read_text())
exact=(out/'exact.log').read_text();parent=(out/'parent.log').read_text()
assert 'checks=8713' in exact and 'complete_words=262144' in exact
assert 'checks=266' in parent
record=json.loads((root/'results/rtl/hbm_cp_fast_frontier_20261006/exact_r1/terminal.json').read_text())
record.update(source_sha256=hashes,parallel_phase_complete_words=262144,new_cycles=0,new_RTL_FF=0,changed_source=True,physical_qualified=False,adopted=False,simulator=subprocess.check_output(['iverilog','-V'],stderr=subprocess.STDOUT,text=True).splitlines()[0],local_lightweight_peak_RSS_KiB=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
for name in ['rtl/hbm_accel/integrated_20261005/ot_ds_hbm_cluster20_integrated.sv','tools/uarch_model.py']:
    record['source_sha256'][name]=hashlib.sha256((root/name).read_bytes()).hexdigest()
(out/'terminal.json').write_text(json.dumps(record,indent=2)+'\n')
