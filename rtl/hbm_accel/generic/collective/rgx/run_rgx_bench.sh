#!/bin/bash
# run_rgx_bench.sh (hgi-1010/a): build and run tb_hgi_coll_rgx (hardware COLL.ROW_GATHER, spec G25) from the repo root.
#   run_rgx_bench.sh <outdir> matrix          full PASS matrix + the 5 mutants (each must FAIL) + DEL 8 + record mode
#   run_rgx_bench.sh <outdir> quick           base build: G96 K512 dest / non-dest / stalls / K2048
#   run_rgx_bench.sh <outdir> mut <NAME>      one mutant build (SLOT, OMAJ, DUP, CREDIT, NOGATE) on its trigger case
# Prints one line per case to <outdir>/SUMMARY ("OK name expect got CYCLES=..."), and "HGI_RGX PASS" / "HGI_RGX FAIL".
# Verilator 5 (--binary --timing); the record-mode build needs 5.050 (5.032 aborts in V3 on it): VERILATOR overrides.
set -u
R=$(cd "$(dirname "$0")/../../../../.." && pwd)
O=$(realpath -m "$1"); MODE=${2:-quick}; mkdir -p "$O/logs"
V=${VERILATOR:-$(ls /home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator 2>/dev/null || echo verilator)}
build() {  # build <obj> [verilator -G/-D ...]
  local ob=$O/$1; shift
  ( cd "$R" && $V --binary --timing -j 8 -O3 --x-assign fast --x-initial fast -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD \
    -Wno-MULTIDRIVEN --top-module tb_hgi_coll_rgx -Mdir "$ob" -Irtl/hbm_accel/generic "$@" \
    rtl/hbm_accel/generic/collective/rgx/tb_hgi_coll_rgx.sv rtl/hbm_accel/generic/collective/rgx/ot_hgi_coll_rgx.sv \
    rtl/hbm_accel/generic/collective/rgx/ot_hgi_coll_rgx_src.sv rtl/hbm_accel/generic/collective/rgx/ot_hgi_coll_rgx_sink.sv \
    rtl/hbm_accel/tu/ot_hbm_accel_tu_endpoint_psg.sv rtl/hbm_accel/tu/ot_hcoll_port.sv rtl/hbm_accel/tu/ot_hcoll_sram_prims.sv \
    rtl/hbm_accel/ha2_ar/ot_ha2_prims.sv rtl/link/ot_link_afifo.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv \
    rtl/hdc/ot_hdc_fastfp.sv rtl/model/hbm_pc40_native_sim_20261003/ot_sram_1r1w_128x256_m1_r2c2_sim.sv \
    rtl/hbm_accel/generic/ot_hgi_cfg.sv rtl/hbm_accel/generic/collective/ot_hgi_coll_decode.sv \
    rtl/hbm_accel/generic/collective/ot_hgi_coll_record.sv rtl/hbm_accel/generic/collective/ot_hgi_coll_amerge.sv \
    rtl/hbm_accel/generic/collective/ot_hgi_coll_ep.sv > "$ob.build.log" 2>&1 ) || echo "BUILD FAIL $ob" >> "$O/SUMMARY"
}
run() {  # run <name> <PASS|FAIL> <obj> args...
  local n=$1 e=$2 o=$3; shift 3
  "$O/$o/Vtb_hgi_coll_rgx" "$@" > "$O/logs/$n.log" 2>&1
  if grep -q "^PASS tb_hgi_coll_rgx" "$O/logs/$n.log"; then r=PASS; else r=FAIL; fi
  local c; c=$(grep -o "RUN 0 PASS.*CYCLES=[0-9]*" "$O/logs/$n.log" | grep -o "M=[0-9]* own=[0-9]*\|CYCLES=[0-9]*" | tr '\n' ' ')
  local why; why=$(grep -m1 -o "FAIL.*" "$O/logs/$n.log" | cut -c1-140)
  [ "$r" = "$e" ] && v=OK || v=WRONG
  echo "$v $n expect=$e got=$r $c $why | $*" >> "$O/SUMMARY"
}
: > "$O/SUMMARY"
case $MODE in
quick)
  build obj_base
  run g96_dest PASS obj_base +G=96 +RANK=5 +K=512 +SEED=1 &
  run g96_nondest PASS obj_base +G=96 +RANK=77 +K=512 +SEED=4 &
  run g96_stall PASS obj_base +G=96 +RANK=5 +K=512 +STALL=30 +HSTALL=30 +TXSTALL=20 +SEED=7 &
  run g96_k2048 PASS obj_base +G=96 +RANK=0 +K=2048 +K2=512 +SEED=5 &
  wait ;;
mut)
  m=$3; build obj_$m -GMUT_$m=1
  case $m in CREDIT) a="+STALL=60";; NOGATE) a="+SKEW=60 +STALL=60";; *) a="";; esac
  run mut_$m FAIL obj_$m +G=96 +RANK=5 +K=512 +SEED=1 $a ;;
matrix)
  build obj_base & build obj_del8 -GDEL=8 & build obj_rec -DRGX_REC & build obj_recdel8 -DRGX_REC -GDEL=8 &
  for m in SLOT OMAJ DUP CREDIT NOGATE; do build obj_$m -GMUT_$m=1 & done
  wait
  B=obj_base
  for s in 1 2 3; do run g96_dest_s$s PASS $B +G=96 +RANK=5 +K=512 +SEED=$s & done
  run g96_nondest PASS $B +G=96 +RANK=77 +K=512 +SEED=4 &
  run g96_k2048 PASS $B +G=96 +RANK=0 +K=2048 +K2=512 +SEED=5 &
  run g96_k2048_stall PASS $B +G=96 +RANK=40 +K=2048 +K2=33 +STALL=25 +HSTALL=25 +TXSTALL=25 +SEED=6 &
  run g96_stall PASS $B +G=96 +RANK=5 +K=512 +STALL=30 +HSTALL=30 +TXSTALL=20 +SEED=7 &
  run g96_stall50_all PASS $B +G=96 +RANK=95 +DESTS=96 +K=512 +STALL=50 +SEED=8 &
  run g96_skew PASS $B +G=96 +RANK=63 +K=512 +SKEW=50 +STALL=20 +SEED=9 &
  run g96_skew_full PASS $B +G=96 +RANK=12 +K=1024 +SKEW=95 +STALL=10 +HSTALL=10 +SEED=10 &
  run g96_k1 PASS $B +G=96 +RANK=5 +K=1 +K2=2 +SEED=11 &
  run g96_k7 PASS $B +G=96 +RANK=5 +K=7 +K2=512 +SEED=12 &
  run g96_tightsw PASS $B +G=96 +RANK=30 +K=512 +EQCAP=4 +LAT=120 +TXLAT=60 +SEED=13 &
  run g96_b1 PASS $B +G=96 +RANK=5 +K=512 +LB=0 +SEED=14 &
  run g96_b128 PASS $B +G=96 +RANK=5 +K=512 +LB=7 +SEED=15 &
  run g96_sec63 PASS $B +G=96 +RANK=5 +K=512 +SEC=63 +STALL=10 +SEED=16 &
  run g96_sec9 PASS $B +G=96 +RANK=5 +K=512 +SEC=9 +SEED=17 &
  run g96_sec9_k2048 PASS $B +G=96 +RANK=50 +K=2048 +SEC=9 +STALL=20 +SEED=18 &
  run g8 PASS $B +G=8 +RANK=13 +K=512 +STALL=10 +SEED=19 &
  run g8_noforeign PASS $B +G=8 +RANK=13 +K=512 +FOREIGN=0 +SEED=19 &
  run g4 PASS $B +G=4 +RANK=6 +K=256 +HSTALL=20 +SEED=20 &
  run g2 PASS $B +G=2 +RANK=3 +DESTS=1 +K=128 +SEED=21 &
  run g1 PASS $B +G=1 +RANK=9 +K=64 +SEED=22 &
  run g96_del8 PASS obj_del8 +G=96 +RANK=5 +K=512 +SEED=1 &
  run g96_del8_k2048 PASS obj_del8 +G=96 +RANK=0 +K=2048 +K2=512 +SEED=5 &
  run g96_del8_stall PASS obj_del8 +G=96 +RANK=5 +K=512 +STALL=30 +HSTALL=30 +TXSTALL=20 +SEED=7 &
  run rec_g96_dest PASS obj_rec +G=96 +RANK=5 +K=512 +SEED=1 &
  run rec_g96_nondest PASS obj_rec +G=96 +RANK=77 +K=512 +SEED=4 &
  run rec_g96_k2048_stall PASS obj_rec +G=96 +RANK=40 +K=2048 +K2=33 +STALL=25 +HSTALL=25 +TXSTALL=25 +SEED=6 &
  run rec_g96_sec9 PASS obj_rec +G=96 +RANK=5 +K=512 +SEC=9 +STALL=10 +SEED=17 &
  run rec_g8 PASS obj_rec +G=8 +RANK=13 +K=512 +STALL=10 +SEED=19 &
  run rec_g96_skew PASS obj_rec +G=96 +RANK=63 +K=512 +SKEW=50 +STALL=20 +SEED=9 &
  run rec_del8 PASS obj_recdel8 +G=96 +RANK=5 +K=512 +SEED=1 &
  wait
  run mut_slot FAIL obj_SLOT +G=96 +RANK=5 +K=512 +SEED=1 &
  run mut_omaj FAIL obj_OMAJ +G=96 +RANK=5 +K=512 +SEED=1 &
  run mut_dup FAIL obj_DUP +G=96 +RANK=5 +K=512 +SEED=1 &
  run mut_credit FAIL obj_CREDIT +G=96 +RANK=5 +K=512 +STALL=60 +SEED=1 &
  run mut_nogate FAIL obj_NOGATE +G=96 +RANK=5 +K=512 +SKEW=60 +STALL=60 +SEED=1 &
  wait ;;
esac
sort -o "$O/SUMMARY" "$O/SUMMARY"
if grep -q "^OK" "$O/SUMMARY" && ! grep -qv "^OK" "$O/SUMMARY"; then echo "HGI_RGX PASS $(grep -c '^OK' "$O/SUMMARY") cases"; else echo "HGI_RGX FAIL"; grep -v "^OK" "$O/SUMMARY"; fi
