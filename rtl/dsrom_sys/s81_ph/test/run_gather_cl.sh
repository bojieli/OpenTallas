#!/bin/bash
# run_gather_cl.sh <src root> <out dir> [trace_all.json] [layers] : tb_s81ph_gather_cl (Verilator 5.050), s81-gather.
# The gather CLUSTER (32 hardened 4-root leaves with the SRAM macro models + dsfd_gth_ctl) in lockstep with the FLAT
# dsfd_sp_gather_c: rows equal every cycle after the stated shift c + k - 2, control lane / t_xgo / c_done / c_st equal
# every cycle.  base (PASS): the real field order of each layer in <layers> (trace of root_open_rows.py with
# --trace-regions all), stress, and ovf (EXPECT 1: capacity fault, fail closed).  refuse: ovf stimulus with the
# coverage demand -> REFUSED.  Mutants, each must FAIL: lanes of roots 0 / 1 swapped (S81PH_GTH_CL_MUT_LANE), chain
# slots swapped in the leaf (S81PH_MUT_CHAIN), no entry forwarding in the root (S81PH_MUT_NOFWD), wrong phase on t_xgo
# (S81PH_MUT_XGO), slot overflow not detected (S81PH_MUT_OVF, on ovf).  Verdict: GATHER_CL_GATE PASS|FAIL.
set -u
SRC=$1; OUT=$2; TRACE=${3:-}; LAYERS=${4:-"0 2 14"}
VL=${VL:-verilator}; J=${J:-16}; MODES=${MODES:-"base lane chain nofwd xgo ovf"}
LOCAL_DEF=""
if [ "${LOCAL_BANKS:-0}" = 1 ]; then
 LOCAL_DEF="+define+S81PH_GTH_LOCAL_BANKS"
 if [ -z "${RAW:-}" ]; then MODES="$MODES heap"; fi
fi
if [ "${SSA2:-0}" = 1 ]; then
 LOCAL_DEF="$LOCAL_DEF +define+S81PH_GTH_SSA2"
 if [ -z "${RAW:-}" ]; then MODES="$MODES decision own_co"; fi
fi
mkdir -p $OUT
P=$SRC/rtl/dsrom_sys/s81_ph; M=$SRC/physical/s81_ph_views/macros; C=$SRC/rtl/dsrom_sys/s81_ctrl
FILES="$SRC/rtl/lib/ot_reset_sync.sv $SRC/rtl/lib/ot_async_fifo.sv $SRC/rtl/common/ot_ratio_cdc_fifo.sv
 $SRC/rtl/v41rom/ot_v41_ret.sv $SRC/rtl/proto/ot_fp32_add_rne_pipe.sv $SRC/rtl/hdc/ot_hdc_delay.sv
 $SRC/rtl/hdc/ot_hdc_prefix.sv $SRC/rtl/gpu/ot_fp32_add_rne_deep.sv
 $C/ot_s81_engine_adapter.sv $C/ot_s81_slab_ep.sv
 $P/ot_s81ph_ret_root_p.sv $P/ot_s81ph_root_blk.sv $P/ot_s81ph_root_tile.sv $P/ot_s81ph_gather.sv $P/dsfd_sp_gather.sv
 $P/ctrl_c/dsfd_sp_gather_c.sv
 $P/ot_s81ph_ret_root_s.sv $P/ot_s81ph_root_leaf.sv $P/dsfd_gth_ctl.sv $P/ctrl_c/dsfd_sp_gather_c_cl.sv
 $M/ot_sram_1r1w_128x66_m1_r2c2/ot_sram_1r1w_128x66_m1_r2c2.v $M/ot_sram_1r1w_256x34_m2_r2c2/ot_sram_1r1w_256x34_m2_r2c2.v
 $M/ot_sram_1r1w_512x34_m4_r2c2/ot_sram_1r1w_512x34_m4_r2c2.v
 $P/test/tb_s81ph_gather_cl.sv"
python3 $SRC/tools/s81_ph/gen_gather_cl.py --check || { echo "GATHER_CL_GATE FAIL generated cluster top is stale" | tee $OUT/verdicts.log; exit 1; }
sha256sum $FILES $P/test/gen_gather_cl_stim.py $P/test/gen_root_stim.py $TRACE > $OUT/sources.sha256
G="python3 $P/test/gen_gather_cl_stim.py"
SS=${SS:-8}; SDEF="+define+S81PH_GTH_S=$SS"
if [ "${DIE_CLOCKS:-0}" = 1 ]; then SDEF="$SDEF +define+S81PH_GTH_DIE_CLOCKS"; fi
$G stress 3 $OUT/stress.txt; $G ovf 3 $OUT/ovf.txt --S $SS; $G refuse 3 $OUT/refuse.txt
REAL=""
if [ -n "$TRACE" ]; then for L in $LAYERS; do $G real 0 $OUT/real_L$L.txt --trace $TRACE --layer $L && REAL="$REAL real_L$L"; done; fi
build() {
  $VL --binary --timing -j $J -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-UNOPTFLAT --unroll-count 64 -CFLAGS -O1 \
      +define+S81PH_GTH_CL_NAME=dsfd_sp_gather_c_cl $SDEF $LOCAL_DEF --top-module tb_s81ph_gather_cl $2 --Mdir $OUT/obj_$1 -o sim $FILES > $OUT/build_$1.log 2>&1
}
run() { # mode case expect need want
  $OUT/obj_$1/sim +STIM=$OUT/$2.txt +EXPECT=$3 +NEED=$4 > $OUT/run_$1_$2.log 2>&1
  res=$(grep -h '^RESULT' $OUT/run_$1_$2.log | tail -1)
  [ -z "$res" ] && res="RESULT FAIL (aborted: $(grep -h -m1 -i 'error' $OUT/run_$1_$2.log $OUT/build_$1.log | cut -c1-120))"
  echo "$1 $2 expect=$3 need=$4 want=$5: $res | $(grep -h '^SUMMARY' $OUT/run_$1_$2.log | tail -1)"
}
for m in $MODES; do
  case $m in base) X="";; lane) X="+define+S81PH_GTH_CL_MUT_LANE";; chain) X="+define+S81PH_MUT_CHAIN";; nofwd) X="+define+S81PH_MUT_NOFWD";;
    xgo) X="+define+S81PH_MUT_XGO";; ovf) X="+define+S81PH_MUT_OVF";; heap) X="+define+S81PH_MUT_HEAP_PHASE";; decision) X="+define+S81PH_MUT_DECISION_PHASE";; own_co) X="+define+S81PH_MUT_OWN_CO_PHASE";; esac
  ( build $m "$X" ) &
done
wait
FIRST=$(echo $REAL stress | awk '{print $1}')
{
  for m in $MODES; do
    case $m in
      base) for c in $REAL; do run base $c 0 1 PASS & done; run base stress 0 1 PASS & run base ovf 1 0 PASS &
            run base refuse 0 1 REFUSED & ;;
      ovf)  run ovf ovf 1 0 FAIL & ;;
      lane|nofwd|heap|decision|own_co) run $m stress 0 0 FAIL & ;;     # need root-specific rows / back-to-back same-row partials: the stress case
      *)    run $m $FIRST 0 0 FAIL & ;;
    esac
  done
  wait
} | sort | tee $OUT/verdicts.log
if [ -n "${RAW:-}" ]; then   # raw negative for the closure loop (expect=fail): ONE mutant mode, exit 1 when its run fails in the bench
  if grep -q "RESULT FAIL" $OUT/verdicts.log && ! grep -q "aborted" $OUT/verdicts.log; then echo "GATHER_CL_NEGATIVE FAIL_AS_REQUIRED" | tee -a $OUT/verdicts.log; exit 1; fi
  echo "GATHER_CL_NEGATIVE NOT_DETECTED" | tee -a $OUT/verdicts.log; exit 0
fi
bad=$(awk '{ w=""; for (i=1;i<=NF;i++) if ($i ~ /^want=/) w=substr($i,6); sub(":","",w); r=""; for (i=1;i<=NF;i++) if ($i=="RESULT") r=$(i+1); if (r!=w) print }' $OUT/verdicts.log | wc -l)
n=$(wc -l < $OUT/verdicts.log)
if [ "$bad" -eq 0 ] && [ "$n" -ge 3 ]; then echo "GATHER_CL_GATE PASS ($n runs)" | tee -a $OUT/verdicts.log
else echo "GATHER_CL_GATE FAIL ($bad of $n runs not as wanted)" | tee -a $OUT/verdicts.log; exit 1; fi
