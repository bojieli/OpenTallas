#!/bin/bash
# run_gu_bench.sh <src root R> <kits dir K> <out dir O> [measure]: build tb_gu_layer (REAL dsdv_seq_host + dsdv_gunit of
# the tree R: the file lists of tools/s81_dv/layer_prog/run_seqhost_prog.sh and rtl/dsrom_sys/s81_dv/unit/test/
# run_gunit_bench.sh) with Verilator 5.050 (the closure daemon's pin), run the positive kit K/kit0 and every mutant kit
# K/m_* (each must FAIL), write O/<kit>.log, O/verilator.version, O/sources.sha256.  Prints GU_BENCH PASS / FAIL.
set -u
R=$(realpath $1); K=$(realpath $2); O=$3; mkdir -p $O; O=$(realpath $O); MEAS=${4:-0}
H=$(cd "$(dirname "$0")" && pwd)
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
U=$R/rtl/dsrom_sys/s81_dv/unit
F="$R/rtl/lib/ot_async_fifo.sv $R/rtl/lib/ot_reset_sync.sv $R/rtl/lib/ot_rst_relay.sv $R/rtl/link/ot_link_afifo.sv
   $R/rtl/dsrom_sys/s81_ctrl/ot_s81_secded.sv $R/rtl/hdc/ingest/ot_hdc_ingest_fp8q.sv $R/rtl/hdc/ingest/ot_hdc_kv_ingest.sv
   $R/rtl/hdc/ingest/ot_rom_host_ingest.sv $R/physical/rom_host_ingest/rtl/dsfd_host.sv
   $R/rtl/dsrom_sys/s81_ingest/ot_s81_ingest_visibility_fence.sv $R/rtl/dsrom_sys/s81_ingest/dsfd_host_native.sv
   $R/rtl/dsrom_sys/s81_ingest/dsfd_host_sd.sv $R/rtl/dsrom_sys/s81_ingest/dsfd_host_c.sv
   $R/rtl/dsrom_sys/s81_static_control/ot_s81_fixed_issue.sv $U/ot_dsdv_fixed_issue.sv $U/ot_dsdv_walk_issue.sv $U/ot_dsdv_vstop.sv $U/dsdv_sh_sd.sv $U/dsdv_seq_host.sv
   $R/physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
   $R/rtl/hdc/ot_hdc_fastfp_lat_f12.sv $R/rtl/hdc/ot_hdc_delay.sv $R/rtl/hdc/ot_hdc_sfu.sv $R/rtl/hdc/v41x/ot_dsrom_su_norm.sv
   $R/rtl/hdc/ot_hdc_fastfp.sv $R/rtl/hdc/ot_hdc_fp32_f12.sv $R/rtl/hdc/ot_hdc_fp32_mul_lat.sv $R/rtl/hdc/ot_hdc_fp32_add_lat.sv
   $R/rtl/hdc/ot_hdc_prefix.sv $R/rtl/hdc/v41x/ot_dsrom_fp32_add_l6.sv $R/rtl/hdc/v41x/ot_dsrom_su_fdiv_f12.sv
   $R/rtl/hdc/v41x/ot_dsrom_su_f12.sv $R/rtl/hdc/v41x/ot_dsrom_su_add6.sv $R/rtl/hdc/v41x/ot_dsrom_divc.sv $R/rtl/dsrom_sys/s81_suhc/ot_s81_su_rw.sv
   $R/rtl/hdc/v41/ot_hdc_select_tree.sv $R/rtl/hdc/v41x/ot_dsrom_su_bias_select.sv $R/rtl/hdc/v41x/ot_hdc_v41x_sfu.sv
   $R/rtl/hdc/v41/ot_hdc_fdiv.sv $R/rtl/hdc/v41/ot_hdc_sinkhorn.sv $R/rtl/hdc/v41/ot_hdc_sk_arith.sv $R/rtl/hdc/v41/ot_hdc_sk_recip_rom.sv
   $R/rtl/hdc/ot_hdc_cg.sv $U/dsdv_gunit_pass.sv $U/dsdv_gunit_tail.sv $U/dsdv_gunit_l0.sv $U/dsdv_gunit_l1.sv $U/dsdv_gunit_l2.sv
   $U/dsdv_gunit_l3.sv $U/dsdv_gunit_l4.sv $U/dsdv_gunit_l5.sv $U/dsdv_gunit_l0r.sv $U/dsdv_gunit_l4r.sv $U/dsdv_gunit_l5f.sv
   $U/dsdv_gunit.sv"
$V --version > $O/verilator.version
sha256sum $F $H/tb_gu_layer.sv $H/gu_kit.py $H/../lower_gu.py > $O/sources.sha256
if [ ! -x $O/obj/tb ]; then
  $V --binary --timing -j ${J:-8} -O2 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-UNOPTFLAT -Wno-TIMESCALEMOD \
    +define+DSFD_HOST_C_STATIC --top-module tb_gu_layer --Mdir $O/obj -o tb $F $H/tb_gu_layer.sv -CFLAGS -O1 > $O/build.log 2>&1 \
    || { echo "GU_BENCH BUILD_FAIL"; grep -m8 %Error $O/build.log; exit 3; }
fi
bad=0
for k in $K/kit0 $K/m_*; do
  [ -d $k ] || continue
  n=$(basename $k)
  $O/obj/tb $(cat $k/tb.args | sed "s#+dir=[^ ]*#+dir=$k#") +measure=$MEAS > $O/$n.log 2>&1
  r=$(grep -m1 '^GU_LAYER' $O/$n.log); echo "$n: $r"
  if [ $n = kit0 ]; then echo "$r" | grep -q '^GU_LAYER PASS' || bad=1
  else echo "$r" | grep -q '^GU_LAYER FAIL' || bad=1; fi
done
[ $bad = 0 ] && echo "GU_BENCH PASS" || echo "GU_BENCH FAIL"
exit $bad
