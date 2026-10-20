#!/bin/bash
set -euo pipefail
O=$1; MODE=${2:-all};mkdir -p "$O"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$V" --version > "$O/verilator.version"
KINDS="pass mutant"; [ "$MODE" = all ] || KINDS="$MODE"
for kind in $KINDS;do
 D=(); EXTRA=(); if [ "${BTAB_S3:-0}" = 1 ];then D+=(-DBTAB_S3);EXTRA+=(rtl/qwen_dv/s5/qfd_dv_s5_btab_s3.sv);fi
[ "$kind" = pass ] || D+=(-DOT_S5_BTAB_MUT)
 "$V" --binary -O1 -j 4 -Wno-fatal -Wno-lint -Wno-style "${D[@]}" --top-module tb_btab_safe rtl/qwen_dv/s5/qfd_dv_s5_btab_safe.sv "${EXTRA[@]}" rtl/test/qwen_dv/s5/tb_btab_safe.sv rtl/test/full_sm_service/sram_models.sv -Mdir "$O/obj_$kind" > "$O/build_$kind.log" 2>&1
 if [ "$MODE" = mutant ];then exec "$O/obj_$kind/Vtb_btab_safe";fi
 set +e
 "$O/obj_$kind/Vtb_btab_safe" > "$O/run_$kind.log" 2>&1
 rc=$?
 set -e
 echo "$kind exit=$rc"
 if [ "$kind" = pass ];then grep -q 'BTAB_EQ PASS' "$O/run_$kind.log";else grep -q 'BTAB_EQ FAIL' "$O/run_$kind.log";test "$rc" -ne 0;fi
 cat "$O/run_$kind.log"
done
