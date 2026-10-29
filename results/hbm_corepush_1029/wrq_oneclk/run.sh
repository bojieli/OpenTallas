#!/bin/bash
set -euo pipefail
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
w=/srv/opentallas-scratch2/claude/wt/codex-hbm-corepush-1029
r=/srv/opentallas-scratch2/claude/codex-hbm-corepush-1029/wrq_oneclk
cd "$w"
d=rtl/hbm_accel/generic/vm/static
h=rtl/hbm_accel/host_static_20261015
for m in 0 1 2; do
  iverilog -g2012 -DWRQ_BENCH_CLOCK_ABI -DMUT=$m -s tb_hbm_sm_vm_wr_q_t_lanes4_lockstep -o "$r/tb$m" "$r/tb.sv" "$r/ot_hbm_sm_vm_wr_q_t_lanes4__oneclk.sv" "$d/ot_hbm_sm_vm_wr_q_lanes_n.sv" "$d/ot_hbm_sm_vm_wr_q_t_lanes.sv" "$d/ot_hbm_sm_vm_wr_q_lanes.sv" "$h/ot_static_cmd_target.sv" "$h/ot_hbm_host_static_ingress.sv" physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v > "$r/compile$m.log" 2>&1
  vvp -n "$r/tb$m" > "$r/tb$m.log" 2>&1
  grep -E "^(lockstep lane-edges|TB_WRQ4_LOCKSTEP)" "$r/tb$m.log"
  if [ "$m" = 0 ];then grep -q "^TB_WRQ4_LOCKSTEP PASS MUT=0" "$r/tb$m.log";else grep -q "^TB_WRQ4_LOCKSTEP FAIL MUT=$m" "$r/tb$m.log";fi
done
echo WRQ_ONECLK_MECHANISM_PASS
