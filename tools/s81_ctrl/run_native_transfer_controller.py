#!/usr/bin/env python3
"""Actual NG256 package/stage/HC/VM/hop H transfer proof, not a layer rate."""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/s81_suhc'))
import hc_gate as HC
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
p.add_argument('--mut',type=int,default=0);p.add_argument('--stall',type=int,default=0);a=p.parse_args()
a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=True);obj=a.out/'obj';obj.mkdir(exist_ok=True)
extra=['rtl/dsrom_sys/s81_suhc/dsfd_sp_hc_c.sv','rtl/dsrom_sys/s81_ph/vm/ot_s81ph_vm_mem.sv']
extra += ['rtl/dsrom_sys/s81_ctrl/'+x+'.sv' for x in (
 'ot_s81_stage_seq','ot_s81_pkg_ctrl','ot_s81_stage_guard','ot_s81_hop_tx','ot_s81_stop',
 'ot_s81_host_cq','ot_s81_ctrl','ot_s81_hc_hland','ot_s81_htransfer','ot_s81_htransfer_boundary') if x!='ot_s81_hc_hland']
extra += ['rtl/dsrom_sys/s81_suhc/ot_s81_hc_hland.sv','rtl/dsrom_sys/ot_dsrom_stall_export.sv',
 'rtl/dsrom_sys/s81_ctrl/test/tb_s81_native_transfer_controller.sv']
source=list(dict.fromkeys(HC.FP['dpi']+HC.RTL+extra))
srcs=HC.dpi_rest(obj)+[ROOT/s for s in source]
cmd=[HC.VERILATOR,'--binary','--timing','-Wno-fatal','-Wno-WIDTH','--top-module','tb_s81_native_transfer_controller',
 '-Mdir',str(obj),'-j','16','--unroll-count','4','-fno-dfg',f'-GMUT={a.mut}',f'-GSTALL={a.stall}',
 *map(str,srcs),'-CFLAGS','-O1']
run=subprocess.run(cmd,capture_output=True,text=True)
(a.out/'build.log').write_text(' '.join(cmd)+'\n'+run.stdout+run.stderr)
if run.returncode:raise SystemExit(run.returncode)
run=subprocess.run([str(obj/'Vtb_s81_native_transfer_controller')],capture_output=True,text=True,cwd=a.out)
(a.out/'run.log').write_text(run.stdout+run.stderr)
rows=[x for x in run.stdout.splitlines() if x.startswith('TB_S81_NATIVE_TRANSFER_CONTROLLER')]
expected='FAIL' if a.mut else 'PASS'
ok=run.returncode==0 and len(rows)==1 and rows[0].split()[-1]==expected
record={'source_sha256':{s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in source},
 'mut':a.mut,'stall':a.stall,'expected':expected,'binary_exit':run.returncode,'verdicts':rows,'gate_pass':ok,
 'scope':'NG256 pure H load/store package/stage/HC/VM/hop composition; no full layer or native120 rate claim'}
(a.out/'record.json').write_text(json.dumps(record,indent=2)+'\n');print('\n'.join(rows));print('NATIVE_TRANSFER_CONTROLLER_GATE', 'PASS' if ok else 'FAIL')
raise SystemExit(0 if ok else 1)
