#!/usr/bin/env bash
set -eu
src=${1:?pinnedsource};out=${2:?output}
mkdir -p "$out"
for mut in GOLDEN MUT_OWNER MUT_ORDER MUT_WRITTEN MUT_ID_BOUND MUT_PROGRESS;do
 flags=();if [ "$mut" != GOLDEN ];then flags=(-P "tb_hgi_coll_row_formatter.$mut=1");fi
 iverilog -g2012 -s tb_hgi_coll_row_formatter "${flags[@]}" -o "$out/$mut.vvp" "$src/rtl/hbm_accel/generic/collective/ot_hgi_coll_row_formatter.sv" "$src/rtl/hbm_accel/generic/collective/tb_hgi_coll_row_formatter.sv"
 set +e
 vvp "$out/$mut.vvp" > "$out/$mut.log" 2>&1
 rc=$?
 set -e
 if [ "$mut" = GOLDEN ];then test "$rc" -eq 0;grep -q 'PASS HGI ROW_GATHER' "$out/$mut.log";
 else test "$rc" -ne 0;grep -q 'FATAL:' "$out/$mut.log";fi
done
sha256sum "$src/rtl/hbm_accel/generic/collective/ot_hgi_coll_row_formatter.sv" "$src/rtl/hbm_accel/generic/collective/tb_hgi_coll_row_formatter.sv" > "$out/source.sha256"
