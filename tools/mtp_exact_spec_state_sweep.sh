#!/bin/bash
# spec_state ring successor vs the as-built ot_dshbm_spec_state, cycle lockstep (rtl/test/hbm_fmax_ctl/
# tb_spec_state_lockstep.sv, a_* delayed by LAT = 5), over seeds x {DRAIN 0, 1} x {f3 (failed source, preserved),
# token-edge TOKEN_EDGE_FIX = 1 (fixed)}.  Icarus (small bench).  Run on an EPYC host (not localhost).
#   tools/mtp_exact_spec_state_sweep.sh OUTDIR [NSEEDS] [NREQ] [JOBS]
set -eu
out=$1; nseeds=${2:-64}; nreq=${3:-20000}; jobs=${4:-32}
root=$(cd "$(dirname "$0")/.." && pwd)
mkdir -p "$out"
cd "$root"
f3=results/rtl/ctl_spec_seed8_fix_20261005/original/spec3_failed.sv
[ -f "$f3" ] || f3=source_set_ctl/spec3_failed.sv
for v in f3 fix1; do
  if [ $v = f3 ]; then dut="$f3"; else dut="rtl/experimental/ctl_spec_seed8_20261005/ot_dshbm_spec_state_f_token_edge.sv rtl/test/mtp_exact/ot_dshbm_spec_state_f_tefix1.sv"; fi
  for d in 0 1; do
    for s in $(seq 1 "$nseeds"); do echo "$v $d $s $dut"; done
  done
done | xargs -P "$jobs" -L 1 bash -c '
  v=$0; d=$1; s=$2; shift 2; o='"$out"'/${v}_d${d}_s${s}
  iverilog -g2012 -s tb_spec_state_lockstep -Ptb_spec_state_lockstep.NREQ='"$nreq"' -Ptb_spec_state_lockstep.SEED=$s \
    -Ptb_spec_state_lockstep.DRAIN=$d -o $o.vvp rtl/hdc/ot_hdc_prefix.sv rtl/gpu/dshbm/ot_dshbm_spec_state.sv "$@" \
    rtl/test/hbm_fmax_ctl/tb_spec_state_lockstep.sv > $o.build 2>&1 || { echo BUILD_FAIL > $o.log; exit 0; }
  vvp -n $o.vvp > $o.log 2>&1; rm -f $o.vvp'
echo done > "$out/DONE"
