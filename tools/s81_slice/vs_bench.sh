#!/bin/bash
# vs_bench.sh <outdir> [MUT 0..6] [L0|L2] [BEAT]  (cwd = repo root): S81-SLICE vs bench (vp + vs + vsw + hub RA lane pair + vq)
# on one layer's 1M-token SU cases (tools/s81_slice/vs_gold.py).  MUT 0 must PASS; MUT 1..6 (SW w, RB bias, QR inverse,
# MOE early BF16 partials, QB halves, RA row shift) must FAIL.  Exit 0 = the expected verdict.
set -u; O=$1; M=${2:-0}; L=${3:-L0}; B=${4:-37}; mkdir -p $O/run
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
CASES=${S81_SU_CASES:-tools/s81_suhc/fixtures/su_cases_v2_ildr.pkl}
python3 tools/s81_slice/vs_gold.py $CASES $O/run $L > $O/gold.log 2>&1 || { echo "BENCH_SETUP_FAILED gold"; tail -5 $O/gold.log; exit 4; }
srcs="rtl/lib/ot_rst_relay.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv
 rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_fastfp_lat_f12.sv rtl/hdc/v41/ot_hdc_fsqrt.sv rtl/hdc/v41/ot_hdc_fdiv.sv
 rtl/hdc/v41/ot_hdc_softplus.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv rtl/hdc/v41/ot_hdc_actquant.sv rtl/hdc/v41x/ot_dsrom_aq12.sv
 rtl/hdc/v41x/ot_dsrom_divc.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/v41x/ot_dsrom_fp32_add_l6.sv rtl/hdc/v41x/ot_dsrom_su_norm.sv
 rtl/hdc/v41x/ot_dsrom_su_fdiv_f12.sv rtl/hdc/v41x/ot_dsrom_su_f12.sv rtl/hdc/v41x/ot_hdc_v41x_spshort.sv
 rtl/hdc/v41x/ot_dsrom_su_swiglu.sv rtl/hdc/v41x/ot_dsrom_su_add6.sv rtl/hdc/v41x/ot_dsrom_su_hcpost.sv rtl/hdc/v41x/ot_dsrom_su_hcpost_lane_pr.sv
 rtl/dsrom_sys/s81_suhc/ot_s81_su_rw.sv rtl/dsrom_sys/s81_suhc/ot_s81_su_rx.sv rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_rxh.sv
 rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_sw.sv
 physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
 physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v
 rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vp.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vq.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vs.sv
 rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vsw.sv rtl/dsrom_sys/s81_dv/slice/test/tb_s81sl_vs.sv"
/usr/bin/time -v -o $O/time.log $V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -GMUT=$M -GBEAT=$B --top-module tb_s81sl_vs -Mdir $O/obj $srcs \
  --build-jobs ${J:-4} -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > $O/build.log 2>&1 || { echo "BUILD_FAILED"; tail -n 8 $O/build.log; exit 3; }
(cd $O/run && ../obj/Vtb_s81sl_vs > ../run.log 2>&1)
grep -E "^VSOP|^SLVS|MISMATCH|TIMEOUT" $O/run.log | head -40
if [ "$M" = 0 ]; then grep -q '^PASS' $O/run.log && { echo "PASS vs MUT=0 $L"; exit 0; }; echo "FAIL vs"; exit 1; fi
grep -q '^FAIL' $O/run.log && { echo "NEGATIVE_CONTROL_FAILED_AS_EXPECTED MUT=$M $L"; exit 0; }; echo "NEGATIVE_CONTROL_PASSED MUT=$M $L (bench blind)"; exit 1
