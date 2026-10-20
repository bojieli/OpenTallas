#!/bin/bash
# QW-F16PROG4: 9-bit CALR request face + real table-ROM loader + VM join (qfd_dv_slice_tload) into the real qfd_dv_vm,
# Verilator 5.050 (closure-daemon pin).  Fixture = compact c63242 table manifest (programme_store.py +
# table_rom_native_fixture.py output, copied into fixture/).  Run from this directory under ot-run (no host pin).
set -uo pipefail
cd "$(dirname "$0")"
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$V" --version > verilator.version
S=src
M=$S/physical/asap7_memory_macros
SRCS="$M/ot_rom_4096x266_m8/ot_rom_4096x266_m8.v $M/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
 $M/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v $M/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
 $S/rtl/qwen_dv/qfd_dv_vm.sv $S/rtl/qwen_dv/qfd_dv_table_rom_loader.sv $S/rtl/qwen_dv/qfd_dv_slice_tload.sv
 $S/rtl/test/qwen_dv/tb_qfd_dv_slice_tload.sv"
sha256sum $SRCS > sources.sha256
B="--binary --timing -j 8 -Wno-fatal --top-module tb_qfd_dv_slice_tload"
mkdir -p logs witness
for m in 0 1 2 3 4 5; do
  ( "$V" $B -GMUT=$m -Mdir obj$m $SRCS > logs/build$m.log 2>&1 || echo BUILD_FAIL > logs/build$m.fail ) &
done
wait
ls logs/*.fail 2>/dev/null && { echo TLOAD_BUILD_FAIL; exit 3; }
ok=1
X=obj0/Vtb_qfd_dv_slice_tload
"$X" +OT_ROM_DIR=$PWD/fixture/s0 +EXPECTED=$PWD/fixture/s0/expected.hex > logs/pass_s0.log 2>&1
grep -q TLOAD_JOIN_PASS logs/pass_s0.log && echo "PASS s0 $(grep -o 'edge_checks=.*' logs/pass_s0.log)" || { echo "FAIL s0"; ok=0; }
"$X" +OT_ROM_DIR=$PWD/fixture/s0 +EXPECTED=$PWD/fixture/s0/expected.hex +FAULT_CASE=1 > logs/collision_s0.log 2>&1
grep -q TLOAD_COLLISION_REJECT_PASS logs/collision_s0.log && echo "PASS collision" || { echo "FAIL collision"; ok=0; }
# mutants: mutant id, fault case, fail regex
while read m fc re; do
  "obj$m/Vtb_qfd_dv_slice_tload" +OT_ROM_DIR=$PWD/fixture/s0 +EXPECTED=$PWD/fixture/s0/expected.hex +FAULT_CASE=$fc > witness/mut$m.log 2>&1
  rc=$?
  if [ $rc != 0 ] && grep -qE "$re" witness/mut$m.log; then echo "MUT $m FAIL_AS_EXPECTED $(grep -oE "$re" witness/mut$m.log | head -1)"; else echo "MUT $m ESCAPED rc=$rc"; ok=0; fi
done <<'MUTS'
1 1 TLOAD_COLLISION_WRITE_NOT_SUPPRESSED
2 0 TLOAD_(EDGE_MISMATCH|UNEXPECTED_FAULT join=1)
3 1 TLOAD_COLLISION_FAULT_AGE
4 0 TLOAD_EDGE_MISMATCH
5 0 TLOAD_(EDGE_MISMATCH|SHARED_HEAD_CLOBBER|BTAB_MISMATCH|UNEXPECTED_FAULT join=0 vm=1)
MUTS
[ $ok = 1 ] && echo F16_TLOAD_JOIN_FUNCTIONAL_PASS || { echo F16_TLOAD_JOIN_FUNCTIONAL_FAIL; exit 1; }
