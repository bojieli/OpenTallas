#!/bin/bash
# ELEM-GAPS/QC 10-18: behavioural bench of the Qwen compute-die reset-tree repeater masters qfd_rst_rep (PAD 0) and
# qfd_rst_rep_p8 (PAD 8) = ot_qwen_rst_rep (rtl/qwen_sys/reset_tree_20261013) -- Verilator 5.050.
# usage: bench_rst_rep.sh <pass|mut|lat> <qfd_rst_rep|qfd_rst_rep_p8> <work dir>
#   pass : the committed kit wrapper (physical/qwen_rst_rep/qfd_rst_rep_masters.sv) must equal the die generator's
#          (gen_relay_rtl.py on a mini die.v); then 20,000 random d levels (incl. long reset-like runs) and on every edge
#          q0 == q1 == d(t - (PAD + 2)) once the pipeline is full.  PASS line: RSTREP_BENCH PASS 0 errors in <n> checks.
#   mut  : the same bench on the wrapper built with ot_qwen_rst_rep MUT=1 (q1 one stage early) -- must FAIL.
#   lat  : the same bench on a wrapper with PAD - 1 / PAD + 1 (0 -> 1) pad flops (wrong tree depth) -- must FAIL.
set -u
mode=$1; M=$2; O=$3
cd "$(dirname "$0")/../.."; mkdir -p "$O"
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
case $M in qfd_rst_rep) PAD=0 ;; qfd_rst_rep_p8) PAD=8 ;; *) echo "bad master $M"; exit 2 ;; esac
cat > "$O/mini_die.v" <<EOT
module qfd_die ();
  wire [0:0] n_ck;
  wire [0:0] n_a;
  wire [0:0] n_b;
  wire [0:0] n_c;
  wire [0:0] n_d;
  qfd_rst_rep r0 (.clk(n_ck), .d(n_a), .q0(n_b), .q1(n_c));
  qfd_rst_rep_p8 r1 (.clk(n_ck), .d(n_b), .q0(n_d));
endmodule
EOT
python3 tools/qwen_split/gen_relay_rtl.py "$O/mini_die.v" "$O/gen.sv" > "$O/gen.json" || { echo GEN_FAILED; exit 2; }
K=physical/qwen_rst_rep/qfd_rst_rep_masters.sv
if ! diff <(grep -v '^`timescale\|^//' "$O/gen.sv") <(grep -v '^`timescale\|^//' $K) > "$O/wrapper.diff"; then
  echo "RSTREP_BENCH FAIL committed wrapper differs from the die generator"; cat "$O/wrapper.diff"; exit 1; fi
W="$O/dut.sv"; cp $K "$W"
case $mode in
  pass) ;;
  mut) sed -i "s/#(.PAD(\([0-9]*\)))/#(.PAD(\1), .MUT(1))/" "$W" ;;
  lat) if [ $PAD = 0 ]; then sed -i "s/#(.PAD(0))/#(.PAD(1))/" "$W"; else sed -i "s/#(.PAD(8))/#(.PAD(7))/" "$W"; fi ;;
  *) echo "bad mode $mode"; exit 2 ;;
esac
cat > "$O/tb.sv" <<EOT
\`timescale 1ns/1ps
module tb;
    localparam integer L = $PAD + 2;
    reg clk = 0; always #5 clk = ~clk;
    reg d = 1; wire q0, q1;
    reg [L+64:0] hist = 0;
    integer e = 0, err = 0, chk = 0, run = 0;
    integer seed = 32'h5eed$PAD;
    $M dut (.clk(clk), .d(d), .q0(q0), .q1(q1));
    always @(posedge clk) begin
        // sample the outputs just before the edge updates them: q(e) = d launched L edges earlier
        if (e > L + 1) begin
            chk = chk + 1;
            if (q0 !== hist[L - 1] || q1 !== hist[L - 1]) begin
                err = err + 1;
                if (err < 6) \$display("ERR edge %0d: d(t-%0d)=%b q0=%b q1=%b", e, L, hist[L - 1], q0, q1);
            end
        end
        hist <= {hist[L+63:0], d};
        e <= e + 1;
        // reset-like level runs (1..3*L edges) mixed with single-edge toggles
        if (run == 0) begin run = 1 + ((\$random(seed) & 7) == 0 ? (\$random(seed) & 32'h7fff) % (3 * L + 1) : 0); d <= \$random(seed); end
        else run = run - 1;
        if (e == 20000) begin
            if (err == 0) \$display("RSTREP_BENCH PASS 0 errors in %0d checks ($M PAD $PAD latency %0d)", chk, L);
            else \$display("RSTREP_BENCH FAIL %0d errors in %0d checks ($M)", err, chk);
            \$finish;
        end
    end
endmodule
EOT
verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb -Mdir "$O/obj" \
  "$O/tb.sv" "$W" rtl/qwen_sys/reset_tree_20261013/ot_qwen_rst_rep.sv > "$O/build.log" 2>&1 || { echo "RSTREP_BENCH BUILD_FAILED"; tail -20 "$O/build.log"; exit 2; }
"$O/obj/Vtb" | tee "$O/run.log"
grep -q "RSTREP_BENCH PASS" "$O/run.log"
