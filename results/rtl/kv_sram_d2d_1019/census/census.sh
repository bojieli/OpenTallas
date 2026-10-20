#!/bin/bash
# KV-SRAM-D2D native transparent census of qkd_d2d_static_sfm / _ovl_sfm (same flow as kv-d2d-1019 census: ORFS keep hook,
# OT_RST_COPIES_MAX 24, proc/opt-full/techmap/opt-full + native DFF/INV, BUF/INV-transparent terminal loads)
O=/srv/opentallas-scratch/claude/kv-d2d-1019/census
S=/srv/opentallas-scratch/claude/kv-sram-d2d-1019
Y=$HOME/.local/opentallas-tools/yosys-0.68/bin/yosys
mkdir -p $S/census && cd $S/census
cp $O/transparent.py $O/invmap.v . ; ln -sfn $O/libs libs; ln -sfn $S/src/physical/common_flow common_flow
sed -e 's#rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_dies_sfo.sv#rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_dies_sfo.sv rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_sfm.sv#' \
    -e 's#physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2_bb.v#physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2_bb.v physical/asap7_memory_macros_v2/d2d_sram_1r1w_64x137_m1_r2c2_p192/d2d_sram_1r1w_64x137_m1_r2c2_p192_bb.v#' \
    -e 's#-chparam SAFE_RC 1#-chparam SAFE_RC 1 -chparam SRAMV 1 -chparam FEG 1#' $O/synth.tcl > synth.tcl
grep -q ot_qwen_d2d_sfm.sv synth.tcl && grep -q SRAMV synth.tcl || { echo "synth.tcl patch failed"; exit 3; }
for top in qkd_d2d_static_sfm qkd_d2d_static_ovl_sfm; do
 ( mkdir -p $top && cd $top && ln -sfn ../common_flow common_flow && ln -sfn ../libs libs && ln -sfn ../invmap.v invmap.v && \
   TOP=$top SRCROOT=$S/src RSTMAX=24 OUT=$top $Y -c ../synth.tcl > synth.log 2>&1; echo "synth exit $?"; \
   python3 ../transparent.py $top.json $top > roles.json; echo "roles exit $?" ) > $top.txt 2>&1 &
done
wait
for top in qkd_d2d_static_sfm qkd_d2d_static_ovl_sfm; do echo "== $top"; cat $top.txt; python3 - $top/roles.json <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
print('max',d['max'],'violations',len(d['violations']),'over24',len(d['rows_over24']))
for r in sorted(d['violations'],key=lambda r:-r['terminal_loads'])[:20]: print(' VIOL',r['terminal_loads'],r['role'],r['name'],r['driver'][1])
PY
done
