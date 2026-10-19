#!/bin/bash
set -uo pipefail
cd "$(dirname "$0")/../../.."
verilator --version
verilator --version | grep -q '5.050' || exit 2
rc=0
for pair in '64 0' '32 0' '16 0' '64 1' '64 2' '64 3' '64 4' '64 5'; do
 read -r ne mut <<< "$pair"
 tag=n${ne}m${mut}
 mkdir -p "out/$tag"
 verilator --binary --timing -j 4 -Wno-fatal --top-module tb_sysface_sram_players -GNE="$ne" -GMUT="$mut" --Mdir "out/$tag" rtl/test/qwen_split/tb_sysface_sram_players.sv rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_static.sv rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_cal_sram.sv physical/asap7_memory_macros/ot_sram_1r1w_64x16_m1/ot_sram_1r1w_64x16_m1.v > "$tag.build.log" 2>&1
 if [ "$?" -ne 0 ]; then tail -20 "$tag.build.log";rc=1;continue;fi
 "out/$tag/Vtb_sysface_sram_players" > "$tag.run.log" 2>&1
 if [ "$mut" -eq 0 ];then grep -q 'SYSFACE_SRAM PASS' "$tag.run.log" || rc=1;else grep -q 'SYSFACE_SRAM FAIL' "$tag.run.log" || rc=1;fi
 tail -10 "$tag.run.log"
done
echo MATRIX_RC=$rc
exit "$rc"
