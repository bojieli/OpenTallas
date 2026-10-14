#!/usr/bin/env python3
"""Source-bound connected controller/CP bench; kernel arithmetic is synthetic in the established MX1 bench."""
import sys, pathlib, json
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import hgi_mtp_native_gate as G
work=pathlib.Path(sys.argv[1]).resolve();mode=sys.argv[2]
work.mkdir(parents=True,exist_ok=True)
tb=(ROOT/G.TB_A).read_text();assert G.OLD_INST in tb
p=work/'connected.sv';p.write_text(tb.replace(G.OLD_INST,G.NEW_INST))
base=[ROOT/s for s in G.NATIVE+G.FACADE]
if mode=='positive':
 cases=[G.run(work,'connected_positive','tb_hbm_native_mtp_cp_closed_control_mx1',base+[ROOT/s for s in G.MX1]+[p])]
 for k in (0,1,2):
  for r in (0,1):cases.append(G.run(work,f'cp_result_{k}_{r}','tb_hfd_mtp_x_cp_stop',base+[ROOT/G.TB_B],(f'KIND={k}',f'RESET_FIRST={r}')))
 ok=all(c['returncode']==0 and c.get('phase')!='compile' for c in cases)
 print('MTP_NATIVE_PHYSICAL_EXACT', 'PASS' if ok else 'FAIL')
else:
 be=(ROOT/G.MX1[1]).read_text();assert G.MUT_NEEDLE in be
 m=work/'wrong_job.sv';m.write_text(be.replace(G.MUT_NEEDLE,"cpl_job=raw[232:201]^32'd1"))
 cases=[G.run(work,'wrong_job','tb_hbm_native_mtp_cp_closed_control_mx1',base+[ROOT/G.MX1[0],m]+[ROOT/s for s in G.MX1[2:]]+[p])]
 ok=cases[0]['returncode']!=0 and cases[0].get('phase')!='compile'
 print('MTP_NATIVE_PHYSICAL_MUTANT','REJECTED' if ok else 'ESCAPED')
(work/'receipt.json').write_text(json.dumps(cases,indent=2)+'\n')
for c in cases: print(c['case'],c['returncode'],c.get('phase'),c['output'])
sys.exit((0 if ok else 1) if mode=='positive' else (1 if ok else 0))
