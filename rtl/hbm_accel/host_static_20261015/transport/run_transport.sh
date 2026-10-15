#!/usr/bin/env bash
set -euo pipefail
out=${1:?out};mkdir -p "$out"
for mut in 0 1 2 3; do
 iverilog -g2012 -s tb_host_cfg_transport -Ptb_host_cfg_transport.MUT="$mut" -o "$out/sim$mut" rtl/hbm_accel/host_static_20261015/transport/{ot_hbm_host_cfg_cdc,ot_hbm_host_cfg_demux,tb_host_cfg_transport}.sv > "$out/build$mut.log" 2>&1
 set +e;vvp "$out/sim$mut" > "$out/run$mut.log" 2>&1;rc=$?;set -e
 if [[ "$mut" == 0 ]];then [[ "$rc" == 0 ]] && grep -q '^HOST_CFG_TRANSPORT_PASS' "$out/run$mut.log";
 else
  [[ "$rc" != 0 ]] || { echo "mutant$mut survived";exit 1; }
  if [[ "$mut" == 1 ]];then grep -q 'HOST_CFG_TRANSPORT BRESP' "$out/run$mut.log";
  else grep -q 'HOST_CFG_TRANSPORT target/payload mismatch' "$out/run$mut.log";fi
 fi
 cat "$out/run$mut.log"
done
echo HOST_CFG_TRANSPORT_GATE_PASS
