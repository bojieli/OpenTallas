#!/usr/bin/env bash
# A2P (H-NETLIST 2026-10-16): 2-node VM ring gate (N_Q=2) + 4-node regression.
#   run_vms_static_ring2.sh OUT
# PASS = ring2 memory + packet positives PASS; mutants MUT=1 (payload / return port) and MUT=2 (node 0 built N_Q=4)
# of both benches FAIL with a fatal; ring4 memory + packet benches (N_Q default 4) PASS with their mutants failing.
set -u
cd "$(dirname "$0")"
out=$(realpath -m "${1:?out}"); mkdir -p "$out"
macro=../../../../../physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
sha256sum ot_vms_bank_static.sv ot_vms_rstop_static.sv ot_vms_rcl_static.sv ot_vms_hub_static.sv tb_vms_static_ring2_memory.sv tb_vms_static_ring2_packet.sv "$macro" > "$out/sources.sha256"
fail=0
run(){ # tb mut expect(pass|fail) srcs...
 local tb=$1 mut=$2 exp=$3; shift 3
 iverilog -g2012 -s $tb -P$tb.MUT=$mut -o "$out/$tb-$mut.vvp" "$@" > "$out/$tb-$mut.compile.log" 2>&1 || { echo "COMPILE_FAIL $tb $mut"; cat "$out/$tb-$mut.compile.log"; fail=1; return; }
 vvp "$out/$tb-$mut.vvp" > "$out/$tb-$mut.log" 2>&1; local rc=$?
 if [ $exp = pass ]; then
  if [ $rc = 0 ] && grep -q '^PASS ' "$out/$tb-$mut.log"; then echo "POSITIVE $tb MUT=$mut PASS: $(grep '^PASS' "$out/$tb-$mut.log")"; else echo "POSITIVE $tb MUT=$mut FAILED"; tail -3 "$out/$tb-$mut.log"; fail=1; fi
 else
  if [ $rc != 0 ] && ! grep -q '^PASS ' "$out/$tb-$mut.log" && grep -q 'FATAL\|fatal' "$out/$tb-$mut.log"; then echo "MUTANT $tb MUT=$mut REJECTED: $(grep -m1 -io 'fatal.*' "$out/$tb-$mut.log" | head -c 160)"; else echo "MUTANT $tb MUT=$mut SURVIVED"; tail -3 "$out/$tb-$mut.log"; fail=1; fi
 fi
}
M=(ot_vms_bank_static.sv ot_vms_rstop_static.sv "$macro")
P=(ot_vms_bank_static.sv ot_vms_rstop_static.sv ot_vms_rcl_static.sv ot_vms_hub_static.sv "$macro")
run tb_vms_static_ring2_memory 0 pass "${M[@]}" tb_vms_static_ring2_memory.sv
run tb_vms_static_ring2_memory 1 fail "${M[@]}" tb_vms_static_ring2_memory.sv
run tb_vms_static_ring2_memory 2 fail "${M[@]}" tb_vms_static_ring2_memory.sv
run tb_vms_static_ring2_packet 0 pass "${P[@]}" tb_vms_static_ring2_packet.sv
run tb_vms_static_ring2_packet 1 fail "${P[@]}" tb_vms_static_ring2_packet.sv
run tb_vms_static_ring2_packet 2 fail "${P[@]}" tb_vms_static_ring2_packet.sv
# N_Q=4 regression (historical ring4 benches, default parameter)
run tb_vms_static_ring4_memory 0 pass "${M[@]}" tb_vms_static_ring4_memory.sv
run tb_vms_static_ring4_memory 1 fail "${M[@]}" tb_vms_static_ring4_memory.sv
run tb_vms_static_ring4_packet 0 pass "${P[@]}" tb_vms_static_ring4_packet.sv
run tb_vms_static_ring4_packet 1 fail "${P[@]}" tb_vms_static_ring4_packet.sv
rm -f "$out"/*.vvp
[ $fail = 0 ] && echo "VMS_RING2_GATE PASS" || { echo "VMS_RING2_GATE FAIL"; exit 1; }
