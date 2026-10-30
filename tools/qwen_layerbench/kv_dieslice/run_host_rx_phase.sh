#!/bin/bash
set -euo pipefail
R=$(cd "$(dirname "$0")/../../.." && pwd)
D=$(realpath -m "${1:?OUT}"); mkdir -p "$D"
for case in 0:172:0 2:172:1 2:170:0; do
  IFS=: read -r p dt bad <<< "$case"
  name=p${p}_dt${dt}_b${bad}
  iverilog -g2012 -s tb_host_rx_phase -Ptb_host_rx_phase.PHASE=$p -Ptb_host_rx_phase.RXDT=$dt -Ptb_host_rx_phase.EXPECT_BAD=$bad -o $D/tb_$name.vvp $R/rtl/test/qwen_split/tb_host_rx_phase.sv $R/rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_sfm.sv $R/rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_static.sv $R/rtl/qwen_sys/context_transport_20261014/qkd_host_record_port.sv $R/rtl/qwen_sys/context_transport_20261014/qkd_context_records.sv $R/rtl/qwen_sys/split_20261014/ot_qwen_crc_parallel.sv $R/rtl/qwen_sys/split_20261014/ot_qwen_static_slot_link.sv $R/rtl/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv $R/physical/qwen_kv_die_phy/ot_qkvd_ucie_x64_phy/ot_qkvd_ucie_x64_phy_model.sv $R/physical/asap7_memory_macros_v2/d2d_sram_1r1w_64x137_m1_r2c2_p192/d2d_sram_1r1w_64x137_m1_r2c2_p192.v $R/physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v >$D/build_$name.log 2>&1
  vvp $D/tb_$name.vvp >$D/run_$name.log 2>&1
  cat $D/run_$name.log
done
