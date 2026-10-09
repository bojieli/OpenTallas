#!/bin/bash
# sys-takeover 2026-10-09: committed far-bus gate (rtl/test/emb_hbm/tb_emb_far_bus.sv: native-output equivalence vs the
# golden ot_qfd_link_far, default-off, 64 tx / rx per class, credits) with OT_QFD_FAR_AFW (registered-write receive FIFO);
# neg = the bench's NEG=1 mutated engine credit, which must fail.     far_bus_afw_bench.sh pos|neg OUT
set -u
m=$1; o=$2; mkdir -p "$o"
S=(rtl/lib/ot_reset_sync.sv rtl/lib/ot_async_fifo.sv rtl/physical/ot_qwen_async_fifo_w.sv rtl/physical/ot_qwen_die_cdc_ch.sv
 rtl/qwen_sys/emb_hbm_20261008/ot_qfd_link_far.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_link_far_bus.sv rtl/test/emb_hbm/tb_emb_far_bus.sv)
P=(); [[ $m == neg ]] && P=(-Ptb_emb_far_bus.NEG=1)
iverilog -g2012 -DOT_QFD_FAR_AFW "${P[@]}" -s tb_emb_far_bus -o "$o/sim" "${S[@]}" > "$o/build.log" 2>&1 || { cat "$o/build.log"; echo FAR_AFW_BENCH_ERROR; exit 2; }
vvp -n "$o/sim" > "$o/run.log" 2>&1; rc=$?; tail -2 "$o/run.log"
if [[ $m == pos ]]; then [[ $rc == 0 ]] && grep -q '^PASS far_bus' "$o/run.log" && { echo FAR_AFW_PASS; exit 0; }; echo FAR_AFW_FAIL; exit 1; fi
[[ $rc != 0 ]] || grep -q FAIL "$o/run.log" && { echo FAR_AFW_NEG_DETECTED; exit 1; }; echo FAR_AFW_NEG_MISSED; exit 0
