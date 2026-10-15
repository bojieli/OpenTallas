#!/usr/bin/env python3
"""Read retained cap/NT CTS databases with actual TT/FF libraries.
Placement RC diagnostic only, never routed/native qualification.
"""
import hashlib,json,subprocess
from pathlib import Path
out=Path('/srv/opentallas-scratch/codex/s81-norm-physical-1015/margin-cts-probe');out.mkdir(parents=True,exist_ok=True)
libroot='/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/'
libs=['AO_RVT_{c}_nldm_211120.lib.gz','INVBUF_RVT_{c}_nldm_220122.lib.gz','OA_RVT_{c}_nldm_211120.lib.gz','SEQ_RVT_{c}_nldm_220123.lib','SIMPLE_RVT_{c}_nldm_211120.lib.gz']
records=[]
for variant,date,cell in [('cap','013321','ot_s81_hc_ctfx_cap'),('nt','013322','ot_s81_hc_ctfx_nt')]:
 root=Path('/srv/opentallas-scratch/claude/ref_gate')/f's81hc_ctfx{variant}_margin_ref-20261015-{date}'; work=root/'routes/gate/work/orfs';base=next(work.glob('results/asap7/*/base'));rel=base.relative_to(work)
 for corner in ['tt','ff']:
  tcl='read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef\nread_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef\n'
  for lib in libs:tcl+=f'read_liberty {libroot}asap7sc7p5t_{lib.format(c=corner.upper())}\n'
  tcl+=f'read_db /work/{rel}/4_cts.odb\nset ::ot_ce_corner {corner}\nread_sdc /work/{rel}/4_cts.sdc\nset_propagated_clock [all_clocks]\nread_sdc /src/physical/ref_tile/s81hc_ctfx{variant}_margin_ref/signoff.sdc\nread_sdc /src/physical/common_flow/io_ref_routed.sdc\nsource /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl\nestimate_parasitics -placement\nputs "PLACEMENT_ONLY_WNS max [sta::worst_slack_cmd max] min [sta::worst_slack_cmd min]"\nreport_checks -path_delay min_max -group_path_count 8 -format full_clock_expanded -digits 4\nexit\n'
  f=out/f'{variant}_{corner}.tcl';f.write_text(tcl);log=out/f'{variant}_{corner}.log'
  with log.open('w') as stream:rc=subprocess.run(['docker','run','--rm','-v',f'{work}:/work:ro','-v',f'{root}/src:/src:ro','-v',f'{out}:/probe','openroad/orfs:latest','/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad','-no_init','-exit',f'/probe/{f.name}'],stdout=stream,stderr=subprocess.STDOUT).returncode
  rec={'variant':variant,'corner':corner,'rc':rc,'scope':'retained CTS with placement RC only','odb_sha256':hashlib.sha256((base/'4_cts.odb').read_bytes()).hexdigest(),'log':str(log),'summary':[s for s in log.read_text().splitlines() if 'PLACEMENT_ONLY_WNS' in s or '[ERROR' in s]};records.append(rec);print(json.dumps(rec),flush=True)
(out/'receipt.json').write_text(json.dumps(records,indent=2)+'\n')
raise SystemExit(any(r['rc'] for r in records))
