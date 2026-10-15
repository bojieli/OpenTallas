#!/usr/bin/env bash
set -euo pipefail
root=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
out=$(realpath -m "$1");mkdir -p "$out"
build=$(mktemp -d /tmp/hcoll-native-transport.XXXXXX)
trap 'rm -rf "$build"' EXIT
cd "$root"
for p in rtl/qwen_sys/split_20261014/ot_qwen_crc_parallel.sv rtl/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v;do
 git show "4c66b6a95:$p" > "$build/$(basename "$p")"
done
p=rtl/hbm_accel/generic/collective/p2p
io=rtl/hbm_accel/io_static_20261015
for m in ${MUTANTS:-0 1 2 3 4};do
 iverilog -g2012 -s tb_static_capture_endpoint_transport -Ptb_static_capture_endpoint_transport.MUT="$m" -o "$build/sim$m" \
 "$build"/*.sv "$build"/*.v "$p/ot_hgi_coll_static_link_capture.sv" "$p/ot_hgi_coll_static_capture_ctl.sv" "$p/ot_hgi_coll_static_pinreg_ctl.sv" "$p/ot_hgi_coll_static_pinreg_store.sv" "$p/ot_hgi_coll_static_seq_ctl.sv" \
 "$io/ot_hbm_static_gearbox.sv" "$io/ot_hbm_static_frame_transport.sv" "$io/tb_static_capture_endpoint_transport.sv"
 vvp "$build/sim$m" > "$out/m$m.log" 2>&1
 cat "$out/m$m.log"
done
