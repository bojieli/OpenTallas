#!/bin/bash
# beatnorm_bench.sh <outdir> [base|muttree] [SG]  (cwd = repo root): S81-SLICE beat-leaf norm bench under Verilator 5:
# the 5 beat leaves (ot_s81sl_vn + ot_s81sl_vq) of slice SG on the DS1M golden row.  base must PASS; muttree (vn level-1
# pairing broken) must FAIL.  Exit 0 = the expected verdict.
set -u; O=$1; M=${2:-base}; SG=${3:-0}; mkdir -p $O/run
G0=results/rtl/hbm_norm_engine_view_20261006/gold
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
MACV=physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
python3 tools/s81_slice/norm_gold.py $O/run > $O/gold.log 2>&1 || { echo "BENCH_SETUP_FAILED gold"; cat $O/gold.log; exit 4; }
DEF=""; [ "$M" = muttree ] && DEF="+define+OT_S81SL_MUT_TREE"
srcs="$(sort -u physical/hbm_norm_split_20261008/sources.f | tr '\n' ' ') $MACV rtl/lib/ot_rst_relay.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vn.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vq.sv rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_beatnorm.sv"
/usr/bin/time -v -o $O/time.log $V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD $DEF -GSG=$SG --top-module tb_s81sl_beatnorm -Mdir $O/obj $srcs \
  --build-jobs ${J:-4} -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > $O/build.log 2>&1 || { echo "BUILD_FAILED"; tail -n 8 $O/build.log; exit 3; }
cp $G0/x.mem $G0/w.mem $G0/cfg.mem $G0/ey.mem $G0/eqc.mem $G0/eqe.mem $O/run/ && (cd $O/run && ../obj/Vtb_s81sl_beatnorm > ../run.log 2>&1)
grep -E "^SLBEATNORM|MISMATCH" $O/run.log | head -12
if [ "$M" = base ]; then grep -q '^PASS' $O/run.log && { echo "PASS beatnorm $M SG=$SG"; exit 0; }; echo "FAIL beatnorm"; exit 1; fi
grep -q '^FAIL' $O/run.log && { echo "NEGATIVE_CONTROL_FAILED_AS_EXPECTED $M"; exit 0; }; echo "NEGATIVE_CONTROL_PASSED $M (bench blind)"; exit 1
