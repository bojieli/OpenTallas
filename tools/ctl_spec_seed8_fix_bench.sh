#!/bin/bash
# Bounded semantic checks only. Invoke on admitted EPYC2, not localhost.
set -eu
root_dir=$(cd "$(dirname "$0")/.." && pwd)
run_dir=$1
if [ ! -x /srv/opentallas-scratch/admit.sh ]; then
  echo 'Run this on admitted EPYC2; local heavy jobs are forbidden.' >&2; exit 2
fi
if [ -e "$run_dir" ]; then echo 'Use a fresh output directory; failure evidence is immutable.' >&2; exit 2; fi
mkdir -p "$run_dir"
cd "$root_dir"
old_dir=results/rtl/ctl_spec_seed8_fix_20261005/original
fixed_source=rtl/experimental/ctl_spec_seed8_20261005/ot_dshbm_spec_state_f_token_edge.sv
bench_dir=rtl/test/ctl_spec_seed8_20261005
# Each reservation is scheduling only. No wall/CPU/address-space/file-size cap.
/srv/opentallas-scratch/admit.sh 2 -- iverilog -g2012 -s tb_spec_token_reset_repro -o "$run_dir/repro.out" \
  rtl/hdc/ot_hdc_prefix.sv rtl/gpu/dshbm/ot_dshbm_spec_state.sv "$old_dir/spec3_failed.sv" \
  "$fixed_source" "$bench_dir/tb_spec_token_reset_repro.sv" > "$run_dir/repro_build.log" 2>&1
/srv/opentallas-scratch/admit.sh 2 -- vvp -n "$run_dir/repro.out" > "$run_dir/repro.log" 2>&1
/srv/opentallas-scratch/admit.sh 2 -- iverilog -g2012 -s tb_spec_state_lockstep \
  -Ptb_spec_state_lockstep.NREQ=3000 -Ptb_spec_state_lockstep.SEED=8 -o "$run_dir/seed8.out" \
  rtl/hdc/ot_hdc_prefix.sv rtl/gpu/dshbm/ot_dshbm_spec_state.sv "$fixed_source" \
  "$bench_dir/tb_spec_seed8_fixed.sv" > "$run_dir/seed8_build.log" 2>&1
/srv/opentallas-scratch/admit.sh 2 -- vvp -n "$run_dir/seed8.out" > "$run_dir/seed8.log" 2>&1
# Keep the exact terminal-count parser in addition to simulator failure status.
grep -Eq '^LOCKSTEP spec_state .*mismatches=0$' "$run_dir/seed8.log"
printf '0\n' > "$run_dir/exit.txt"
