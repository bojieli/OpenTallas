#!/usr/bin/env bash
set -uo pipefail
seed=$1
job=/srv/opentallas-scratch/jobs/sagan-ctl-spec-drain-seeds9-16-r1
wt=/srv/opentallas/repos/sagan-ctl-drain-seeds-ff9fe287e
out=$job/seed$seed
mkdir "$out"
cd "$wt"
source ~/.opentallas-env
iverilog -g2012 -s tb_spec_state_lockstep -Ptb_spec_state_lockstep.NREQ=3000 -Ptb_spec_state_lockstep.SEED="$seed" -Ptb_spec_state_lockstep.DRAIN=1 -o "$out/sim.out" rtl/hdc/ot_hdc_prefix.sv rtl/gpu/dshbm/ot_dshbm_spec_state.sv results/rtl/ctl_spec_seed8_fix_20261005/original/spec3_failed.sv rtl/test/hbm_fmax_ctl/tb_spec_state_lockstep.sv > "$out/build.log" 2>&1
rc=$?
printf '%s\n' "$rc" > "$out/compile.exit"
if [ "$rc" = 0 ]; then
 vvp -n "$out/sim.out" > "$out/run.log" 2>&1
 rc=$?
 printf '%s\n' "$rc" > "$out/runtime.exit"
 if [ "$rc" = 0 ]; then grep -Eq '^LOCKSTEP spec_state requests=3000 .*mismatches=0$' "$out/run.log" || rc=90; fi
fi
printf '%s\n' "$rc" > "$out/exit"
exit "$rc"
