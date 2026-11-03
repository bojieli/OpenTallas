#!/usr/bin/env bash
# DIE-QC-63/SC: old d90 SC leaf vs event HARD_PINREG=1 leaf, lock-step iverilog co-simulation (tb_sc_hard1_vs_old.sv).
# usage: run_eq_sim.sh REPO OUTDIR [SEEDS...]
set -euo pipefail
R=$1; O=$2; shift 2; SEEDS=${*:-1 2}
mkdir -p "$O"; cd "$O"
if [ ! -s old_k79.sv ]; then
git -C "$R" show d90b109213c6949da87b330ef143d96bbe937934:rtl/qwen_dv/s5/qfd_dv_s5_sc2_leaf.sv \
  | sed -e "s/\bqfd_dv_s5_sc2_leaf\b/qfd_dv_s5_sc2_leaf_old/; s/\bqfd_dv_s5_sc2_k79 u\b/qfd_dv_s5_sc2_k79_old u/" > old_leaf.sv
git -C "$R" show d90b109213c6949da87b330ef143d96bbe937934:rtl/qwen_dv/s5/qfd_dv_s5_sc2_k79.sv \
  | sed -e "1,5s/^module qfd_dv_s5_sc2_k79(/module qfd_dv_s5_sc2_k79_old(/" > old_k79.sv
fi
grep -c "^module qfd_dv_s5_sc2_k79_old(" old_k79.sv; grep -c "qfd_dv_s5_sc2_k79_old u" old_leaf.sv
sha256sum old_leaf.sv old_k79.sv "$R"/rtl/qwen_dv/s5/qfd_dv_s5_sc2_leaf.sv "$R"/rtl/qwen_dv/s5/qfd_dv_s5_sc2_k79.sv > inputs.sha256
iverilog -g2012 -o sim.vvp -s tb "$R"/results/qc_die63_sc_1102/eq/tb_sc_hard1_vs_old.sv old_leaf.sv old_k79.sv \
  "$R"/rtl/qwen_dv/s5/qfd_dv_s5_sc2_leaf.sv "$R"/rtl/qwen_dv/s5/qfd_dv_s5_sc2_k79.sv "$R"/rtl/qwen_dv/s5/qfd_dv_s5_sc2_k79_helpers.sv 2> compile.time
for s in $SEEDS; do (vvp -n sim.vvp +SEED=$s > sim_seed$s.full 2>&1; tail -15 sim_seed$s.full > sim_seed$s.log) & done
(vvp -n sim.vvp +SEED=7 +DELAY=1 > sim_negctl_delay1.full 2>&1; tail -15 sim_negctl_delay1.full > sim_negctl_delay1.log) &
wait
grep -h "SC_EQ_SIM" sim_seed*.log sim_negctl_delay1.log
