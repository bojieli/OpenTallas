#!/usr/bin/env python3
"""One changed-source CP output-tail gate, preserving existing fault/debt checks."""
from pathlib import Path
import json,subprocess,hashlib,re,resource
root=Path(__file__).resolve().parents[1]
out=root/'results/rtl/hbm_cp_control_tail_20261006/exact_r1';out.mkdir(parents=True,exist_ok=True)
work=Path('/tmp/harvey-cp-control-tail-exact-r1');work.mkdir(exist_ok=True)
path='rtl/hbm_accel/integrated_20261005/ot_hbm_integrated_su_cp_bind.sv'
old=subprocess.check_output(['git','show','6dc352dbd:'+path],cwd=root,text=True);new=(root/path).read_text();inherited={}
for name in ['ot_hbm_cp_parallel_phase','ot_hbm_cp_phase_nand2','ot_hbm_cp_phase_nor2','ot_hbm_cp_frontier_nand3','ot_hbm_cp_frontier_nor3','ot_hbm_cp_frontier_entry','ot_hbm_cp_four_encode','ot_hbm_cp_four_xor4']:
    a=re.search(r'module '+name+r'\b.*?endmodule',old,re.S).group();b=re.search(r'module '+name+r'\b.*?endmodule',new,re.S).group();assert a==b,name
    inherited[name]=hashlib.sha256(a.encode()).hexdigest()
hashes={}
for kind,top in [('exact','tb_su_cp_grouped_owner'),('parent','tb_su_cp_parent_association')]:
    cmd=json.loads((root/f'results/rtl/hbm_cp_phase_parallel_20261006/exact_r1/{kind}_command.json').read_text())
    cmd.insert(2,f'-P{top}.CONTROL_TAIL_CUT_TEST=1');cmd[cmd.index('-o')+1]=str(work/(kind+'.vvp'))
    for name in cmd:
        if name.endswith('.sv'):hashes[name]=hashlib.sha256((root/name).read_bytes()).hexdigest()
    (out/(kind+'_command.json')).write_text(json.dumps(cmd,indent=2)+'\n')
    with (out/(kind+'_compile.log')).open('w') as f:subprocess.run(cmd,cwd=root,stdout=f,stderr=subprocess.STDOUT,check=True)
    with (out/(kind+'.log')).open('w') as f:subprocess.run(['vvp',str(work/(kind+'.vvp'))],cwd=root,stdout=f,stderr=subprocess.STDOUT,check=True)
    print((out/(kind+'.log')).read_text())
exact=(out/'exact.log').read_text();parent=(out/'parent.log').read_text()
assert 'checks=8713' in exact and 'complete_words=4096 unknown_cases=24' in exact and 'checks=266' in parent
record=json.loads((root/'results/rtl/hbm_cp_phase_parallel_20261006/exact_r1/terminal.json').read_text())
record.update(source_sha256=hashes,control_tail_complete_words=4096,tail_unknown_cases=24,parallel_phase_truth_rerun=False,parallel_phase_truth_inherited=True,inherited_unchanged_modules_sha256=inherited,changed_source=True,new_RTL_FF=0,new_cycles=0,physical_qualified=False,adopted=False,local_lightweight_peak_RSS_KiB=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
for name in ['rtl/hbm_accel/integrated_20261005/ot_ds_hbm_cluster20_integrated.sv']:
    record['source_sha256'][name]=hashlib.sha256((root/name).read_bytes()).hexdigest()
(out/'terminal.json').write_text(json.dumps(record,indent=2)+'\n')
