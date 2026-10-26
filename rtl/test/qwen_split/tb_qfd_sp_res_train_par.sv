`timescale 1ns/1ps
// Q-ELEM-CMP (2026-10-16): production-shape bench of the three die masters qfd_sp_res_train_par_{0,1,2} (the die's
// composition: one train command bundle fanned out to the three bands, every ck_bank tied to the band clock as in die.v).
// Independent reference = the documented static calendar (qfd_res_train_par.sv header):
//   burst k = 8 t + i is captured at cycle t*stride + i (cycle 0 = the train_start edge); its slot s (< NS) leaves band b
//   at F(k,s) = D + b*NS + t*P + i*NS + s, P = max(8 NS, stride); the payload beat is on rb after edge F+1 (bank emit
//   register + rb register), {valid = we|end, end, end & !we, addr 20, mask 16, data 512}, end = (b == 2 && s == NS-1);
//   a marker train (payload_write 0) puts {1,1,1,0...} on band 2's rb after edge F(k, NS-1) for every burst.
// Every rb word of every band on every edge is compared (zero outside its slots); fault must stay 0.  Trains use the
// legal Qwen shapes: payload trains count 1..3, marker trains 1..8, NS 1/2/4/8, stride 8..255.
module tb_qfd_sp_res_train_par;
parameter integer NTRAIN=60, SEED=1;
localparam integer D=2;
reg ck=0; always #5 ck=~ck;
reg rst_n=0, tstart=0, tpay=0; reg [3:0] tcount=0, tns=0; reg [31:0] tstride=0;
reg [4424:0] rq [0:2];
wire [550:0] rb [0:2]; wire [2:0] flt;
`define RTP_CK .ck(ck),.ck_bank0(ck),.ck_bank1(ck),.ck_bank2(ck),.ck_bank3(ck),.ck_bank4(ck),.ck_bank5(ck),.ck_bank6(ck),.ck_bank7(ck),.ck_bank8(ck),.ck_bank9(ck),.ck_bank10(ck),.ck_bank11(ck),.ck_bank12(ck),.ck_bank13(ck),.ck_bank14(ck),.ck_bank15(ck),.ck_bank16(ck),.ck_bank17(ck),.ck_bank18(ck),.ck_bank19(ck),.ck_bank20(ck),.ck_bank21(ck),.ck_bank22(ck),.ck_bank23(ck)
`define RTP_CMD .rst_n(rst_n),.train_start(tstart),.train_count(tcount),.capture_stride(tstride),.payload_write(tpay),.slot_count(tns)
qfd_sp_res_train_par_0 b0(`RTP_CK, `RTP_CMD, .rq(rq[0]), .rb(rb[0]), .fault(flt[0]));
qfd_sp_res_train_par_1 b1(`RTP_CK, `RTP_CMD, .rq(rq[1]), .rb(rb[1]), .fault(flt[1]));
qfd_sp_res_train_par_2 b2(`RTP_CK, `RTP_CMD, .rq(rq[2]), .rb(rb[2]), .fault(flt[2]));
// expected rb per band per edge (sparse): index = edge number
localparam integer HZ = 1<<17;
reg [550:0] exp_rb [0:2][0:HZ-1];
reg [4424:0] sched_rq [0:2][0:HZ-1];
reg sched_v [0:HZ-1];
reg cmd_v [0:HZ-1]; integer cmd_c [0:HZ-1], cmd_s [0:HZ-1], cmd_p [0:HZ-1], cmd_n [0:HZ-1]; integer last_edge = 0;
integer edge_n=0, err=0, words=0, rows=0, b, k, s, t, i, tr, e0, P, F, c, NS, stride, pay, stop, cyc, seed;
reg [551:0] w; reg we;
always @(posedge ck) edge_n <= edge_n + 1;
// drive rq for the coming edge at each negedge
always @(negedge ck) for (b = 0; b < 3; b = b + 1) rq[b] = sched_v[edge_n] ? sched_rq[b][edge_n] : '0;
// compare after each edge
always @(negedge ck) if (rst_n) begin
  for (b = 0; b < 3; b = b + 1) begin
    if (rb[b] !== exp_rb[b][edge_n - 1]) begin err = err + 1;
      if (err < 8) $display("ERR edge %0d band %0d rb[550:548]=%b exp=%b data0=%h exp=%h", edge_n - 1, b, rb[b][550:548], exp_rb[b][edge_n-1][550:548], rb[b][31:0], exp_rb[b][edge_n-1][31:0]); end
    if (rb[b][550]) words = words + 1;
  end
  if (flt !== 3'b000) begin err = err + 1; if (err < 8) $display("ERR edge %0d fault %b", edge_n - 1, flt); end
end
function automatic integer fb(input integer bb, input integer kk, input integer ns, input integer p);
  fb = D + bb*ns + (kk/8)*p + (kk%8)*ns;
endfunction
initial begin
  seed = SEED;
  for (k = 0; k < HZ; k = k + 1) begin sched_v[k] = 0; cmd_v[k] = 0; for (b = 0; b < 3; b = b + 1) begin exp_rb[b][k] = '0; sched_rq[b][k] = '0; end end
  // plan all trains on an absolute edge timeline (edge index = the posedge that samples train_start)
  e0 = 40;
  for (tr = 0; tr < NTRAIN; tr = tr + 1) begin
    pay = (tr % 4 != 3);
    c = pay ? 1 + ($urandom(seed) % 3) : 1 + ($urandom % 8); seed = seed + 1;
    NS = 1 << ($urandom % 4);
    stride = (c > 1) ? 8 + ($urandom % 248) : 8 + ($urandom % 64);
    P = (stride > 8*NS) ? stride : 8*NS;
    stop = fb(2, 8*c-1, NS, P) + NS;
    // record the command at e0 (stored in band 0's slot of a side table via sched words)
    sched_v[e0] = 1;
    for (k = 0; k < 8*c; k = k + 1) begin
      t = k / 8; i = k % 8; cyc = t*stride + i;
      sched_v[e0 + cyc] = 1;
      for (b = 0; b < 3; b = b + 1) begin
        sched_rq[b][e0 + cyc][4424] = 1'b1;
        for (s = 0; s < 8; s = s + 1) begin
          we = pay && (s < NS) && ($urandom % 5 != 0);
          for (int q = 0; q < 16; q++) w[32*q +: 32] = $urandom;
          w[527:512] = $urandom; w[547:528] = $urandom; w[551:548] = 0;
          if (pay) sched_rq[b][e0 + cyc][552*s +: 552] = w;
          sched_rq[b][e0 + cyc][4416 + s] = we;
          if (pay && s < NS) begin
            F = fb(b, k, NS, P) + s;
            exp_rb[b][e0 + F + 1] = {we || (b == 2 && s == NS-1), (b == 2 && s == NS-1), (b == 2 && s == NS-1) && !we,
                                    we ? w[547:528] : 20'd0, we ? w[527:512] : 16'd0, we ? w[511:0] : 512'd0};
            if (we) rows = rows + 1;
          end
        end
      end
      if (!pay) exp_rb[2][e0 + fb(2, k, NS, P) + NS - 1] = {3'b111, 548'd0};
    end
    // command table (packed into a parallel array by edge)
    cmd_v[e0] = 1; cmd_c[e0] = c; cmd_s[e0] = stride; cmd_p[e0] = pay; cmd_n[e0] = NS;
    e0 = e0 + stop + 2 + ($urandom % 6);
  end
  last_edge = e0 + 20;
end
always @(negedge ck) begin
  tstart = 0;
  if (cmd_v[edge_n] === 1'b1) begin tstart = 1; tcount = 4'(cmd_c[edge_n]); tstride = 32'(cmd_s[edge_n]); tpay = cmd_p[edge_n][0]; tns = 4'(cmd_n[edge_n]); end
end
initial begin
  repeat (4) @(negedge ck); rst_n = 1;
  #1; wait (last_edge > 0); while (edge_n < last_edge) @(negedge ck);
  if (err == 0 && words > 0)
    $display("RTP_BENCH PASS trains=%0d rows=%0d rb_words=%0d errors=0", NTRAIN, rows, words);
  else
    $display("RTP_BENCH FAIL trains=%0d rows=%0d rb_words=%0d errors=%0d", NTRAIN, rows, words, err);
  $finish;
end
endmodule
