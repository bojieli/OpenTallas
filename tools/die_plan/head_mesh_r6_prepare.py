#!/usr/bin/env python3
from pathlib import Path
import shutil
import sys

w = Path('/srv/opentallas-scratch2/claude/wt/codex-head-mesh-2249')
sys.path.insert(0, str(w / 'tools/die_plan'))
import schema
import landing_contract
import signoff

r = Path('/srv/opentallas-scratch2/claude/codex-head-mesh-2249/r6')
k = r / 'hd_mesh_e'
p = schema.Plan(schema.load('/srv/opentallas-scratch2/claude/die-head-34/mesh_e/source_plan_rekit_ff342_p2.json'))
block = landing_contract.ring_input_sdc(p, 'hd_mesh_e')
assert 'cland_fstart_in_m_tx_ft_i' in block
s = k / 'constraint.sdc'
old = s.read_text()
assert '# source-synchronous ring inputs' in old
s.write_text(old.split('# source-synchronous ring inputs', 1)[0] + block)
for f in (k / 'run/results/asap7/dp_hd_mesh_e/base').glob('4*.sdc'):
    f.write_text(f.read_text() + '\n' + block)
with (k / 'config.mk').open('a') as f:
    f.write('\n# R6 bootstrap only; final hold margin10 and structuralguard-100 unchanged\n'
            'export OT_IO_HOLD_PAD_PRE_TARGET_PS = -80\n')
shutil.copy2(w / 'tools/orfs_hold_mm.tcl', k / 'orfs_hold_mm.tcl')
shutil.copy2(w / 'tools/die_plan/head_mesh_pre_route_actual.py', k / 'head_mesh_pre_route_actual.py')
signoff.copy_signoff_bundle(k)
s = (w / 'tools/die_plan/head_mesh_r4_run.sh').read_text()
s = s.replace('R=/srv/opentallas-scratch2/claude/codex-head-mesh-2249\n',
              'R=/srv/opentallas-scratch2/claude/codex-head-mesh-2249/r6\n')
s = s.replace('codex-head-mesh-r4-2249', 'codex-head-mesh-r6-2249')
s = s.replace('run_r4.log', 'run_r6.log').replace('signoff_r4', 'signoff_r6')
s = s.replace('$M grt HOLD_SLACK_MARGIN=10', '$M do-5_1_grt HOLD_SLACK_MARGIN=10')
s = s.replace('$M route\n', 'python3 /work/head_mesh_pre_route_actual.py\n$M route\n')
(r / 'run.sh').write_text(s)
print('HEAD_R6_PREPARED', r)
