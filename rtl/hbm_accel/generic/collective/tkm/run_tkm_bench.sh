#!/bin/bash
# run_tkm_bench.sh (hgi-1010/k): build and run tb_hgi_coll_tkm (hardware COLL.TOPK_MERGE, ot_hgi_coll_ep TKM = 1).
#   run_tkm_bench.sh <outdir> <vecdir> matrix      every case in <vecdir> (tools/hgi_coll_tkm_vectors.py) + stalls/skew on the
#                                                   production cases + the 4 mutants (each must FAIL on a production case)
#   run_tkm_bench.sh <outdir> <vecdir> quick       base build, every case
#   run_tkm_bench.sh <outdir> <vecdir> mut <N>     mutant N run as a PASS case on syn_sel (must print HGI_TKM FAIL)
# Prints one line per case to <outdir>/SUMMARY ("OK name expect got CYCLES=..."), then "HGI_TKM PASS" / "HGI_TKM FAIL".
set -u
R=$(cd "$(dirname "$0")/../../../../.." && pwd)
O=$(realpath -m "$1"); VEC=$(realpath -m "$2"); MODE=${3:-quick}; mkdir -p "$O/logs"
V=${VERILATOR:-$(ls /home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator 2>/dev/null || echo verilator)}
J=${J:-8}
TKM_SOURCES=()
if [ "${TKM_CLUSTER:-0}" = 1 ]; then
  TKM_SOURCES=(-DOT_TKM_CLUSTER_BENCH rtl/hbm_accel/generic/collective/tkm/ot_hgi_coll_tkm_cluster.sv)
fi
build() {  # build <obj> [verilator -G/-D ...]
  local ob=$O/$1; shift
  ( cd "$R" && $V --binary --timing -j $J -O2 --x-assign fast --x-initial fast -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD \
    -Wno-MULTIDRIVEN -Wno-WIDTHCONCAT --top-module tb_hgi_coll_tkm -Mdir "$ob" -Irtl/hbm_accel/generic "${TKM_SOURCES[@]}" "$@" \
    rtl/hbm_accel/generic/collective/tkm/tb_hgi_coll_tkm.sv rtl/hbm_accel/generic/collective/tkm/ot_hgi_coll_tkm.sv rtl/lib/ot_rst_relay.sv \
    rtl/hbm_accel/generic/collective/rgx/ot_hgi_coll_rgx_src.sv rtl/hbm_accel/generic/collective/rgx/ot_hgi_coll_rgx_sink.sv \
    rtl/hbm_accel/tu/ot_hbm_accel_tu_endpoint_psg.sv rtl/hbm_accel/tu/ot_hcoll_port.sv rtl/hbm_accel/tu/ot_hcoll_sram_prims.sv \
    rtl/hbm_accel/ha2_ar/ot_ha2_prims.sv rtl/link/ot_link_afifo.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv \
    rtl/hdc/ot_hdc_fastfp.sv rtl/model/hbm_pc40_native_sim_20261003/ot_sram_1r1w_128x256_m1_r2c2_sim.sv physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v \
    rtl/hbm_accel/generic/ot_hgi_cfg.sv rtl/hbm_accel/generic/collective/ot_hgi_coll_decode.sv \
    rtl/hbm_accel/generic/collective/ot_hgi_coll_record.sv rtl/hbm_accel/generic/collective/ot_hgi_coll_amerge.sv \
    rtl/hbm_accel/generic/collective/ot_hgi_coll_ep.sv > "$ob.build.log" 2>&1 ) || echo "BUILD FAIL $ob" >> "$O/SUMMARY"
}
run() {  # run <name> <PASS|FAIL> <obj> <case> args...
  local n=$1 e=$2 o=$3 c=$4; shift 4
  "$O/$o/Vtb_hgi_coll_tkm" +DIR="$VEC/$c" "$@" > "$O/logs/$n.log" 2>&1
  if grep -q "^PASS tb_hgi_coll_tkm" "$O/logs/$n.log"; then r=PASS; else r=FAIL; fi
  local cy; cy=$(grep -o "CYCLES=[0-9]* SURV=[0-9]* INS=[0-9]* SINK=[0-9]*" "$O/logs/$n.log")
  local why; why=$(grep -m1 -o "FAIL.*" "$O/logs/$n.log" | cut -c1-140)
  [ "$r" = "$e" ] && v=OK || v=WRONG
  echo "$v $n expect=$e got=$r $cy $why | $c $*" >> "$O/SUMMARY"
}
: > "$O/SUMMARY"
cases=$(cd "$VEC" && ls -d */ | tr -d /)
case $MODE in
mut)   # mut <N>: mutant N on syn_sel as an ordinary PASS case -> the run must end "HGI_TKM FAIL" (closure-loop fail stage)
  m=${4:-1}; build obj_mut$m -GMUT_TKM=$m
  run mut${m}_syn_sel PASS obj_mut$m syn_sel ;;
quick)
  build obj_base
  for c in $cases; do run $c PASS obj_base $c & done; wait ;;
matrix)
  build obj_base & build obj_mut1 -GMUT_TKM=1 & build obj_mut2 -GMUT_TKM=2 & build obj_mut3 -GMUT_TKM=3 & build obj_mut4 -GMUT_TKM=4 & wait
  for c in $cases; do run $c PASS obj_base $c & done
  for c in $(cd "$VEC" && ls -d prod_* syn_sel syn_cand 2>/dev/null | tr -d /); do
    run ${c}_wstall30 PASS obj_base $c +WSTALL=30 +SEED=3 &
    run ${c}_skew60 PASS obj_base $c +SKEW=60 +SEED=5 &
  done
  wait
  P=$(cd "$VEC" && ls -d prod_sel_* 2>/dev/null | head -1 | tr -d /); P=${P:-syn_sel}
  for m in 1 2 3 4; do run mut${m}_$P FAIL obj_mut$m $P & done
  wait ;;
esac
if grep -q "^WRONG\|BUILD FAIL" "$O/SUMMARY"; then echo "HGI_TKM FAIL" >> "$O/SUMMARY"; else echo "HGI_TKM PASS" >> "$O/SUMMARY"; fi
cat "$O/SUMMARY"
