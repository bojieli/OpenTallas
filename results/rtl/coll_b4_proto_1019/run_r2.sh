#!/bin/bash
set -eu
cd /srv/opentallas-scratch/claude/coll-b4-proto-r2-1019/src
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
O=/srv/opentallas-scratch/claude/coll-b4-proto-r2-1019/out
mkdir -p "$O"
for mode in golden r513 banksel; do
 def=()
 case $mode in r513) def=(+define+OT_COLL_B4_MUT_R513);; banksel) def=(+define+OT_COLL_B4_MUT_BANKSEL);; esac
 verilator +define+OT_COLL_B4_NATIVE --binary --timing --top-module tb_ring_b4 -j 8 -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-TIMESCALEMOD "${def[@]}" --Mdir "$O/obj_$mode" rtl/test/qwen_coll_b4/tb_ring_b4.sv rtl/rom/ot_coll_tp8_static.sv rtl/rom/ot_coll_sram_bank64.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1/ot_sram_1r1w_32x64_m1.v physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.v >"$O/build_$mode.log" 2>&1
 rc=0
 "$O/obj_$mode/Vtb_ring_b4" >"$O/$mode.log" 2>&1 || rc=$?
 if [ "$mode" = golden ]; then cat "$O/$mode.log"; test "$rc" = 0; else test "$rc" != 0; grep -Eq "B4_[PR]_DATA" "$O/$mode.log"; echo "B4_RING MUTANT_CAUGHT $mode exit=$rc"; fi
done

export OT_VERILATOR=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
O=/srv/opentallas-scratch/claude/coll-b4-proto-r2-1019
python3 tools/qwen_coll_tp8_static_bench.py --out "$O/core_b4" --latu 65 --lats 390 --qfd --pr-b4 --production
cp "$O/core_b4/record.json" "$O/core_b4/record_production.json"
python3 tools/qwen_coll_tp8_static_bench.py --out "$O/core_b4" --latu 65 --lats 390 --qfd --pr-b4
cp "$O/core_b4/record.json" "$O/core_b4/record_unit.json"
python3 tools/qwen_coll_tp8_static_bench.py --out "$O/default_b2" --latu 53 --lats 378 --qfd --production
