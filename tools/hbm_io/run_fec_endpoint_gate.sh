#!/usr/bin/env bash
set -euo pipefail
root=${HCOLL_ROOT:-$(git -C "$(dirname "$0")" rev-parse --show-toplevel)}
out=$(realpath -m "$1");mut=${2:-0};mkdir -p "$out";cd "$root"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
p=rtl/hbm_accel/generic/collective/p2p
io=rtl/hbm_accel/io_static_20261015
"$V" --binary --timing -O2 -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-UNOPTFLAT -Irtl/dsrom_sys/s81_link --top-module tb_static_fec_endpoint_transport -GDMUT="$mut" --Mdir "$out/obj" -o sim \
 "$io/tb_static_fec_endpoint_transport.sv" "$io/hfd_serdes487_static_window.sv" "$io/ot_hbm_static_word_cdc.sv" "$io/ot_hbm_static_frame_transport.sv" "$io/ot_hbm_static_gearbox.sv" \
 "$p/ot_hgi_coll_static_link_capture.sv" "$p/ot_hgi_coll_static_capture_ctl.sv" "$p/ot_hgi_coll_static_pinreg_ctl.sv" "$p/ot_hgi_coll_static_pinreg_store.sv" "$p/ot_hgi_coll_static_seq_ctl.sv" \
 rtl/qwen_sys/split_20261014/ot_qwen_crc_parallel.sv rtl/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v \
 rtl/hbm_accel/io_native_20261014/ot_hbm_kp4_enc_rooted.sv rtl/hbm_accel/io_native_20261014/ot_hbm_kp4_dec_rooted.sv rtl/hbm_accel/io_native_20261014/ot_hbm_kp4_encode52_map.sv rtl/hbm_accel/io_native_20261014/ot_hbm_kp4_syndrome55_map.sv rtl/dsrom_sys/s81_link/ot_pdie_serdes.sv > "$out/build.log" 2>&1 || { tail -30 "$out/build.log";exit 2; }
code=0
"$out/obj/sim" > "$out/run.log" 2>&1 || code=$?
cat "$out/run.log"
if [[ "$mut" == 0 ]];then
 [[ "$code" == 0 ]];grep -q 'FEC_ENDPOINT PASS slots300 checks234 words2048 decoded2048 age102' "$out/run.log"
 pids=()
 for s in 1 2 3 4;do
  ( "$out/obj/sim" +mut="$s" > "$out/m$s.log" 2>&1 && grep -q 'FEC_ENDPOINT MUTANT PASS' "$out/m$s.log" ) &
  pids+=("$!")
 done
 status=0
 for pid in "${pids[@]}";do wait "$pid" || status=1;done
 for s in 1 2 3 4;do cat "$out/m$s.log";done
 [[ "$status" == 0 ]]
else
 [[ "$code" != 0 ]];grep -q 'FEC_DECODE_ERROR' "$out/run.log"
 echo 'FEC_ENDPOINT FORNEY_MUTANT_REJECTED'
fi
