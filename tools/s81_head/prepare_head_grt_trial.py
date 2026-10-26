"""Stage diagnostic GRT-only standard FF hold repair from the reviewed CTS seed.
The measured virtual insertion includes the existing -120ps source latency;
this candidate does not adopt a parent clock contract or claim SIGNED.
"""
import argparse,json,shutil,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('seed',type=Path);p.add_argument('out',type=Path);a=p.parse_args()
repo=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(repo/'tools/die_plan'))
from core_flow import binding,apply
if a.out.exists():raise SystemExit('refuse existing output')
a.out.mkdir(parents=True)
for f in a.seed.iterdir():
 if f.is_file() and not f.name.endswith('.log') and not f.name.startswith(('postcts_gate_','setup_','hold_')):shutil.copy2(f,a.out/f.name)
for sub in ['rtl','macros']:shutil.copytree(a.seed/sub,a.out/sub)
# Reuse the actual reviewed CTS placement/netlist/SDC, never rerun CTS under FF.
shutil.copytree(a.seed/'run/results',a.out/'run/results')
if list((a.out/'run/results').rglob('5*.odb')):raise SystemExit('seed contains route evidence')
basis='DIAGNOSTIC CTS measured absolute pin insertion including preserved clk source -120ps; no parent contract adoption'
b=binding(401.36,299.29,basis_tt=basis,basis_ff=basis)
cfg=(a.out/'config.mk').read_text().splitlines()
replace=['OT_VCLK_TT','OT_VCLK_FF','SKIP_INCREMENTAL_REPAIR','CORNER','CORNERS','HOLD_SLACK_MARGIN']
cfg=[x for x in cfg if not any(x.startswith('export '+k+' =') for k in replace)]
cfg+=apply(a.out,b,'hd_elemB_l4_native_DIAGNOSTIC',hold_ff_margin=5,grt_pre_extra=['/work/grt_clock_protect.tcl'])
cfg+=['export SKIP_INCREMENTAL_REPAIR = 0','export CORNER = BC','export CORNERS = bc','export HOLD_SLACK_MARGIN = 5']
(a.out/'config.mk').write_text('\n'.join(cfg)+'\n')
(a.out/'grt_clock_protect.tcl').write_text('set_dont_touch [get_nets clk]\n')
(a.out/'DIAGNOSTIC_SCOPE.txt').write_text(basis+'\nTT setup / FF hold,833ps,60/25ps uncertainty, pair80. No DRT or SIGNED. Intrinsic network means521.36TT/419.29FF differ from absolute insertion by source-120.\n')
# do-grt avoids make prerequisites; only the reviewed4_cts checkpoint is consumed.
(a.out/'run_grt_trial.sh').write_text(r'''#!/bin/bash
set -euo pipefail
K=$(realpath "$1")
test "${2:-grt}" = grt || { echo GRT_ONLY; exit 2; }
docker run --rm --cpus="${4:-16}" --memory="${3:-32}g" --memory-swap="${3:-32}g" -v "$K:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; OT_VCLK_CORNER=ff make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=16 CORNER=BC CORNERS=bc HOLD_SLACK_MARGIN=5 do-grt' > "$K/grt_diagnostic.log" 2>&1
if find "$K/run/results" -type f \( -name 5_route.odb -o -name 5_2_route.odb -o -name 6_final.odb \) | grep -q .; then echo SCOPE_OVERRUN;exit 99;fi
''')
print(a.out)
