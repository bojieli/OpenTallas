#!/usr/bin/env bash
set -euo pipefail
root=${HCOLL_ROOT:-$(cd "$(dirname "$0")/../../../../.." && pwd)}
out=$(realpath -m "$1");vec=$(realpath -m "$2");mkdir -p "$out";cd "$root"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
p=rtl/hbm_accel/generic/collective/p2p;t=rtl/hbm_accel/generic/collective/tkm
src=("$p/tb_hfd_coll_static_allgather.sv" "$p/ot_hfd_coll_q_static.sv" "$p/ot_hgi_coll_static_issuer.sv"
 "$p/ot_hgi_coll_qslots.sv" "$p/ot_hgi_coll_pring_static.sv" "$p/ot_hgi_coll_static_vmwrite.sv" "$p/ot_hgi_coll_static_link.sv"
 "$t/ot_hgi_coll_tkm_static.sv" "$t/ot_hgi_coll_tkm.sv" "$t/ot_hgi_coll_tkm_buffer.sv"
 rtl/lib/ot_rst_relay.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv
 rtl/qwen_sys/split_20261014/ot_qwen_crc_parallel.sv rtl/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv rtl/qwen_sys/split_20261014/ot_qwen_static_slot_link.sv
 physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v)
"$V" --binary --timing --hierarchical -O1 -j "${JOBS:-4}" -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN \
 --top-module tb_hfd_coll_static_allgather --Mdir "$out/obj" "$p/qtkm_hier.vlt" "${src[@]}" > "$out/build.log" 2>&1 || { tail -35 "$out/build.log";exit 2; }
for mut in 0 1 2 3;do
 "$out/obj/Vtb_hfd_coll_static_allgather" +DIR="$vec" +MUT="$mut" > "$out/m$mut.log" 2>&1
 cat "$out/m$mut.log"
 if [[ "$mut" == 0 ]];then grep -q '^ALLGATHER_NATIVE PASS ' "$out/m$mut.log";else grep -q '^ALLGATHER_MUTANT PASS ' "$out/m$mut.log";fi
 if grep -Eq '%Fatal|%Error' "$out/m$mut.log";then exit 1;fi
done
