#!/bin/bash
set -euo pipefail
O=${1:?outdir};MODE=${2:-pass};mkdir -p "$O"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$V" --version
ARGS=();case "$MODE" in pass);;bank)ARGS+=(-DOT_S5_BTAB_MUT);;age)ARGS+=(-GMUT_AGE=1);;drop)ARGS+=(-GMUT_DROP=1);;*)exit 2;;esac
SRCS=(rtl/qwen_dv/s5/qfd_dv_s5_btab_safe.sv rtl/qwen_dv/s5/qfd_dv_s5_btab_s4.sv rtl/test/qwen_dv/s5/tb_btab_firstuse.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v)
sha256sum "${SRCS[@]}"
"$V" --binary --timing -O1 -j 4 --x-initial unique --x-assign unique -DOT_MEM_NO_INIT -Wno-fatal -Wno-lint -Wno-style --top-module tb_btab_firstuse "${ARGS[@]}" "${SRCS[@]}" -Mdir "$O/obj" > "$O/build.log" 2>&1
if [ "$MODE" = pass ];then
 for S in 1 17 999;do "$O/obj/Vtb_btab_firstuse" +verilator+rand+reset+2 +verilator+seed+$S > "$O/seed$S.log" 2>&1;grep BTAB_FIRSTUSE_PASS "$O/seed$S.log";done
else
 set +e
 "$O/obj/Vtb_btab_firstuse" +verilator+rand+reset+2 +verilator+seed+17 > "$O/run.log" 2>&1
 R=$?
 set -e
 cat "$O/run.log";test "$R" -ne 0;grep -q BTAB_FIRSTUSE_FAIL "$O/run.log"
fi
