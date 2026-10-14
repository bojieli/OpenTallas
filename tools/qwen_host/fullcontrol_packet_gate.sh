#!/usr/bin/env bash
set -euo pipefail
R=$(cd "$(dirname "$0")/../.." && pwd)
OUT=${1:?output directory}; TRANSPORT=${2:-$R}
mkdir -p "$OUT"
S=("$R/rtl/test/qwen_host/tb_qkd_host_fullcontrol_packet.sv" "$R/rtl/qwen_sys/host_20261013/qkd_host_fullcontrol.sv" "$R/rtl/qwen_sys/host_20261013/qkd_host_sys_csr.sv" "$R/rtl/qwen_sys/system_20261008/ot_host_if_pb2.sv" "$R/rtl/physical/ot_qwen_host_ctl.sv" "$R/rtl/qwen_sys/system_20261008/ot_qfd_pkgctl.sv" "$R/rtl/qwen_sys/ot_qwen_sys_rst_seq.sv" "$R/rtl/lib/ot_reset_sync.sv")
for TOP in qkd_host_packet_bundle qkd_host_rx_class qkd_host_tx_class qkd_host_axi_packet qkd_host_ctrl_packet; do S+=("$TRANSPORT/rtl/qwen_sys/host_20261013/$TOP.sv"); done
S+=("$R/rtl/qwen_sys/host_20261013/qkd_host_ctl_pins.sv" "$R/rtl/qwen_sys/host_20261013/qkd_host_if_pins.sv" "$R/rtl/qwen_sys/host_20261013/qkd_host_csr_pins.sv" "$R/rtl/qwen_sys/host_20261013/qkd_host_rst_pins.sv" "$R/rtl/qwen_sys/host_20261013/qkd_host_pin_channel.sv")
for MUT in 0 1 2 3; do
  iverilog -g2012 -s tb_qkd_host_fullcontrol_packet -Ptb_qkd_host_fullcontrol_packet.MUT="$MUT" -o "$OUT/tb-$MUT" "${S[@]}" > "$OUT/build-$MUT.log" 2>&1
  set +e
  vvp "$OUT/tb-$MUT" > "$OUT/run-$MUT.log" 2>&1
  RC=$?
  set -e
  if [[ $MUT == 0 ]];then
   if [[ $RC != 0 ]] || ! grep -q '^PASS full actual HOST' "$OUT/run-$MUT.log";then cat "$OUT/run-$MUT.log";exit 1;fi
  else
   if [[ $RC == 0 ]] || ! grep -q 'FATAL' "$OUT/run-$MUT.log";then cat "$OUT/run-$MUT.log";exit 1;fi
  fi
  cat "$OUT/run-$MUT.log"
  rm "$OUT/tb-$MUT"
done
