#!/usr/bin/env python3
"""Opt-in staging of the real-ICG parent CTS mechanism into an existing parent kit."""
import json,shutil,sys
from pathlib import Path
here=Path(__file__).resolve().parent;repo=here.parents[2]
kd=Path(sys.argv[1]); opt=dict(entry_um=[228.972,578.88],plan_args=sys.argv[2:])
for src,dst in [('prepare.py','parent_trunk_prepare.py'),('plan.py','parent_trunk_plan.py'),('measure.tcl','parent_trunk_measure.tcl'),('cts.tcl','parent_trunk_cts.tcl')]:shutil.copyfile(here/src,kd/dst)
for fn in ['parent_trunk_dme.py','parent_trunk_insert.tcl','parent_trunk_stage_table_ckinvdcx16.json','clk_aocv_table_g021.json']:shutil.copyfile(repo/'tools/die_plan'/fn,kd/fn)
(kd/'parent_trunk_options.json').write_text(json.dumps(opt,indent=1)+'\n')
s=(kd/'config.mk').read_text()
if 'parent_trunk_cts.tcl' in s:raise SystemExit('already staged; refuse overwrite')
s+='\n# CODEX A0 parent opt-in local cluster + RTL ICG split DME clock\nexport PRE_CTS_TCL = /work/parent_trunk_cts.tcl\nexport SKIP_CTS_REPAIR_TIMING = 1\n'
(kd/'config.mk').write_text(s)
# Physical trials track this stage explicitly; regenerate the ordinary kit hash with the added files.
sys.path.insert(0,str(repo/'physical/die_plan/qwen_compute/cores/legacy'));from gen_core_kit_qc import kit_hash
f=json.loads((kd/'freeze.json').read_text());f['parent_trunk_kit_stage']=opt;f['kit_hash']=kit_hash(kd);(kd/'freeze.json').write_text(json.dumps(f,indent=1)+'\n')
print('PARENT_TRUNK_STAGE',f['kit_hash'])
