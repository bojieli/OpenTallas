#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")/../.."
python3 tools/hgi_sum96_20261009/make_vectors.py gate || exit $?
cd gate
common=(../rtl/hdc/ot_hdc_prefix.sv ../rtl/hdc/ot_hdc_fp32_add_lat.sv ../rtl/hbm_accel/generic_sum96_20261009/ot_hgi_sum96_final_tree.sv ../rtl/hbm_accel/generic_sum96_20261009/tb_sum96_final_tree.sv)
for mode in positive wrongtree drop;do
 defs=();if [ "$mode" = wrongtree ];then defs=(-DMUTANT_TREE);fi
 if [ "$mode" = drop ];then defs=(-DMUTANT_DROP);fi
 /usr/bin/time -v -o "$mode.compile.time" iverilog -g2012 "${defs[@]}" -s tb_sum96_final_tree -o "$mode.vvp" "${common[@]}" > "$mode.compile.log" 2>&1
 build=$?;if [ "$build" -ne 0 ];then echo "$mode build=$build";exit "$build";fi
 /usr/bin/time -v -o "$mode.run.time" vvp "$mode.vvp" > "$mode.run.log" 2>&1
 rc=$?;echo "$mode build=$build runtime=$rc"
 if [ "$mode" = positive ] && [ "$rc" -ne 0 ];then exit "$rc";fi
 if [ "$mode" != positive ] && [ "$rc" -eq 0 ];then exit 10;fi
done
