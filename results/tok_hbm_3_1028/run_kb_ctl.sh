#!/bin/bash
# TOK-HBM-3 idx provider bench. Usage: run_kb_ctl.sh <repo-root> <scratch-out>. Positive (IDXQ N-row, d4g 1-row, both
# halves, bad-schedule fault) + 4 mutants of the provider that MUST fail. Verilator in docker, 4 GB cap.
set -uo pipefail
ROOT=${1:?repo};OUT=${2:?out};HERE=$ROOT/results/tok_hbm_3_1028
mkdir -p "$OUT";cp "$HERE/tb_idxn_kb_ctl.sv" "$ROOT/rtl/hbm_next/idxn/ot_hnx_idxn_kb_ctl.sv" "$ROOT/rtl/hbm_next/idxn/ot_hnx_idxn_keybuf.sv" \
 "$ROOT/physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v" "$OUT/"
cd "$OUT"
build(){ # $1 = provider file, $2 = obj dir
 docker run --rm -m 4g -e HOME=/tmp -e CCACHE_DISABLE=1 -u $(id -u):$(id -g) -v "$OUT":"$OUT" -w "$OUT" verilator/verilator:v5.032 --binary --timing -O1 -Wno-fatal \
  -Wno-lint -Wno-style -j 8 --top-module tb_idxn_kb_ctl -Mdir "$2" -o sim tb_idxn_kb_ctl.sv "$1" ot_hnx_idxn_keybuf.sv \
  ot_sram_1r1w_256x256_m2_r2c2.v > "$2.build.log" 2>&1 || { echo "BUILD FAIL $1"; tail -5 "$2.build.log"; }
}
sed 's/assign replay_index=key_index;/assign replay_index=pre_index_in;/' ot_hnx_idxn_kb_ctl.sv > m1.sv   # replay index from PRE (one edge skew)
sed 's/assign live_v=key_v&&key_row==5.d0;/assign live_v=key_v;/' ot_hnx_idxn_kb_ctl.sv > m2.sv            # live on every row
sed 's/assign replay_v=key_v&&key_row!=5.d0;/assign replay_v=1'"'"'b0;/' ot_hnx_idxn_kb_ctl.sv > m3.sv       # never replay
sed 's/assign clear=frame_start;/assign clear=1'"'"'b0;/' ot_hnx_idxn_kb_ctl.sv > m4.sv                       # never clear
for m in pos m1 m2 m3 m4; do f=$m.sv; [ $m = pos ] && f=ot_hnx_idxn_kb_ctl.sv; [ -x obj_$m/sim ] || build $f obj_$m & done; wait
: > positive.log
for s in 1 2 3; do for a in "" "+D4G" "+HALF" "+D4G +HALF" "+BAD" "+BAD +HALF"; do echo "## SEED=$s $a" >> positive.log; obj_pos/sim +SEED=$s $a | grep KB_CTL >> positive.log; done; done
cat positive.log
: > mutant.log
for m in m1 m2 m3 m4; do cmp -s $m.sv ot_hnx_idxn_kb_ctl.sv && { echo "$m NOT APPLIED" >> mutant.log; continue; }
 [ -x obj_$m/sim ] || { echo "$m BUILD_FAIL" >> mutant.log; continue; }; r=$( { obj_$m/sim +SEED=1; obj_$m/sim +SEED=1 +BAD; } | grep -c "KB_CTL FAIL")
 echo "$m fails=$r/2 $( [ "$r" -ge 1 ] && echo CAUGHT || echo MISSED)" >> mutant.log; done
cat mutant.log
