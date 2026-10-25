#!/usr/bin/env bash
# S81-HEAD HD-TILE (10-21): ot_s81hd_tile / spo / spr mini-array bench (cwd = repo root, Verilator 5.050).
#   hd_tile_bench.sh OUTDIR SCEN [MUT]
#   SCEN A    t0 = rows 21888.. (ten 1), t1 = rows 22016.. (ten 1), 2 positions: golden argmax 21946 / 4173a558, cycles
#        B    t0 = rows 22016.. (ten 1), t1 = rows 21888.. (ten 0): 22141 / 40cdce35 (the golden bundle is excluded)
#        C    t0 = rows 21888.. row0 21888, t1 = the same image with strap row0 21760: equal logits, lowest id 21818 wins
#        D    as A with one x slice lane at BF16 +Inf: the bundle faults, flt = 1 must reach the spr output
#        ALL  A B C D on one build
#   MUT  none | TIE_FLIP | GO_DROP | TEN_IGNORED | FLT_DROP (ot_s81hd_tile) | SKEW_LANE (bundle A_SKEW_LINES) | SPO_OW_DROP (spo) | SPR_EARLY (spr)
#        (+define+OT_S81HD_MUT_<MUT>)
# Images: results/rtl/s81_head_tile_1021/img (tools/s81_head/hd_tile_images.py, released head.weight + golden x of the 1M
# token).  Last line BENCH_PASS / BENCH_FAIL; exit 0 only on BENCH_PASS.
set -u
O=$(realpath -m "${1:?outdir}"); SC=${2:?scen}; M=${3:-none}; mkdir -p "$O"
IMG=$(realpath results/rtl/s81_head_tile_1021/img)
# 10-24: CUT (decimal, default 511 = 0x1ff) / SPLIT9 (default 1) env select the element pipeline (default = the closed
# element views, SK 11; CUT=379 SPLIT9=0 = the 10-21 0x17b point, SK 8); SK != 8 re-skews the images into OUTDIR/img_skN.
CUT=${CUT:-511}; S9=${SPLIT9:-1}; SKV=$(python3 -c "print(1+bin($CUT).count('1')+$S9)")
if [ $SKV != 8 ]; then
  [ -f $O/img_sk$SKV/hb_1.viamap.hex ] || python3 tools/s81_head/hd_reskew_images.py $IMG $O/img_sk$SKV --from 8 --to $SKV > $O/reskew.log || exit 4
  IMG=$O/img_sk$SKV
fi
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
$V --version
SRCS="rtl/common/ot_prefix.sv rtl/v41rom/ot_v41_fadd.sv rtl/v41rom/ot_v41_bmul2.sv rtl/v41rom/ot_dsrom_bmul3.sv rtl/hdc/ot_hdc_delay.sv
 physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8.v
 rtl/dsrom_sys/s81_head/ot_s81hd_elem.sv rtl/dsrom_sys/s81_head/ot_s81hd_oreg.sv rtl/dsrom_sys/s81_head/ot_s81hd_elem_cv.sv rtl/dsrom_sys/s81_head/ot_s81hd_bundle.sv rtl/dsrom_sys/s81_head/ot_s81hd_tile.sv
 rtl/dsrom_sys/s81_head/ot_s81hd_spo.sv rtl/dsrom_sys/s81_head/ot_s81hd_spr.sv rtl/dsrom_sys/s81_head/test/tb_s81hd_mini.sv"
D=""; [ "$M" != none ] && D="+define+OT_S81HD_MUT_$M"
CV=${CV:-0}   # 10-24: CV=1 = elements as the closed-view macro models (ot_s81hd_bundle CV)
# 10-24: AIS / MH / CS env = tile A_INPUT_STAGES / MERGE_HOP / CMP_STAGES (default 0 = unchanged)
AIS=${AIS:-0}; MH=${MH:-0}; CS=${CS:-0}
# 10-24 (S81/HEAD2): ASL / BDH env = tile A_SKEW_LINES / BD_HOPS (per-A-core transport lines; 0 = unchanged)
ASL=${ASL:-0}; BDH=${BDH:-0}
OBJ=$O/obj_${M}_${CUT}_${S9}_cv${CV}_a${AIS}m${MH}c${CS}s${ASL}b${BDH}
if [ ! -x $OBJ/Vtb_s81hd_mini ]; then
  $V --binary --timing -O1 -Wno-fatal -Wno-lint -Wno-style $D --top-module tb_s81hd_mini -GCUT=$CUT -GSPLIT9=$S9 -GCV=$CV -GAIS=$AIS -GMH=$MH -GCS=$CS -GASL=$ASL -GBDH=$BDH -Mdir $OBJ $SRCS --build-jobs ${J:-8} \
    -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > $O/build_$M.log 2>&1 || { grep -m10 %Error $O/build_$M.log; echo "BUILD_FAILED $M"; exit 3; }
fi
link() {   # link DIR T SRC: tile T's ROM instances -> image prefix SRC
  for e in a0 a1 a2 a3 b; do for k in 0 1; do ln -sf $IMG/$3${e}_$k.viamap.hex $1/$2${e}_$k.viamap.hex; done; done
}
EXP_CYC_A=${EXP_CYC_A:-$([ $CUT = 379 ] && [ $S9 = 0 ] && echo 8375 || { [ $CV = 1 ] && echo 8432 || echo 8430; })}
# 10-24 pipelining: + BD_LAT (S81/HEAD2: measured tail cost of BD_HOPS, default 0) + AIS (A input stages) + 2 MH (bundle merge hops) + CS per tile on the 2-tile chain
EXP_CYC_A=${EXP_CYC_X:-$((EXP_CYC_A + AIS + 2*MH + 2*CS + ${BD_LAT:-0}))}  # +1 bundle pk_q stage (10-24 GEOM-REVIEW); CV 1: +2 more = the rebuilt elemB then elemA output register stages (ot_s81hd_oreg)
  # 8,429 at 0x1ff / SPLIT9 1 (10-24)   # measured go (spo input) -> spr output, 2-tile chain: bundle 8,357 (IOREG 1, SAFE 1: +2) + spo 1 + pin 1 + fire 2 x 2 + spr 5 + chain hop
run() {    # run NAME T0SRC T1SRC args...
  local N=$1 a=$2 b=$3; shift 3; local W=$O/scen_${N}_$M; mkdir -p $W
  ln -sf $IMG/xa.hex $W/xa.hex; ln -sf $IMG/xb.hex $W/xb.hex; link $W t0 $a; link $W t1 $b
  $OBJ/Vtb_s81hd_mini +DIR=$W +OT_ROM_DIR=$W "$@" > $O/run_${N}_$M.log 2>&1
  grep -E "^(POS|TB_PASS|TB_FAIL|%Error|.*readmem)" $O/run_${N}_$M.log | sed "s/^/$N: /" | head -12
  grep -q "^TB_PASS" $O/run_${N}_$M.log
}
ok=0; n=0
for s in $( [ "$SC" = ALL ] && echo "A B C D" || echo $SC ); do
  n=$((n+1))
  case $s in
  A) run A h g +ROW0_0=21888 +ROW0_1=22016 +NPOS=2 +EXP_ROW=21946 +EXP_BITS=4173a558 +EXP_FLT=0 +EXP_CYC=$EXP_CYC_A && ok=$((ok+1)) ;;
  B) run B g h +ROW0_0=22016 +ROW0_1=21888 +TEN1=0 +EXP_ROW=22141 +EXP_BITS=40cdce35 +EXP_FLT=0 && ok=$((ok+1)) ;;
  C) run C h h +ROW0_0=21888 +ROW0_1=21760 +EXP_ROW=21818 +EXP_BITS=4173a558 +EXP_FLT=0 && ok=$((ok+1)) ;;
  D) run D h g +ROW0_0=21888 +ROW0_1=22016 +XINF_M=100 +EXP_ROW=-1 +EXP_FLT=1 && ok=$((ok+1)) ;;
  *) echo "unknown scenario $s"; exit 2 ;;
  esac
done
[ $ok = $n ] && { echo "BENCH_PASS s81hd_mini SCEN=$SC MUT=$M CUT=$CUT SPLIT9=$S9 CV=$CV AIS=$AIS MH=$MH CS=$CS ASL=$ASL BDH=$BDH ($ok/$n)"; exit 0; }
echo "BENCH_FAIL s81hd_mini SCEN=$SC MUT=$M CUT=$CUT SPLIT9=$S9 CV=$CV AIS=$AIS MH=$MH CS=$CS ASL=$ASL BDH=$BDH ($ok/$n)"; exit 1
