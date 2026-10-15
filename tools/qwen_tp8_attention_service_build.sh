#!/bin/bash
set -eu
out=$1
vl=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
e_read_latency=${E_READ_LATENCY:-1}
[[ "$e_read_latency" =~ ^[1-9][0-9]*$ ]] || { echo 'E_READ_LATENCY must be positive' >&2; exit 2; }
v_return_latency=${V_RETURN_LATENCY:-$((16 + e_read_latency))}
src='rtl/hdc/nearhbm/ot_qwen_tp8_vrow_capture.sv rtl/hdc/nearhbm/ot_qwen_tp8_vrow_static.sv rtl/hdc/nearhbm/ot_qwen_tp8_k_request_static.sv rtl/hdc/nearhbm/ot_qwen_tp8_attention_service.sv rtl/hdc/nearhbm/ot_qwen_tp8_vrow_merge.sv rtl/hdc/nearhbm/ot_qwen_tp8_pv256_pair.sv rtl/hdc/nearhbm/ot_qwen_tp8_pv256_slice.sv rtl/hdc/nearhbm/ot_qwen_tp8_pv256_finalize.sv rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_h.sv rtl/hdc/nearhbm/ot_qkd_ectl_parts.sv rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_hub_p.sv rtl/hdc/nearhbm/ot_qwen_nearhbm_prod.sv rtl/hdc/ot_hdc_sfu_q.sv rtl/hdc/nearhbm/ot_qwen_nearhbm_sfu_p.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_fp32_add_lat_nr.sv rtl/test/nearhbm/sim_nhb_fp_lat_dpi.sv rtl/test/sim_hdc_v41x_fastfp_dpi.sv rtl/test/sim_hdc_v41x_fastfp_wrap.sv rtl/model/hbm_pc40_native_sim_20261003/ot_sram_1r1w_128x256_m1_r2c2_sim.sv'
mkdir -p "$out"
$vl --cc --exe --build -j 8 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN --top-module ot_qwen_tp8_attention_service \
 -GSTATIC_IO_TIMING="${STATIC_IO_TIMING:-0}" -GSTATIC_K_TRANSPORT="${STATIC_K_TRANSPORT:-0}" -GK_RETURN_LATENCY="${K_RETURN_LATENCY:-16}" \
 -GSTATIC_V_TRANSPORT="${STATIC_V_TRANSPORT:-0}" -GE_READ_LATENCY="$e_read_latency" -GV_RETURN_LATENCY="$v_return_latency" +define+KVD_HEADS=1 +define+KVD_Q_FP32=1 +define+KVD_QK_ONLY=1 +define+KVD_ECTL3 -CFLAGS "-O1" --Mdir "$out" -o Vtb $src rtl/test/nearhbm/tb_qwen_tp8_attention_service.cpp rtl/test/nearhbm/sim_nhb_fp_lat_dpi.cpp rtl/test/sim_hdc_v41x_fastfp_dpi.cpp > "$out/build.log" 2>&1
