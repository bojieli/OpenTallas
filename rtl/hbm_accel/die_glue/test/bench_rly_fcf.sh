#!/bin/bash
# Bench of one F1 forwarded-clock FORK relay master hbfd_rly_<W>_<FLOW>_fc_f<N> (Verilator 5.050).
#   bench_rly_fcf.sh <pass|mut|ckmut<k>> <W> <FLOW> <N> <work dir>
# 20,000 words (zero words under the reset releases), every cycle, every bit, every branch k < N:
#   (1) o<k> == the previous cycle's i AND == o of the existing tile hbfd_rly_<W>_<FLOW> on the same clock (lockstep);
#   (2) clk_out<k> == clk_in at both clock levels;
#   (3) a downstream fc tile clocked by clk_out<k> and fed by o<k> reproduces o<k> one cycle later (each branch forwards
#       a usable clock);  async clear checked mid-stream.
# mut: OT_HBM_RLY_MUT (register bit 0 inverted) -> FAIL.  ckmut<k>: OT_HBM_RLY_FCF_MUT_CLKOUT=k (clk_out<k> held low) -> FAIL.
set -u
mode=$1; W=$2; FL=$3; N=$4; O=$5
M=hbfd_rly_${W}_${FL}
cd "$(dirname "$0")/../../../.."; mkdir -p "$O"
[ -d /home/ubuntu/.local/opentallas-tools/verilator-5.050/bin ] && export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
OP=""; DS=""; CK=""; CHK=""
for k in $(seq 0 $((N-1))); do
  OP="$OP, .o$k(o[$k]), .clk_out$k(ck[$k])"
  DS="$DS  ${M}_fc u_d$k (.clk_in(ck[$k]), .rs(rs), .i(o[$k]), .o(d[$k]), .clk_out(dk[$k]));
"
  CK="$CK || ck[$k] !== c"
  CHK="$CHK      if (o[$k] !== ex || o[$k] !== o_old) err = err + 1;
      if (n > 9010 || (n > 10 && n < 9000)) if (d[$k] !== ex2) perr = perr + 1;
"
done
cat > "$O/tb.sv" <<EOT
module tb;
  reg c = 0, rs = 0; reg [$W-1:0] i = 0; wire [$W-1:0] o_old; wire [$W-1:0] o [$N]; wire [$W-1:0] d [$N];
  wire [$N-1:0] ck, dk; reg [$W-1:0] ex = 0, ex2 = 0;
  integer n = 0, err = 0, cerr = 0, perr = 0;
  $M u_old (.ck(c), .rs(rs), .i(i), .o(o_old));
  ${M}_fc_f$N u_f (.clk_in(c), .rs(rs), .i(i)$OP);
$DS
  always #5 c = ~c;
  always @(c) begin #1 if (1'b0 $CK) cerr = cerr + 1; end
  initial begin
    repeat (3) @(negedge c);
    rs = 1;
    for (n = 0; n < 20000; n = n + 1) begin
      @(negedge c);
$CHK
      if (n == 9000) begin rs = 0; #1 if (o[0] !== '0) err = err + 1; ex = '0; #1 rs = 1; end
      if (n < 4 || (n >= 9000 && n < 9004)) i = '0; else for (int b = 0; b < $W; b++) i[b] = \$urandom;
      @(posedge c); ex2 = ex; ex = i;
    end
    \$display("RLY_FCF_BENCH %s %0d errors %0d clock_errors %0d chain_errors in %0d words (%s_fc_f%0d W=%0d)",
              (err || cerr || perr) ? "FAIL" : "PASS", err, cerr, perr, n, "$M", $N, $W);
    \$finish;
  end
endmodule
EOT
DEF=""; [ "$mode" = mut ] && DEF="-DOT_HBM_RLY_MUT"
case "$mode" in ckmut*) DEF="-DOT_HBM_RLY_FCF_MUT_CLKOUT=${mode#ckmut}";; esac
verilator --binary --timing -Wno-fatal -Wno-WIDTH $DEF --top-module tb -Mdir "$O/obj" -o tb \
  "$O/tb.sv" rtl/lib/ot_rst_relay.sv rtl/hbm_accel/die_glue/ot_hbm_rly.sv rtl/hbm_accel/die_glue/hbfd_rly_masters.sv \
  rtl/hbm_accel/die_glue/ot_hbm_rly_fc.sv rtl/hbm_accel/die_glue/hbfd_rly_fc_masters.sv \
  rtl/hbm_accel/die_glue/ot_hbm_rly_fcf.sv rtl/hbm_accel/die_glue/hbfd_rly_fcf_masters.sv > "$O/build.log" 2>&1 || { echo BUILD_FAILED; tail -5 "$O/build.log"; exit 2; }
"$O/obj/tb" | tee "$O/bench.log" | grep RLY_FCF_BENCH
grep -q 'RLY_FCF_BENCH PASS' "$O/bench.log"
