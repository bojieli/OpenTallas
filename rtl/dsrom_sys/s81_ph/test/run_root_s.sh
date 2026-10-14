#!/bin/bash
# run_root_s.sh <src root> <out dir> [trace.json] : tb_s81ph_root_s (Verilator 5.050), s81-gather 2026-10-13.
# ot_s81ph_ret_root_s (flop arrays AND the two SRAM macro models) in cycle-exact lockstep with ot_s81ph_ret_root_p.
# base (PASS): real field order (trace.json of tools/s81_ph/root_open_rows.py, layers / regions it holds), stress x3,
#   full, deep, and the fail-closed cases ovf / bad (root_s faults alone), qfull / dup (both fault).
# refuse: the real stream asked for every coverage event -> RESULT REFUSED (coverage refusal works).
# mutants (each must FAIL): S81PH_MUT_NOFWD (no entry forwarding), S81PH_MUT_WADDR (pairing store write address off by
#   one), S81PH_MUT_CREDIT (dropped read credit), S81PH_MUT_QFWD (no queue write-register forward),
#   S81PH_MUT_OVF (slot overflow not detected: the capacity fault mutant, on the ovf case).
# Verdict line: ROOT_S_GATE PASS|FAIL.   Env: VL (verilator), J (16), S (8).
set -u
SRC=$1; OUT=$2; TRACE=${3:-}
VL=${VL:-verilator}; J=${J:-16}; S=${S:-8}
LOCAL_DEF=""
if [ "${LOCAL_BANKS:-0}" = 1 ]; then LOCAL_DEF="+define+S81PH_GTH_LOCAL_BANKS"; fi
mkdir -p $OUT
P=$SRC/rtl/dsrom_sys/s81_ph; M=$SRC/physical/s81_ph_views/macros
FILES="$SRC/rtl/hdc/ot_hdc_prefix.sv $SRC/rtl/gpu/ot_fp32_add_rne_deep.sv $P/ot_s81ph_ret_root_p.sv $P/ot_s81ph_ret_root_s.sv
 $M/ot_sram_1r1w_128x66_m1_r2c2/ot_sram_1r1w_128x66_m1_r2c2.v $M/ot_sram_1r1w_512x34_m4_r2c2/ot_sram_1r1w_512x34_m4_r2c2.v $M/ot_sram_1r1w_256x34_m2_r2c2/ot_sram_1r1w_256x34_m2_r2c2.v
 $P/test/tb_s81ph_root_s.sv"
sha256sum $FILES $P/test/gen_root_stim.py $TRACE > $OUT/sources.sha256
G="python3 $P/test/gen_root_stim.py"
for s in 1 2 3; do $G stress $s $OUT/stress$s.txt --S $S; done
for c in full deep ovf qfull bad dup; do $G $c 7 $OUT/$c.txt --S $S; done
REAL=""
if [ -n "$TRACE" ]; then
  for lr in $(python3 -c "
import json,sys
d=json.load(open('$TRACE'))['layers']
print(' '.join(f'{L}:{r}' for L in d for r in d[L]['traces'] if d[L]['traces'][r]))"); do
    L=${lr%%:*}; r=${lr##*:}
    $G real 0 $OUT/real_L${L}_r$r.txt --trace $TRACE --layer $L --region $r && REAL="$REAL real_L${L}_r$r"
  done
fi
build() { # mode defines
  $VL --binary --timing -j $J -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-UNOPTFLAT --unroll-count 64 -CFLAGS -O1 \
      --top-module tb_s81ph_root_s -GS=$S $LOCAL_DEF $2 --Mdir $OUT/obj_$1 -o sim $FILES > $OUT/build_$1.log 2>&1
}
run() { # mode case expect need
  $OUT/obj_$1/sim +STIM=$OUT/$2.txt +EXPECT=$3 +NEED=$4 > $OUT/run_$1_$2.log 2>&1
  res=$(grep -h '^RESULT' $OUT/run_$1_$2.log | tail -1)
  [ -z "$res" ] && res="RESULT FAIL (aborted: $(grep -h -m1 'Assertion failed' $OUT/run_$1_$2.log | sed 's/.*Assertion failed in //' | cut -c1-90))"
  echo "$1 $2 expect=$3 need=$4 want=$5: $res | $(grep -h '^SUMMARY' $OUT/run_$1_$2.log | tail -1)"
}
( build base "" ) &
( build nofwd "+define+S81PH_MUT_NOFWD" ) &
( build waddr "+define+S81PH_MUT_WADDR" ) &
( build credit "+define+S81PH_MUT_CREDIT" ) &
( build qfwd "+define+S81PH_MUT_QFWD" ) &
( build ovf "+define+S81PH_MUT_OVF" ) &
if [ "${LOCAL_BANKS:-0}" = 1 ]; then ( build heap "+define+S81PH_MUT_HEAP_PHASE" ) & fi
wait
{
  for c in $REAL; do run base $c 0 16 PASS; done
  for s in 1 2 3; do run base stress$s 0 543 PASS; done      # 1 + 2 + 4 + 8 + 16 + 512
  run base full 0 68 PASS
  run base deep 0 32 PASS
  run base ovf 1 128 PASS
  run base bad 1 1024 PASS
  run base qfull 2 256 PASS
  run base dup 2 2048 PASS
  FIRST=$(echo $REAL stress1 | awk '{print $1}')
  cp $OUT/$FIRST.txt $OUT/refuse.txt; run base refuse 0 4095 REFUSED
  run nofwd stress1 0 0 FAIL
  run waddr stress1 0 0 FAIL
  run credit stress1 0 0 FAIL
  run qfwd stress1 0 0 FAIL
  run ovf ovf 1 0 FAIL
  if [ "${LOCAL_BANKS:-0}" = 1 ]; then run heap stress1 0 0 FAIL; fi
} | tee $OUT/verdicts.log
bad=$(awk '{ w=""; for (i=1;i<=NF;i++) if ($i ~ /^want=/) w=substr($i,6); sub(":","",w); r=""; for (i=1;i<=NF;i++) if ($i=="RESULT") r=$(i+1); if (r!=w) print }' $OUT/verdicts.log | wc -l)
n=$(wc -l < $OUT/verdicts.log)
if [ "$bad" -eq 0 ] && [ "$n" -ge 15 ]; then echo "ROOT_S_GATE PASS ($n runs)" | tee -a $OUT/verdicts.log
else echo "ROOT_S_GATE FAIL ($bad of $n runs not as wanted)" | tee -a $OUT/verdicts.log; exit 1; fi
