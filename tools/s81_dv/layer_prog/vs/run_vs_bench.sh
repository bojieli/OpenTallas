#!/bin/bash
# run_vs_bench.sh <kit root R> <out O> <vec dir>... : build tb_vs_lowered once on the REAL slice vp / vs / vsw / vq + the
# hub RA lane pair (file list = tools/s81_slice/vs_bench.sh + ot_s81sl_aq12x), Verilator 5.050 (the closure daemon's pin),
# then run every vector dir (gen_vs_bench.py output: *.mem + params.txt).  Prints one line per vector:
#   VSB <vec> PASS|FAIL  (the tb's SLVSL summary follows).  Exit 0 always; the verdict is in the logs.
set -u
R=$(realpath $1); O=$2; shift 2; mkdir -p $O; O=$(realpath $O)
H=$R/tools/s81_dv/layer_prog/vs
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
S="rtl/lib/ot_rst_relay.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv
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
 rtl/dsrom_sys/s81_dv/slice/ot_s81sl_aq12x.sv
 rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vp.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vq.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vs.sv
 rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vsw.sv tools/s81_dv/layer_prog/vs/tb_vs_lowered.sv"
F=""; for f in $S; do F="$F $R/$f"; done
$V --version > $O/verilator.version
(cd $R && sha256sum $S tools/s81_dv/layer_prog/lower_vs.py tools/s81_dv/layer_prog/vs/gen_vs_bench.py \
   tools/s81_dv/layer_prog/vs/run_vs_bench.sh) > $O/sources.sha256
if [ ! -x $O/obj/Vtb_vs_lowered ]; then
  /usr/bin/time -v -o $O/build.time $V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --top-module tb_vs_lowered \
    -Mdir $O/obj $F --build-jobs ${J:-4} -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > $O/build.log 2>&1 \
    || { echo "VSB BUILD_FAILED"; grep -m8 %Error $O/build.log; exit 3; }
fi
for d in "$@"; do
  d=$(realpath $d); n=$(basename $d)
  (cd $d && $O/obj/Vtb_vs_lowered $(cat params.txt) > $O/$n.run.log 2>&1)
  v=$(grep -m1 -E '^(PASS|FAIL)$' $O/$n.run.log || echo NOVERDICT)
  echo "VSB $n $v"; grep -E '^SLVSL' $O/$n.run.log
done
