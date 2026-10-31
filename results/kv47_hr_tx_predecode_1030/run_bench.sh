#!/bin/bash
# DIE-KV-47-HR: lockstep bench ref (origin/main MU, CONST_LANE_WRITES=0) vs KV-only hr_tx_predecode variant
# (CONST_LANE_WRITES=1, HDR_PREDECODE=HP), core_tx parameters. Usage: run_bench.sh <repo root> <N> [seeds...]
# Also runs 2 mutants which must FAIL: M1 flag hflags[11] off by one bit (peer token frame z263), M2 one rp one-hot copy rotates backwards.
set -euo pipefail
R=$(cd "$1" && pwd); N=$2; shift 2; H=$(cd "$(dirname "$0")" && pwd); T=$(mktemp -d)
git -C "$R" show 'origin/main:rtl/qwen_sys/mu_qwen_20261018/qkd_host_ctrl_token_service_packet_collected_mu.sv' \
  | sed 's/module qkd_host_ctrl_token_service_packet_collected_mu #/module qkd_host_ctrl_token_service_packet_collected_mu_ref #/' > $T/ref.sv
V=$R/rtl/qwen_sys/mu_qwen_20261018/hr_tx_predecode/qkd_host_ctrl_token_service_packet_collected_mu.sv
sed 's/hflags\[11\]=x\[511:263\]==0;/hflags[11]=x[511:264]==0;/' $V > $T/mut1.sv; ! cmp -s $V $T/mut1.sv
sed 's/else if(take)oh<={oh\[2:0\],oh\[3\]};/else if(take)oh<=(gi==1?{oh[0],oh[3:1]}:{oh[2:0],oh[3]});/' $V > $T/mut2.sv; ! cmp -s $V $T/mut2.sv
for s in "${@:-1 2 3}"; do for hp in 1 0; do
  iverilog -g2012 -o $T/sim_${s}_$hp -Ptb.SEED=$s -Ptb.N=$N -Ptb.HP=$hp $H/tb_hr_tx_predecode_lockstep.sv $T/ref.sv $V
  (r=$(vvp -n $T/sim_${s}_$hp | grep -E '^(PASS|FAIL)'); echo "$r") &
done; done
for m in 1 2; do
  iverilog -g2012 -o $T/sim_mut$m -Ptb.SEED=1 -Ptb.N=$N -Ptb.HP=1 $H/tb_hr_tx_predecode_lockstep.sv $T/ref.sv $T/mut$m.sv
  (r=$(vvp -n $T/sim_mut$m | grep -E '^(PASS|FAIL)'); echo "MUTANT M$m: $r") &
done
wait
rm -rf $T
