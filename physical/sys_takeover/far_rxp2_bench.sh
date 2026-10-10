#!/bin/bash
# sys-takeover 2026-10-10: far92 RXP 2 gate.
#   far_rxp2_bench.sh pos OUT    : (1) tb_cdc_ch_rxp at the far92 shape with RXP=0, 1 and 2 (backpressured receiver, order /
#                                  values / faults), (2) the committed far-bus gate tb_emb_far_bus.sv with OT_QFD_FAR_RXP2
#                                  (+ AFW): bus emb_o / kv_o compared against the golden core delayed by the one pin register
#                                  (RXP 2), plus its class / order / data / credit-count checks -> FAR_RXP2_PASS
#   far_rxp2_bench.sh neg OUT    : mutant OT_CDC_RXP_MUT_NESTALE (the registered non-empty flag misses the edge's own write /
#                                  issue) must fail tb_cdc_ch_rxp at RXP 2 -> FAR_RXP2_NEG_DETECTED (rc 1)
#   far_rxp2_bench.sh negbus OUT : the far-bus NEG (mutated engine credit) must fail with RXP 2 -> FAR_RXP2_NEG_DETECTED
set -u
m=$1; o=$2; mkdir -p "$o"
C=(rtl/physical/ot_qwen_die_cdc_ch.sv rtl/lib/ot_async_fifo.sv rtl/physical/ot_qwen_async_fifo_w.sv rtl/lib/ot_reset_sync.sv)
run_cdc() {
  local tag=$1 rxp=$2; shift 2
  iverilog -g2012 "$@" -Ptb_cdc_ch_rxp.RXP=$rxp -s tb_cdc_ch_rxp -o "$o/$tag.vvp" rtl/test/sys_takeover/tb_cdc_ch_rxp.sv "${C[@]}" > "$o/$tag.build.log" 2>&1 || { cat "$o/$tag.build.log"; echo FAR_RXP2_BENCH_ERROR; exit 2; }
  vvp -n "$o/$tag.vvp" > "$o/$tag.log" 2>&1
  grep CDC_RXP "$o/$tag.log" | tail -1
  grep -q '^CDC_RXP PASS' "$o/$tag.log"
}
python3 physical/sys_takeover/far_rxp2_tb.py "$o" || { echo FAR_RXP2_BENCH_ERROR; exit 2; }
S=("${C[@]}" rtl/qwen_sys/emb_hbm_20261008/ot_qfd_link_far.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_link_far_bus.sv "$o/tb_emb_far_bus_rxp2.sv")
if [[ $m == neg ]]; then
  if run_cdc mut 2 -DOT_CDC_RXP_MUT_NESTALE; then echo FAR_RXP2_NEG_MISSED; exit 0; fi
  echo FAR_RXP2_NEG_DETECTED; exit 1
fi
if [[ $m == negbus ]]; then
  iverilog -g2012 -DOT_QFD_FAR_AFW -DOT_QFD_FAR_RXP2 -Ptb_emb_far_bus.NEG=1 -s tb_emb_far_bus -o "$o/busneg.vvp" "${S[@]}" > "$o/busneg.build.log" 2>&1 || { cat "$o/busneg.build.log"; echo FAR_RXP2_BENCH_ERROR; exit 2; }
  vvp -n "$o/busneg.vvp" > "$o/busneg.log" 2>&1; rc=$?; tail -1 "$o/busneg.log"
  if [[ $rc == 0 ]] && ! grep -q FAIL "$o/busneg.log"; then echo FAR_RXP2_NEG_MISSED; exit 0; fi
  echo FAR_RXP2_NEG_DETECTED; exit 1
fi
ok=1
run_cdc rxp0 0 || ok=0
run_cdc rxp1 1 || ok=0
run_cdc rxp2 2 || ok=0
iverilog -g2012 -DOT_QFD_FAR_AFW -DOT_QFD_FAR_RXP2 -s tb_emb_far_bus -o "$o/bus.vvp" "${S[@]}" > "$o/bus.build.log" 2>&1 || { cat "$o/bus.build.log"; echo FAR_RXP2_BENCH_ERROR; exit 2; }
vvp -n "$o/bus.vvp" > "$o/bus.log" 2>&1; rc=$?; tail -1 "$o/bus.log"
[[ $rc == 0 ]] && grep -q '^PASS far_bus' "$o/bus.log" || ok=0
[[ $ok == 1 ]] && { echo FAR_RXP2_PASS; exit 0; }
echo FAR_RXP2_FAIL; exit 1
