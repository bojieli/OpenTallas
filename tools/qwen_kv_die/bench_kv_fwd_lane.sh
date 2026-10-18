#!/bin/bash
# KV-CLOCK/LANEKITS 10-18: behavioural bench of the KV forwarded-clock half-cycle lane masters qkd_rlysh0_/qkd_rlysh_/
# qkd_landsh_/qkd_landsh0_<S> (rtl/qwen_sys/kv_fwd_lane_20261018/qkd_rlysh.sv over rtl/qwen_split/qfd_fwd_lane.sv).
# The testbench is the Qwen one (tools/qwen_split/bench_fwd_lane.sh tb, extracted verbatim: 8 lanes n = 1, 2, 5, 5+2T lag,
# 8, 27 frames, source released before / after the receiver, clock leg longer than data leg), instantiating the qfd_*
# frames; thin shims qfd_*_<S>_EW_65x30 -> qkd_*_<S> put the KV wrappers + shared cores under test.  Verilator 5.050.
# usage: bench_kv_fwd_lane.sh <pass|sel|naive|vld|full|hop0inv> <work dir> <S>    (S = 1 | 36 | 296 | 528)
set -u
mode=$1; O=$2; W=${3:?S}
cd "$(dirname "$0")/../.."; mkdir -p "$O"
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
DEF=
case $mode in
  pass) ;; sel) DEF=+define+OT_QFD_LAND_MUT_SEL ;; naive) DEF=+define+OT_QFD_LAND_MUT_NAIVE ;;
  vld) DEF=+define+OT_QFD_LAND_MUT_VLD ;; full) DEF=+define+OT_QFD_LANE_MUT_FULL ;; hop0inv) DEF=+define+OT_QFD_LANE_MUT_HOP0INV ;;
  *) echo "bad mode $mode"; exit 2 ;;
esac
awk '/^cat > "\$O\/tb.sv" <<.EOT.$/{f=1; next} f && /^EOT$/{exit} f' tools/qwen_split/bench_fwd_lane.sh > "$O/tb.sv"
[ -s "$O/tb.sv" ] || { echo TB_EXTRACT_FAILED; exit 2; }
sed -i "s/_16_EW_65x30/_${W}_EW_65x30/g; s/parameter integer W = 16/parameter integer W = ${W}/" "$O/tb.sv"
V=$((W-1))
cat > "$O/shims.sv" <<EOT
module qfd_rlyh0_${W}_EW_65x30 (input wire ck, input wire en, input wire [$V:0] a, output wire [$V:0] b, output wire eb, output wire ck_o);
  qkd_rlysh0_${W} u (.ck(ck), .en(en), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module qfd_rlyh_${W}_EW_65x30 (input wire ckf, input wire ea, input wire [$V:0] a, output wire [$V:0] b, output wire eb, output wire ck_o);
  qkd_rlysh_${W} u (.ckf(ckf), .ea(ea), .a(a), .b(b), .eb(eb), .ck_o(ck_o));
endmodule
module qfd_landh_${W}_EW_65x30 (input wire ckf, input wire ea, input wire [$V:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire tie_hi, output wire tie_lo, output wire [$V:0] b, output wire fault);
  qkd_landsh_${W} u (.ckf(ckf), .ea(ea), .a(a), .ck(ck), .rs(rs), .k0(k0), .k1(k1), .k2(k2), .tie_hi(tie_hi), .tie_lo(tie_lo), .b(b), .fault(fault));
endmodule
module qfd_landh0_${W}_EW_65x30 (input wire ck_s, input wire en, input wire [$V:0] a, input wire ck, input wire rs, input wire k0, input wire k1, input wire k2, output wire tie_hi, output wire tie_lo, output wire [$V:0] b, output wire fault);
  qkd_landsh0_${W} u (.ck_s(ck_s), .en(en), .a(a), .ck(ck), .rs(rs), .k0(k0), .k1(k1), .k2(k2), .tie_hi(tie_hi), .tie_lo(tie_lo), .b(b), .fault(fault));
endmodule
EOT
verilator --binary --timing -Wno-fatal -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-COMBDLY -Wno-LATCH -Wno-INITIALDLY --top-module tb $DEF \
  -Mdir "$O/obj" -o tb "$O/tb.sv" "$O/shims.sv" rtl/qwen_sys/kv_fwd_lane_20261018/qkd_rlysh.sv rtl/qwen_split/qfd_fwd_lane.sv \
  rtl/hdc/ot_hdc_cg.sv > "$O/build.log" 2>&1 || { echo BUILD_FAILED; tail -20 "$O/build.log"; exit 2; }
"$O/obj/tb" | tee "$O/bench.log" | grep -E 'FWD_BENCH|FWD_LANE (NF|FAULT)'
grep -q 'FWD_BENCH PASS' "$O/bench.log"
