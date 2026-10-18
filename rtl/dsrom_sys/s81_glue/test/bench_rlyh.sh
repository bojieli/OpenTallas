#!/bin/bash
# S81-LAND2 half-cycle lane bench (Verilator 5.050).  usage: bench_rlyh.sh <pass|mut> <master> <W> <work dir> [N stations]
# N (default 3) stations of <master> chained as on the die: station 0 ck = the source root clock, station k+1 ck =
# station k ck_o (DIE-CLOCK F1).  The source launches one random word per root cycle (i changes at the root negedge).
# Expected with HC = 1 (ck_o = ~ck): station k captures half a period after station k-1, so word m (driven before root
# posedge P_m) is on station k's o from edge P_m + k*T/2 until the next same-phase edge.  Checked at every half period:
#   after root posedge P_m: every EVEN station k holds w[m - k/2];   after root negedge: every ODD k holds w[m - (k-1)/2]
# i.e. the lane delivers word m at station N-1 after (N-1)/2 root cycles + 1 (N stations = ceil(N/2) cycles, half of
# today's N).  20,000 words; async clear checked mid-stream (RSREG = 1: each station's first ck edge after release holds 0,
# so exactly the first word after release is a bubble at every station).
# mut: the OT_DVRLYH_MUT build (HC 1 masters with the non-inverting ck_o pair: the full-cycle relay) -- must FAIL.
set -u
mode=$1; M=$2; W=$3; O=$4; N=${5:-3}
cd "$(dirname "$0")/../../../.."; mkdir -p "$O"
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
cat > "$O/tb.sv" <<EOT
module tb;
  localparam int N = $N, W = $W, H = 8;
  reg ck = 0, rs = 0;
  reg [W-1:0] i = 0;
  wire [W-1:0] o [N];
  wire ckc [N+1];
  reg [W-1:0] w [H];
  integer n = 0, err = 0, chk = 0, m = 0, k = 0, warm = 0;
  assign ckc[0] = ck;
  for (genvar s = 0; s < N; s++) begin : g
    $M st (.ck(ckc[s]), .rs(rs), .i(s == 0 ? i : o[s == 0 ? 0 : s - 1]), .o(o[s]), .ck_o(ckc[s + 1]));
  end
  always #5 ck = ~ck;
  function automatic [W-1:0] word(input integer age); word = (m - age >= warm) ? w[(m - age) % H] : '0; endfunction
  initial begin
    for (k = 0; k < H; k++) w[k] = '0;
    repeat (3) @(negedge ck); rs = 1; repeat (2) @(negedge ck);
    m = 0; warm = 0;
    for (n = 0; n < 20000; n = n + 1) begin
      for (int b = 0; b < W; b++) i[b] = \$urandom;
      w[m % H] = i;
      @(posedge ck); #1;
      for (k = 0; k < N; k += 2) begin chk++; if (o[k] !== word(k / 2)) err++; end
      @(negedge ck); #1;
      for (k = 1; k < N; k += 2) begin chk++; if (o[k] !== word((k - 1) / 2)) err++; end
      m = m + 1;
      if (n == 9000) begin rs = 0; #1 for (k = 0; k < N; k++) if (o[k] !== '0) err++; #1 rs = 1; warm = m + 1; end
    end
    \$display("RLYH_BENCH %s %0d errors in %0d checks, %0d words, %0d stations (%s W=%0d, half-cycle hops)", err ? "FAIL" : "PASS", err, chk, n, N, "$M", W);
    \$finish;
  end
endmodule
EOT
DEF=""; [ "$mode" = mut ] && DEF="-DOT_DVRLYH_MUT"
verilator --binary --timing -Wno-fatal -Wno-WIDTH $DEF --top-module tb -Mdir "$O/obj" -o tb \
  "$O/tb.sv" rtl/dsrom_sys/s81_glue/ot_s81_rly.sv rtl/dsrom_sys/s81_glue/dsfd_rly_masters*.sv > "$O/build.log" 2>&1 || { echo BUILD_FAILED; tail -5 "$O/build.log"; exit 2; }
"$O/obj/tb" | tee "$O/bench.log" | grep RLYH_BENCH
grep -q 'RLYH_BENCH PASS' "$O/bench.log"
