#!/usr/bin/env bash
# Bounded original HD-CTL mechanism with actual old/new controller output-capture comparison.
set -euo pipefail
O=${1:?out};mkdir -p "$O";O=$(cd "$O" && pwd)
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
T=rtl/dsrom_sys/s81_head
SRCS=(rtl/lib/ot_rst_relay_tree3.sv "$T/ot_s81hd_util.sv" "$T/ot_s81hd_ctl.sv" "$T/ot_s81hd_ctl_peer_r2o.sv"
 rtl/dsrom_sys/mtp/dsfd_mtp_tops.sv rtl/dsrom_sys/mtp/ot_dsrom_mtp_seq.sv rtl/dsrom_sys/mtp/ot_dsrom_mtp_link_pair.sv
 physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v)
"$V" --version > "$O/verilator_version.txt"
sha256sum "${SRCS[@]}" "$T/test/tb_s81hd_ctl_output_local.sv" "$0" > "$O/source.sha256"
for mode in base bypass; do
 args=();test "$mode" = base || args=(-DOT_S81HD_OUTPUT_BYPASS_MUT)
 "$V" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-lint -Wno-style \
  "${args[@]}" --top-module tb_s81hd_ctl_output_local --output-split 20000 --output-split-cfuncs 200 \
  -Mdir "$O/$mode" "${SRCS[@]}" "$T/test/tb_s81hd_ctl_output_local.sv" --build-jobs "${J:-8}" > "$O/build_$mode.log" 2>&1
 set +e
 "$O/$mode/Vtb_s81hd_ctl_output_local" > "$O/$mode.log" 2>&1
 rc=$?
 set -e
 echo "$rc" > "$O/$mode.exit"
 if test "$mode" = base; then
  test "$rc" -eq 0;grep '^CTL_OUTPUT_CAPTURE_PASS' "$O/$mode.log";grep '^PASS hd_ctl' "$O/$mode.log"
 else
  test "$rc" -ne 0;grep '^FAIL hd_ctl output_same_edge mismatch' "$O/$mode.log"
  echo 'CTL_OUTPUT_BYPASS_NEGATIVE_CAUGHT'
 fi
done
echo 'CTL_OUTPUT_EXISTING_MECHANISM_PASS'
