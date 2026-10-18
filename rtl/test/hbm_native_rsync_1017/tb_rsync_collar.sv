`timescale 1ns/1ps
// HBM-NATIVE 2026-10-17: lockstep r1 (raw rst_n: ot_hbm_static_cfg_collar_r1ref) vs r2 (2-flop pin reset synchroniser)
// collar at the XSER=0 die parameters of col_sfu (CASE 0) / col_idx (CASE 1). One driver feeds both: repeated install
// epochs (select/page, sequential programme rows, operand rows, records with increasing offsets, need, descriptor,
// launch, client busy/done, rare illegal frames) plus random-time mid-run resets. Every output is compared at every
// edge except inside the reset window [assert edge - 3, release edge + 4]: r2 asserts and releases 2 edges after r1, and
// the bench holds every strobe low inside the window (the elastic host ingress is idle around reset: a frame captured
// in the 2 edges before the assert would still land in r2 but not in r1). One PASS/FAIL line.
module tb_rsync_collar;
parameter integer CASE = 0, MUT = 0, NCYC = 80000, SEED = 7;
localparam integer PAGE_W = CASE ? 1 : 3, NS = CASE ? 1 : 2, NPR = CASE ? 6 : 1, NREC = CASE ? 8 : 0,
                   NGO = CASE ? 2 : 1, NB = 2, NF = CASE ? 4 : 1, AW = PAGE_W + 11;
reg clk = 0, rst_n = 0; always #1 clk = ~clk;
reg d_cfg = 0, d_desc = 0, d_launch = 0, d_done = 0; reg [7:0] cfg_target = 8'd120; reg [11:0] cfg_addr = 0;
reg [255:0] cfg_data = 0; reg [NB-1:0] d_busy = 0; reg [NF-1:0] d_fault = 0;
reg hold = 1;                                         // reset window: strobes low, no compare
wire cfg_v = d_cfg & !hold, desc_v = d_desc & !hold, launch_v = d_launch & !hold, c_done = d_done & !hold;
wire [NB-1:0] c_busy = hold ? {NB{1'b0}} : d_busy; wire [NF-1:0] c_fault = hold ? {NF{1'b0}} : d_fault;
wire [NS-1:0] we0, we1; wire [AW-1:0] pa0, pa1; wire [255:0] pd0, pd1; wire [NPR*256-1:0] pr0, pr1;
wire s0, s1, r0, r1, a0, a1, f0, f1; wire [NGO-1:0] g0, g1; wire [220:0] rc0, rc1;
ot_hbm_static_cfg_collar_r1ref #(.PAGE_W(PAGE_W),.NS(NS),.NPR(NPR),.NREC(NREC),.NGO(NGO),.NB(NB),.NF(NF)) u_old(
 .clk(clk),.clk_in(clk),.rst_n(rst_n),.tgt(8'd120),.cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
 .desc_v(desc_v),.launch_v(launch_v),.c_busy(c_busy),.c_done(c_done),.c_fault(c_fault),
 .pw_we(we0),.pw_addr(pa0),.pw_data(pd0),.prm(pr0),.start_v(s0),.go(g0),.rec(rc0),.ready(r0),.active(a0),.fault(f0));
ot_hbm_static_cfg_collar #(.PAGE_W(PAGE_W),.NS(NS),.NPR(NPR),.NREC(NREC),.NGO(NGO),.NB(NB),.NF(NF),.MUT(MUT)) u_new(
 .clk(clk),.clk_in(clk),.rst_n(rst_n),.tgt(8'd120),.cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
 .desc_v(desc_v),.launch_v(launch_v),.c_busy(c_busy),.c_done(c_done),.c_fault(c_fault),
 .pw_we(we1),.pw_addr(pa1),.pw_data(pd1),.prm(pr1),.start_v(s1),.go(g1),.rec(rc1),.ready(r1),.active(a1),.fault(f1));
// Qualified data outputs (fleet 10-17, hdie_col_idx_r1-r2-62981a68f NEEDS_RTL): pw_addr/pw_data are valid only with pw_we and
// rec only with go (the record payload rides its go strobe). r2 asserts reset 2 edges after r1, so a record whose offset
// falls in those 2 edges still fires in r2 (its go is inside the uncompared window) and leaves a different HELD rec
// value after release, while r1 was already in reset: 83 edges of rec-only differences with go = 0 on iverilog 12's
// stimulus. Strobes and every reset-cleared output are still compared on every edge.
wire [AW+256-1:0] pq0 = |we0 ? {pa0,pd0} : 0, pq1 = |we1 ? {pa1,pd1} : 0;
wire [220:0] rq0 = |g0 ? rc0 : 221'd0, rq1 = |g1 ? rc1 : 221'd0;
wire [NS+AW+256+NPR*256+NGO+221+4-1:0] o0 = {we0,pq0,pr0,s0,g0,rq0,r0,a0,f0}, o1 = {we1,pq1,pr1,s1,g1,rq1,r1,a1,f1};
integer cyc = 0, seed = SEED, err = 0, cmp = 0, nst = 0, nwe = 0, ngo = 0, nflt = 0, nrdy = 0, nrst = 0, rlo = 0, win = 0, pre = 0;
// ---- reset process + compare (negedge: outputs settled after the posedge)
always @(negedge clk) begin
  cyc = cyc + 1;
  if (cyc == 6) begin rst_n = 1; win = 5; end
  else if (cyc > 6 && rst_n && win == 0 && pre == 0 && ($urandom(seed) % 2500) == 0) begin hold = 1; pre = 3; end
  else if (pre > 0) begin pre = pre - 1; if (pre == 0) begin rst_n = 0; rlo = 3 + $urandom(seed) % 6; nrst = nrst + 1; end end
  else if (cyc > 6 && !rst_n) begin rlo = rlo - 1; if (rlo <= 0) begin rst_n = 1; win = 5; end end
  else if (win > 0) begin win = win - 1; if (win == 0) hold = 0; end
  if (!hold) begin
    cmp = cmp + 1;
    if (o0 !== o1) begin err = err + 1; if (err <= 5) $display("MISMATCH cyc %0d diff %h", cyc, o0 ^ o1); end
  end
  if (!hold) begin if (s0) nst = nst + 1; if (|we0) nwe = nwe + 1; if (|g0) ngo = ngo + 1; if (f0) nflt = nflt + 1; if (r0) nrdy = nrdy + 1; end
  if (cyc >= NCYC) begin
    $display("RSYNC_COLLAR CASE=%0d MUT=%0d cycles %0d compared %0d resets %0d start_v %0d pw_we %0d go %0d ready %0d fault_cycles %0d errors %0d %s",
             CASE, MUT, cyc, cmp, nrst + 1, nst, nwe, ngo, nrdy, nflt, err,
             (err == 0 && nst >= 20 && nrst >= 10) ? "RSYNC_LOCKSTEP PASS" : "RSYNC_LOCKSTEP FAIL");
    $finish;
  end
end
// ---- driver (posedge-aligned, strobes one edge each)
task automatic frame(input [11:0] a, input [255:0] d);
  begin @(negedge clk); d_cfg = 1; cfg_addr = a; cfg_data = d; @(negedge clk); d_cfg = 0; cfg_data = {8{$urandom(seed)}}; end
endtask
integer s, r, p, off, np [0:3], gap;
reg [255:0] dd;
initial begin
  @(posedge rst_n);
  forever begin
    while (hold) @(negedge clk);
    for (s = 0; s < NS; s = s + 1) begin
      dd = 0; dd[7:0] = s; dd[8 +: PAGE_W] = 0; frame(12'hE00, dd);
      np[s] = 1 + $urandom(seed) % 6;
      for (p = 0; p < np[s]; p = p + 1) frame(12'(p), {8{$urandom(seed)}});
    end
    for (r = 0; r < NPR; r = r + 1) frame(12'h800 + 12'(r), {8{$urandom(seed)}});
    off = 0;
    for (r = 0; r < NREC; r = r + 1) begin
      off = off + 1 + $urandom(seed) % 5; dd = {8{$urandom(seed)}}; dd[31:0] = off; dd[32] = ($urandom(seed) % 5) != 0;
      dd[34:33] = (NGO > 1) ? 2'($urandom(seed)) : {1'b0, 1'($urandom(seed))}; frame(12'hC00 + 12'(r), dd);
    end
    dd = 0; for (s = 0; s < NS; s = s + 1) dd[s*32 +: 32] = np[s]; dd[128] = $urandom(seed) % 2; frame(12'hE01, dd);
    if (($urandom(seed) % 12) == 0) frame(12'h7FF, 0);                  // rare out-of-sequence row: sticky fault
    repeat (2) begin
      @(negedge clk); cfg_target = 8'd120; d_desc = 1; @(negedge clk); d_desc = 0;
      repeat ($urandom(seed) % 4) @(negedge clk);
      d_launch = 1; @(negedge clk); d_launch = 0;
      gap = 10 + $urandom(seed) % 40;
      repeat (gap) begin @(negedge clk); d_busy = NB'(($urandom(seed) % 3) == 0 ? $urandom(seed) : 0); d_done = ($urandom(seed) % 8) == 0; end
      d_busy = 0; d_done = 1; @(negedge clk); d_done = 0; repeat (12) @(negedge clk);
    end
    if (($urandom(seed) % 40) == 0) begin d_fault = 1; @(negedge clk); d_fault = 0; end
  end
end
endmodule
