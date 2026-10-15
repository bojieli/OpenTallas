#!/usr/bin/env bash
set -euo pipefail
root=${HCOLL_ROOT:-$(git -C "$(dirname "$0")" rev-parse --show-toplevel)}
cd "$root"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
p=rtl/hbm_accel/generic/collective/p2p
t=rtl/hbm_accel/generic/collective/tkm
src=("$p/ot_hfd_coll_q_static_v2.sv" "$p/ot_hgi_coll_static_issuer.sv"
 "$p/ot_hgi_coll_qslots.sv" "$p/ot_hgi_coll_pring_static.sv" "$p/ot_hgi_coll_static_vmwrite.sv"
 "$p/ot_hgi_coll_static_link_seq.sv" "$p/ot_hgi_coll_static_seq_ctl.sv" "$p/ot_hgi_coll_reduce_static.sv" "$p/ot_hgi_coll_argmax_static.sv" "$root/rtl/hbm_accel/generic/collective/ot_hgi_coll_amerge.sv" "$t/ot_hgi_coll_tkm_static.sv" "$t/ot_hgi_coll_tkm.sv" "$t/ot_hgi_coll_tkm_buffer.sv"
 rtl/lib/ot_rst_relay.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv
 rtl/qwen_sys/split_20261014/ot_qwen_crc_parallel.sv rtl/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv
 rtl/qwen_sys/split_20261014/ot_qwen_static_slot_link.sv
 physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v)
for n in ${HCOLL_LINT_TOPS:-3 2};do
 "$V" --lint-only --hierarchical "$p/qtkm_hier.vlt" --timing -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-TIMESCALEMOD \
   --top-module "ot_hfd_coll_q${n}_static_v2" "${src[@]}"
done
