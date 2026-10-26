#!/bin/bash
# LANDFIX-SQ 10-18: behavioural bench of the Qwen FORWARDED RESET LANE (rtl/qwen_split/qfd_fwd_lane.sv ot_qfd_rlane_st /
# ot_qfd_rlane_land) through the GENERATED die wrappers (tools/qwen_split/gen_relay_rtl.py: qfd_rlyr0_ / qfd_rlyr_ /
# qfd_rlyrl_) -- Verilator 5.050.
# usage: bench_fwd_rst_lane.sh <pass|full|land2> <work dir> [<rlyr0 master> <rlyr master> <rlyrl master>]
#   (Q-H16C 10-18: the three masters default to the *_1_EW_65x30 frames; a class kit names its own master for its family
#    so the bench elaborates the kit's top -- the generated wrapper body is the same for every frame / direction)
#   pass : 6 lanes (n = 1, 2, 3, 5, 8, 27 frames) carry a pseudo-random reset LEVEL from the source root through hop 0
#          (source root), half-cycle stations (clock leg CD, data leg DD per hop) to the reset-release landing on the
#          receiver root (2 ns after the source root).  Per lane the bench derives the FIXED latency L (receiver edges)
#          from the geometry: arrival t = DD + (n >= 2 ? T + (n - 2)(T/2 + CD) : 0) after the launch edge,
#          L = floor((t - DOFF) / T) + 1, and checks on every receiver edge o = level(ed - 1 - L).
#          PASS line: RST_BENCH PASS 0 errors in <checks> checks.
#   full : the same bench on the RTL with OT_QFD_LANE_MUT_FULL (non-inverting forwards = full-cycle hops) -- must FAIL.
#   land2: the generated rlyrl landing wrapper re-registers the level TWICE on the receiving root (one extra edge vs
#          the priced landing) -- must FAIL (Q-H16C 10-18: the landing-kit mutant).
set -u
mode=$1; O=$2
cd "$(dirname "$0")/../.."; mkdir -p "$O"
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
DEF=
case $mode in pass|land2) ;; full) DEF=+define+OT_QFD_LANE_MUT_FULL ;; *) echo "bad mode $mode"; exit 2 ;; esac
R0=${3:-qfd_rlyr0_1_EW_65x30}; RS=${4:-qfd_rlyr_1_EW_65x30}; RL=${5:-qfd_rlyrl_1_EW_65x30}
for m in $R0 $RS $RL; do [[ $m =~ ^qfd_rlyr[0l]?_1_[NSEW]{2}_[0-9]+x[0-9]+$ ]] || { echo "bad master $m"; exit 2; }; done
[[ $R0 == qfd_rlyr0_* && $RS == qfd_rlyr_* && $RL == qfd_rlyrl_* ]] || { echo "masters out of order: $R0 $RS $RL"; exit 2; }
echo "RST_BENCH masters $R0 $RS $RL mode $mode"
cat > "$O/mini_die.v" <<EOT
module qfd_die ();
$(for n in n_a n_b n_c n_d n_ck n_ckf1 n_ckf2 n_ck2; do echo "  wire [0:0] $n;"; done)
  $R0 rly_x_0 (.ck(n_ck), .a(n_a), .b(n_b), .ck_o(n_ckf1));
  $RS rly_x_1 (.ckf(n_ckf1), .a(n_b), .b(n_c), .ck_o(n_ckf2));
  $RL rly_x_2 (.ck(n_ck2), .a(n_c), .b(n_d));
endmodule
EOT
python3 tools/qwen_split/gen_relay_rtl.py "$O/mini_die.v" "$O/wrappers.sv" > "$O/wrappers.json" || { echo GEN_FAILED; exit 2; }
if [ $mode = land2 ]; then
  python3 - "$O/wrappers.sv" $RL <<'EOP' || { echo MUTATE_FAILED; exit 2; }
import re, sys
p, rl = sys.argv[1], sys.argv[2]; s = open(p).read()
old = '    ot_qfd_rlane_land #(.W(1)) u_land (.ck(ck), .a(a), .b(b));'
i = s.index(f'module {rl} ('); j = s.index('endmodule', i)
assert s[i:j].count(old) == 1, 'landing body not found'
new = ('    wire m2;\n    ot_qfd_rlane_land #(.W(1)) u_land0 (.ck(ck), .a(a), .b(m2));\n'
       '    ot_qfd_rlane_land #(.W(1)) u_land (.ck(ck), .a(m2), .b(b));')
open(p, 'w').write(s[:i] + s[i:j].replace(old, new) + s[j:])
print('RST_BENCH MUTANT land2: double landing register in', rl)
EOP
fi
cat > "$O/tb.sv" <<'EOT'
`timescale 1ns/1ps
module tdly #(parameter real D = 1.0) (input wire a, output wire y);
    assign #(D) y = a;
endmodule
module rlane #(parameter integer NF = 5, parameter real CD = 1.0, DD = 1.0, DOFF = 2.0) (
    input wire cks, input wire ckd, input wire [31:0] es, input wire [31:0] ed, output integer err, output integer chk);
    localparam real T = 10.0;
    reg src = 1'b0;
    function automatic lv(input integer e); lv = ((e * 40503 + (e >>> 2) + 3) % 7) < 3; endfunction
    always @(posedge cks) src <= lv(es);                                    // the source launches level(e) at edge e
    wire d [0:NF]; wire c [0:NF]; wire o;
    assign d[0] = src;
    genvar j;
    generate
      if (NF == 1) begin : g1
        wire di; tdly #(DD) u_d (d[0], di);
        qfd_rlyrl_1_EW_65x30 u_l (.ck(ckd), .a(di), .b(o));
      end else begin : gn
        wire b0, cko0;
        qfd_rlyr0_1_EW_65x30 u_s0 (.ck(cks), .a(d[0]), .b(b0), .ck_o(cko0));
        tdly #(DD) u_d1 (b0, d[1]);  tdly #(CD) u_c1 (cko0, c[1]);
        for (j = 1; j < NF - 1; j = j + 1) begin : g_st
          wire bj, ckoj;
          qfd_rlyr_1_EW_65x30 u_s (.ckf(c[j]), .a(d[j]), .b(bj), .ck_o(ckoj));
          tdly #(DD) u_d (bj, d[j + 1]);  tdly #(CD) u_c (ckoj, c[j + 1]);
        end
        qfd_rlyrl_1_EW_65x30 u_l (.ck(ckd), .a(d[NF - 1]), .b(o));
      end
    endgenerate
    real t; integer L;
    initial begin
        err = 0; chk = 0;
        t = DD + ((NF >= 2) ? T + (NF - 2) * (T / 2.0 + CD) : 0.0);
        L = $rtoi($floor((t - DOFF) / T)) + 1;
        $display("RST_LANE NF=%0d CD=%0.2f DD=%0.2f arrival=%0.2f L=%0d", NF, CD, DD, t, L);
    end
    integer te_;
    always @(negedge ckd) begin
        te_ = ed; te_ = te_ - 1 - L;
        if (ed > 40) begin
            chk = chk + 1;
            if (o !== lv(te_)) begin
                err = err + 1;
                if (err < 4) $display("RST_LANE MISMATCH NF=%0d ed=%0d o=%b exp=%b", NF, ed, o, lv(te_));
            end
        end
    end
endmodule
module tb;
    reg cks = 0, ckd = 0;
    reg [31:0] es = 0, ed = 0;
    always #5 cks = ~cks;
    initial begin #2.0; forever #5 ckd = ~ckd; end
    always @(posedge cks) es <= es + 1;
    always @(posedge ckd) ed <= ed + 1;
    integer e [0:5], c [0:5];
    rlane #(.NF(1))                       l0 (cks, ckd, es, ed, e[0], c[0]);
    rlane #(.NF(2))                       l1 (cks, ckd, es, ed, e[1], c[1]);
    rlane #(.NF(3))                       l2 (cks, ckd, es, ed, e[2], c[2]);
    rlane #(.NF(5), .CD(2.0), .DD(1.5))   l3 (cks, ckd, es, ed, e[3], c[3]);
    rlane #(.NF(8), .CD(1.0), .DD(0.5))   l4 (cks, ckd, es, ed, e[4], c[4]);
    rlane #(.NF(27), .CD(0.6), .DD(0.4))  l5 (cks, ckd, es, ed, e[5], c[5]);
    initial begin
        #6000;
        begin : sum
            integer i, te, tc;
            te = 0; tc = 0;
            for (i = 0; i < 6; i = i + 1) begin te = te + e[i]; tc = tc + c[i]; end
            $display("RST_BENCH %s %0d errors in %0d checks", (te || tc < 3000) ? "FAIL" : "PASS", te, tc);
        end
        $finish;
    end
endmodule
EOT
sed -i -e "s/\bqfd_rlyr0_1_EW_65x30\b/$R0/g" -e "s/\bqfd_rlyr_1_EW_65x30\b/$RS/g" -e "s/\bqfd_rlyrl_1_EW_65x30\b/$RL/g" "$O/tb.sv"
verilator --binary --timing -Wno-fatal -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-COMBDLY -Wno-LATCH -Wno-INITIALDLY --top-module tb $DEF \
  -Mdir "$O/obj" -o tb "$O/tb.sv" "$O/wrappers.sv" rtl/qwen_split/qfd_fwd_lane.sv rtl/hdc/ot_hdc_cg.sv > "$O/build.log" 2>&1 || {
  echo BUILD_FAILED; tail -20 "$O/build.log"; exit 2; }
"$O/obj/tb" | tee "$O/bench.log" | grep -E 'RST_BENCH|RST_LANE (NF|MISMATCH)'
grep -q 'RST_BENCH PASS' "$O/bench.log"
