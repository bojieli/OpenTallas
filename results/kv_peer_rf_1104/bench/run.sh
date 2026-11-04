#!/bin/bash
# usage: run.sh (repo root as cwd); Verilator image. PASS lines expected except the mutant row.
set -u; B=results/kv_peer_rf_1104/bench; O=${1:-/tmp/peerb}; mkdir -p $O
REF=rtl/qwen_sys/host_integrated_20261014/qkd_host_peer_root_mux.sv; PL2=results/kv_peer_rf_1104/rtl/qkd_hr_core_peer/qkd_host_peer_root_mux_pl2.sv
V="verilator --binary --timing -Wno-fatal -Wno-lint --top-module tb_mux -O1"
$V $REF $B/tb_mux.sv --Mdir $O/ref -o t >$O/ref.log 2>&1 || tail -5 $O/ref.log
$V -DUSE_PL2 $PL2 $B/tb_mux.sv --Mdir $O/pl2 -o t >$O/pl2.log 2>&1 || tail -5 $O/pl2.log
$V -DUSE_PL2 -DQKD_HR_PE_PL2_MUTANT $PL2 $B/tb_mux.sv --Mdir $O/mut -o t >$O/mut.log 2>&1 || tail -5 $O/mut.log
for s in 1 2 3; do for d in ref pl2; do echo "$d seed $s: $($O/$d/t +SEED=$s | grep -E "^(DONE|FAULT|PASS|FAIL|ERR)" | tail -3 | tr '\n' ' ')"; done; done
for b in 1 2; do for d in ref pl2; do echo "$d bad $b: $($O/$d/t +BAD=$b | grep -E "^(DONE|FAULT|PASS|FAIL|ERR)" | tail -3 | tr '\n' ' ')"; done; done
echo "mutant (must FAIL): $($O/mut/t +SEED=1 | grep -E "^(PASS|FAIL)" | tail -1)"
