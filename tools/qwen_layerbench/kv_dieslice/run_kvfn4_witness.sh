#!/bin/bash
# KV-FN-4: run_kvfn4_witness.sh REPO_ROOT OUTDIR -- unit test of the far-end program witness (tb_kvfn4_witness.sv, modes 0-2)
# + lint of kvs_compute_end.sv with its dependencies.  Small (seconds, <1 GB).
set -euo pipefail
R=$(readlink -f $1); O=$2; H=$R/tools/qwen_layerbench/kv_dieslice; mkdir -p $O
V=${VERILATOR:-verilator}
CR=$R/rtl/qwen_sys/context_transport_20261014/qkd_context_records.sv
rc=0
for m in 0 1 2; do
  $V --binary -Wno-fatal -Wno-lint -Wno-style --timing -GMODE=$m --top-module tb_kvfn4_witness -Mdir $O/m$m $H/tb_kvfn4_witness.sv $CR > $O/m$m.build.log 2>&1
  $O/m$m/Vtb_kvfn4_witness | tee $O/m$m.log | grep UT_KVFN4
  grep -q 'UT_KVFN4 PASS' $O/m$m.log || rc=1
done
IMGD=${D2D_IMG:-$R/physical/die_plan/qwen_kvsys/boot_v36/image_kv41}
$V --lint-only -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-PINMISSING -Wno-MODDUP --timing --top-module kvs_compute_end +incdir+$IMGD \
  -y $R/rtl/qwen_sys/d2d_static_20261015 -y $R/rtl/qwen_sys/split_20261014 -y $R/rtl/qwen_split -y $R/rtl/physical -y $R/rtl/lib -y $R/physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2 \
  $H/kvs_compute_end.sv $R/physical/qwen_kv_die_phy/ot_qkvd_ucie_x64_phy/ot_qkvd_ucie_x64_phy_model.sv \
  $R/rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_static.sv $R/rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_dies.sv \
  $R/rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_cal_seq.sv $R/rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_services.sv \
  $R/rtl/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv $R/rtl/qwen_split/qfd_kvn_static_transport.sv $R/rtl/lib/ot_rst_pipe.sv $CR > $O/lint.log 2>&1 \
  && echo "LINT kvs_compute_end OK" || { echo "LINT kvs_compute_end FAIL"; grep '%Error' $O/lint.log | head; rc=1; }
echo "UT_KVFN4_ALL $([ $rc = 0 ] && echo PASS || echo FAIL)"; exit $rc
