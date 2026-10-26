#!/usr/bin/env bash
# S81-HEAD (10-24): census-safe ot_s81hd_elem == CLOSED-view RTL ot_dsrom_head_elem@f11f3cc47, cycle lockstep.
#   hd_elem_eq.sh OUTDIR A|B CUT SPLIT9          (cwd = repo root, Verilator 5.050)
# A = LV 8 PAD 0 JOIN 1 ROWS 32 (ROM image ga0), B = LV 6 PAD 2 JOIN 0 ROWS 128 (image gb).  Runs MODE 0 (protocol,
# 3 positions) and MODE 1 (stress, 3 seeds).  Last line EQ_BENCH_PASS / EQ_BENCH_FAIL; exit 0 only on PASS.
set -u
O=$(realpath -m "${1:?outdir}"); E=${2:?A|B}; CUT=${3:?cut}; S9=${4:?split9}; mkdir -p "$O"
IMG=$(realpath results/rtl/s81_head_tile_1021/img)
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
$V --version
git show f11f3cc47940002283d1dfcd2de63b6bcfb57f20:rtl/v41rom/ot_dsrom_head_elem.sv \
  | sed 's/\bmodule ot_dsrom_head_elem\b/module ot_dsrom_head_elem_f11/' > $O/ot_dsrom_head_elem_f11.sv
if [ $E = A ]; then G="-GLV=8 -GPAD=0 -GJOIN=1 -GROWS=32 -GINSTANCE='\"ga0\"'"; else G="-GLV=6 -GPAD=2 -GJOIN=0 -GROWS=128 -GINSTANCE='\"gb\"'"; fi
SRCS="rtl/common/ot_prefix.sv rtl/v41rom/ot_v41_fadd.sv rtl/v41rom/ot_v41_bmul2.sv rtl/v41rom/ot_dsrom_bmul3.sv rtl/hdc/ot_hdc_delay.sv
 physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8.v rtl/dsrom_sys/s81_head/ot_s81hd_elem.sv $O/ot_dsrom_head_elem_f11.sv
 rtl/dsrom_sys/s81_head/test/tb_s81hd_elem_eq.sv"
OBJ=$O/obj_${E}_${CUT}_${S9}
eval $V --binary --timing -O1 -Wno-fatal -Wno-lint -Wno-style --top-module tb_s81hd_elem_eq $G -GCUT=$CUT -GSPLIT9=$S9 \
  -Mdir $OBJ $SRCS --build-jobs ${J:-8} -MAKEFLAGS \"OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0\" > $O/build_${E}_${CUT}_${S9}.log 2>&1 \
  || { grep -m10 %Error $O/build_${E}_${CUT}_${S9}.log; echo "BUILD_FAILED"; exit 3; }
ok=0; n=0
run() { local N=$1; shift; n=$((n+1)); $OBJ/Vtb_s81hd_elem_eq +OT_ROM_DIR=$IMG "$@" > $O/run_${E}_${CUT}_${S9}_$N.log 2>&1
  tail -1 $O/run_${E}_${CUT}_${S9}_$N.log | sed "s/^/$N: /"; grep -q '^EQ_PASS' $O/run_${E}_${CUT}_${S9}_$N.log && ok=$((ok+1)); }
run proto +MODE=0 +CYCLES=27000
for s in 1 2; do run stress$s +MODE=1 +CYCLES=40000 +SEED=$s; done
run stress_inf +MODE=1 +CYCLES=40000 +SEED=3 +XFIN=0
[ $ok = $n ] && { echo "EQ_BENCH_PASS elem=$E CUT=$CUT SPLIT9=$S9 ($ok/$n)"; exit 0; }
echo "EQ_BENCH_FAIL elem=$E CUT=$CUT SPLIT9=$S9 ($ok/$n)"; exit 1
