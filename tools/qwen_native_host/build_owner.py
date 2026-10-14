#!/usr/bin/env python3
"""Link source-exact existing HOST/board/allocator/cohort models, no RTL rebuild."""
import argparse,hashlib,json,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--host',type=Path,required=True);p.add_argument('--board',type=Path,required=True);p.add_argument('--allocator',type=Path,required=True);p.add_argument('--cohort',type=Path,required=True);p.add_argument('--router',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--drain-header',type=Path);a=p.parse_args()
a.out.mkdir(parents=True,exist_ok=False)
vlt=Path('/home/ubuntu/.local/opentallas-tools/verilator-5.050/share/verilator/include')
models=[a.host,a.board,a.allocator,a.cohort]
archives=[d/filename for d,filename in zip(models,['Vqkd_host_token_service__ALL.a','Vqkd_host_board_port_fixture__ALL.a','Vot_qwen_tp8_token_epoch_allocator__ALL.a','Vot_qwen_tp8_token_cohort__ALL.a'])]
cmd=['g++','-std=c++20','-O1','-pthread','-I'+str(vlt),'-I'+str(vlt/'vltstd'),'-I'+str(a.source),'-I'+str(a.router.parent)]+['-I'+str(d) for d in models]+[str(a.source/'host_cohort_driver.cpp')]+list(map(str,archives))+[str(vlt/'verilated.cpp'),str(vlt/'verilated_threads.cpp'),'-o',str(a.out/'Vhost_owner')]
if a.drain_header:cmd.insert(1,'-DQWEN_HOST_DRAIN_GATE=1');cmd.insert(1,'-I'+str(a.drain_header.parent))
with (a.out/'link.log').open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
pins={str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in archives+[a.source/'host_owner.hpp',a.source/'host_cohort_driver.cpp',a.router]+([a.drain_header] if a.drain_header else [])}
(a.out/'link_receipt.json').write_text(json.dumps({'scope':'LINK_ONLY_ACTUAL_RTL_ARCHIVES_REUSED','command':cmd,'exit':r.returncode,'source_sha256':pins},indent=2)+'\n')
raise SystemExit(r.returncode)
