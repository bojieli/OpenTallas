#!/bin/bash
# redesign-qwen 2026-10-09: qfd_link_rx128 (ot_qwen_die_cdc_ch W 523 IBUF 128 OCRED 8 AD 8 AFW 1) with the RXP receive
# buffer (sys-takeover far92 7d3ba9bf2: one-hot write / read pointer copies per 32-b slice, registered 2-stage AND-OR read,
# 4-entry staging FIFO; +2 wclk a word, full rate).
#   rx128_rxp_bench.sh pos OUT : tb_cdc_ch_rxp at the rx128 shape, AFW=1 with RXP=0 and RXP=1 (order / values / faults,
#                                random sends, backpressured receiver) -> RX128_RXP_PASS
#   rx128_rxp_bench.sh neg OUT : staging-room mutant (OT_CDC_RXP_MUT_NOINFLIGHT) with AFW=1 must fail -> RX128_RXP_NEG_DETECTED (rc 1)
set -u
m=$1; o=$2; mkdir -p "$o"
C=(rtl/physical/ot_qwen_die_cdc_ch.sv rtl/lib/ot_async_fifo.sv rtl/physical/ot_qwen_async_fifo_w.sv rtl/lib/ot_reset_sync.sv)
run_cdc() {   # tag rxp extra-defines...
  local tag=$1 rxp=$2; shift 2
  iverilog -g2012 "$@" -Ptb_cdc_ch_rxp.RXP=$rxp -Ptb_cdc_ch_rxp.AFW=1 -Ptb_cdc_ch_rxp.NW=3000 -s tb_cdc_ch_rxp -o "$o/$tag.vvp" rtl/test/sys_takeover/tb_cdc_ch_rxp.sv "${C[@]}" > "$o/$tag.build.log" 2>&1 || { cat "$o/$tag.build.log"; echo RX128_RXP_BENCH_ERROR; exit 2; }
  vvp -n "$o/$tag.vvp" > "$o/$tag.log" 2>&1
  grep CDC_RXP "$o/$tag.log"
  grep -q '^CDC_RXP PASS' "$o/$tag.log"
}
if [[ $m == neg ]]; then
  if run_cdc mut 1 -DOT_CDC_RXP_MUT_NOINFLIGHT; then echo RX128_RXP_NEG_MISSED; exit 0; fi
  echo RX128_RXP_NEG_DETECTED; exit 1
fi
ok=1
run_cdc rxp0 0 || ok=0
run_cdc rxp1 1 || ok=0
[[ $ok == 1 ]] && { echo RX128_RXP_PASS; exit 0; }
echo RX128_RXP_FAIL; exit 1
