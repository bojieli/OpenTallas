#!/usr/bin/env bash
# INFRA-FIRST-HEAD-4 (10-27): measured head switching activity. Runs the hd_tile mini-array bench scenario A
# (tb_s81hd_mini: 2 hd_tiles x (4 elemA + 1 elemB), released head.weight images + golden x of the 1M token, 2 positions =
# one full head pass) with Verilator --trace (VCD of one elemA + one elemB instance of tile t0; Verilator --coverage-toggle
# over-counts wide vectors -- e.g. a 256-bit posedge register at 3.8 transitions/cycle -- so it is NOT used).
#   head_activity_sim.sh OUTDIR     (cwd = repo root; Verilator 5.050; default CUT 511 / SPLIT9 1 = the closed element views)
set -u
O=$(realpath -m "${1:?outdir}"); mkdir -p "$O"
IMG=$(realpath results/rtl/s81_head_tile_1021/img)
# CUT 511 / SPLIT9 1 = skew 11 (hd_tile_bench.sh): re-skew the SK8 images exactly as the bench does
[ -f $O/img_sk11/hb_1.viamap.hex ] || python3 tools/s81_head/hd_reskew_images.py $IMG $O/img_sk11 --from 8 --to 11 > $O/reskew.log || exit 4
IMG=$O/img_sk11
V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
SRCS="rtl/common/ot_prefix.sv rtl/v41rom/ot_v41_fadd.sv rtl/v41rom/ot_v41_bmul2.sv rtl/v41rom/ot_dsrom_bmul3.sv rtl/hdc/ot_hdc_delay.sv
 physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8.v
 rtl/dsrom_sys/s81_head/ot_s81hd_elem.sv rtl/dsrom_sys/s81_head/ot_s81hd_oreg.sv rtl/dsrom_sys/s81_head/ot_s81hd_elem_cv.sv rtl/dsrom_sys/s81_head/ot_s81hd_bundle.sv rtl/dsrom_sys/s81_head/ot_s81hd_tile.sv
 rtl/dsrom_sys/s81_head/ot_s81hd_spo.sv rtl/dsrom_sys/s81_head/ot_s81hd_spr.sv $O/tb_s81hd_mini_vcd.sv"
OBJ=$O/obj_vcd
sed 's|^\(\s*initial begin #400000;\)|    initial begin $dumpfile("'$O'/elem.vcd"); $dumpvars(0, tb_s81hd_mini.u_t0.u_b.g_a[0].g_rtl.u_e); $dumpvars(0, tb_s81hd_mini.u_t0.u_b.g_rtlb.u_b); end\n\1|' rtl/dsrom_sys/s81_head/test/tb_s81hd_mini.sv > $O/tb_s81hd_mini_vcd.sv
grep -q dumpvars $O/tb_s81hd_mini_vcd.sv || { echo NO_DUMP_HOOK; exit 5; }
$V --version
[ -x $OBJ/Vtb_s81hd_mini ] || $V --binary --timing -O1 -Wno-fatal -Wno-lint -Wno-style --trace --trace-max-width 1024 --top-module tb_s81hd_mini \
  -GCUT=511 -GSPLIT9=1 -GFADD_L4=0 -GCV=0 -GAIS=0 -GMH=0 -GCS=0 -Mdir $OBJ $SRCS --build-jobs ${J:-8} \
  -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > $O/build.log 2>&1 || { grep -m10 %Error $O/build.log; echo BUILD_FAILED; exit 3; }
W=$O/scen_A; mkdir -p $W
ln -sf $IMG/xa.hex $W/xa.hex; ln -sf $IMG/xb.hex $W/xb.hex
for t in "t0 h" "t1 g"; do set -- $t; for e in a0 a1 a2 a3 b; do for k in 0 1; do ln -sf $IMG/$2${e}_$k.viamap.hex $W/$1${e}_$k.viamap.hex; done; done; done
$OBJ/Vtb_s81hd_mini +DIR=$W +OT_ROM_DIR=$W +ROW0_0=21888 +ROW0_1=22016 +NPOS=2 +EXP_ROW=21946 +EXP_BITS=4173a558 +EXP_FLT=0 +EXP_CYC=8430  > $O/run_A.log 2>&1
grep -E "^(POS|TB_PASS|TB_FAIL|%Error)" $O/run_A.log | head; ls -la $O/elem.vcd
