#!/usr/bin/env bash
# Drain-observation bench of the multi-root return ring qkd_static_kv_return_slots_mc (Q-ELEM-RING 10-16, mc_r3c):
# tb_static_return_idle_mc runs the mc ring beside the unchanged reference ring qkd_static_kv_return_slots on one
# stimulus and checks on EVERY edge that the mc idle_core / idle_hbm are the reference ones exactly one local edge
# later (registered pin captures only) and that data/valid/fault exports are cycle-identical; two core phases.
# Mutants (each must FAIL): occupancy terms dropped (2), the current-edge put term dropped from either export (2),
# mc_r5: the mc_r4 one-stage idle_core form (1) and a one-edge-late fault_core export (1).
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
out=${1:?fresh output directory};mkdir -p "$out"
src="$root/rtl/qwen_sys/static_kv_20261014/qkd_static_kv_return_slots_mc.sv"
ref="$root/rtl/qwen_sys/static_kv_20261014/qkd_static_kv_return_slots.sv"
tb="$root/rtl/test/qwen_static_kv/tb_static_return_idle_mc.sv"
run() { # name file expect
 local n=$1 f=$2 e=$3 ph rc
 for ph in 137 637;do
  iverilog -g2012 -s tb_static_return_idle_mc -Ptb_static_return_idle_mc.PHASE_PS=$ph -Ptb_static_return_idle_mc.DEPTH=${DEPTH:-64} \
   -o "$out/$n-$ph.vvp" "$f" "$ref" "$tb" > "$out/$n-$ph.build.log" 2>&1
  if vvp -n "$out/$n-$ph.vvp" > "$out/$n-$ph.log" 2>&1;then rc=0;else rc=$?;fi
  if [[ $e == pass ]];then [[ $rc == 0 ]] && grep -q '^PASS actual return-ring idle mc' "$out/$n-$ph.log" || { cat "$out/$n-$ph.log";echo "FAIL idle mc $n phase $ph";exit 1; }
  else grep -q '^PASS' "$out/$n-$ph.log" && { cat "$out/$n-$ph.log";echo "FAIL idle mc mutant $n phase $ph passed";exit 1; } || true;fi
  echo "$n phase $ph expect $e: $(grep -m1 'PASS\|FATAL\|IDLE' "$out/$n-$ph.log")"
 done
}
mut() { # name old new
 local f="$out/$1.sv"
 python3 -c 'import sys;s=open(sys.argv[1]).read();assert s.count(sys.argv[2])==1,sys.argv[2];open(sys.argv[4],"w").write(s.replace(sys.argv[2],sys.argv[3]))' "$src" "$2" "$3" "$f"
 run "$1" "$f" fail
}
run positive "$src" pass
mut mut_hbm_occupancy "(published==done_sync2)" "1'b1"
mut mut_core_occupancy "(pub_sync2==consumed)" "1'b1"
mut mut_core_drop_put "idle_core<=rs_c && idle_core_pre && !slot;" "idle_core<=rs_c && idle_core_pre;"
mut mut_hbm_drop_put "idle_hbm<=hr && idle_hbm_pre && !observed && !write_slot;" "idle_hbm<=hr && idle_hbm_pre;"
# mc_r5 (Q-KVRET 10-16): the mc_r4 one-stage idle_core form (current occupancy with only the previous edge's slot)
# asserts one edge early; the fault exports must stay cycle-identical with their sticky state
mut mut_core_r4_form "idle_core<=rs_c && idle_core_pre && !slot;" "idle_core<=rs_c && (pub_sync2==consumed) && !slot && !actual_valid;"
mut mut_core_fault_late "fault_core<=rs_a && (fault_core_s || fault_core_set);" "fault_core<=rs_a && fault_core_s;"
sha256sum "$src" "$ref" "$tb" "$0" > "$out/source.sha256"
echo "PASS native return idle mc: positive 2 phases, 6 mutants x 2 phases FAIL"
