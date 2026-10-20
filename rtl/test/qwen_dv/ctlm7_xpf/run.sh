#!/bin/bash
# CTLM7 XPF depth twin lockstep (Verilator 5.050, the closure daemon's version). Run from the repo root.
set -euo pipefail
V=${VERILATOR:-/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator}
O=${1:-build/ctlm7_xpf}; mkdir -p "$O"
S="rtl/qwen_sys/dvm_20261014/ot_qfd_xpf_static_schedule.sv rtl/qwen_sys/dvm_20261014/ot_qfd_xpf_static_schedule_p.sv rtl/test/qwen_dv/ctlm7_xpf/tb_xpf_p_lockstep.sv"
rc=0
for cfg in "4 20 0" "4 20 1" "8 13 0"; do set -- $cfg
 M="$O/n$1t$2m$3"
 $V --binary --timing -j 4 -Wno-fatal -GN=$1 -GT=$2 -GML=$3 --top-module tb_xpf_p_lockstep $S --Mdir "$M" > "$M.build.log" 2>&1
 for mut in 0 1; do
  "$M/Vtb_xpf_p_lockstep" +MUT=$mut +SEED=$((7919+$1*31+$3)) | tee "$M.mut$mut.out" | grep XPF_P_LOCKSTEP
  if [ $mut = 0 ]; then grep -q 'XPF_P_LOCKSTEP PASS MUT=0' "$M.mut$mut.out" || rc=1; else grep -q 'XPF_P_LOCKSTEP FAIL MUT=1' "$M.mut$mut.out" || rc=1; fi
 done
done
S2="rtl/qwen_sys/program_receiver_20261014/qkd_program_commit.sv rtl/qwen_sys/program_receiver_20261014/qkd_program_pw_observer_p.sv rtl/test/qwen_dv/ctlm7_xpf/tb_obs_p_equiv.sv"
M="$O/obs"; $V --binary --timing -j 4 -Wno-fatal --top-module tb_obs_p_equiv $S2 --Mdir "$M" > "$M.build.log" 2>&1
for mut in 0 1; do
 "$M/Vtb_obs_p_equiv" +MUT=$mut | tee "$M.mut$mut.out" | grep OBS_P_EQUIV
 if [ $mut = 0 ]; then grep -q 'OBS_P_EQUIV PASS MUT=0' "$M.mut$mut.out" || rc=1; else grep -q 'OBS_P_EQUIV FAIL MUT=1' "$M.mut$mut.out" || rc=1; fi
done
exit $rc
