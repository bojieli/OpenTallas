`timescale 1ns/1ps
// HBM-NATIVE 2026-10-17: lockstep r1 (raw rst_n: ot_static_cmd_target_r1ref) vs r2 (RSYNC=1, 2-flop pin reset sync)
// at the cp_svg die parameters (MODE 0, AWA 10, AWB 7, RBW 7, RCW 8, NA 2, NF 1, TGT_PIN 1, tgt 64). One driver feeds
// both: window A / window B rows, legal and illegal descriptors, launches, client active/fault, rare foreign targets,
// plus random-time mid-run resets. Every output is compared at every edge except inside the reset window [assert
// edge - 3, release edge + 4] (strobes held low there; r2 asserts and releases 2 edges after r1). `cycle` is the
// free-running counter from reset release, so r2's is compared as cycle_r2 + 2 == cycle_r1. One PASS/FAIL line.
module tb_rsync_cmd;
parameter integer RSMUT = 0, NCYC = 80000, SEED = 11;
reg clk = 0, rst_n = 0; always #1 clk = ~clk;
reg d_cfg = 0, d_desc = 0, d_launch = 0; reg [7:0] cfg_target = 8'd64; reg [11:0] cfg_addr = 0; reg [255:0] cfg_data = 0;
reg [11:0] desc_base = 0; reg [12:0] desc_limit = 0; reg [15:0] desc_loops = 1; reg [1:0] d_act = 0; reg d_flt = 0;
reg hold = 1;
wire cfg_v = d_cfg & !hold, desc_v = d_desc & !hold, launch_v = d_launch & !hold;
wire [1:0] tgt_active = hold ? 2'b0 : d_act; wire tgt_fault = d_flt & !hold;
wire aw0, aw1, bw0, bw1, rv0, rv1, cv0, cv1, cf0, cf1, f0, f1, ac0, ac1; wire [9:0] aa0, aa1; wire [6:0] ba0, ba1, rb0, rb1;
wire [7:0] rcn0, rcn1; wire [255:0] ad0, ad1, bd0, bd1; wire [0:0] cm0, cm1; wire [31:0] cy0, cy1;
ot_static_cmd_target_r1ref #(.TARGET(8'hff),.TGT_PIN(1),.MODE(0),.AWA(10),.AWB(7),.RBW(7),.RCW(8),.NA(2),.NF(1)) u_old(
 .clk(clk),.rst_n(rst_n),.tgt(8'd64),.cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
 .desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),.launch_v(launch_v),
 .tgt_active(tgt_active),.tgt_fault(tgt_fault),.a_we(aw0),.a_addr(aa0),.a_data(ad0),.b_we(bw0),.b_addr(ba0),.b_data(bd0),
 .run_v(rv0),.run_base(rb0),.run_count(rcn0),.cmd_v(cv0),.cmd(cm0),.cycle(cy0),.configured(cf0),.fault(f0),.active(ac0));
ot_static_cmd_target #(.TARGET(8'hff),.TGT_PIN(1),.MODE(0),.AWA(10),.AWB(7),.RBW(7),.RCW(8),.NA(2),.NF(1),.RSYNC(1),.RSMUT(RSMUT)) u_new(
 .clk(clk),.rst_n(rst_n),.tgt(8'd64),.cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
 .desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),.desc_loops(desc_loops),.launch_v(launch_v),
 .tgt_active(tgt_active),.tgt_fault(tgt_fault),.a_we(aw1),.a_addr(aa1),.a_data(ad1),.b_we(bw1),.b_addr(ba1),.b_data(bd1),
 .run_v(rv1),.run_base(rb1),.run_count(rcn1),.cmd_v(cv1),.cmd(cm1),.cycle(cy1),.configured(cf1),.fault(f1),.active(ac1));
wire [600:0] o0 = {aw0,aa0,ad0,bw0,ba0,bd0,rv0,rb0,rcn0,cv0,cm0,cy0,cf0,f0,ac0}, o1 = {aw1,aa1,ad1,bw1,ba1,bd1,rv1,rb1,rcn1,cv1,cm1,cy1+32'd2,cf1,f1,ac1};
integer cyc = 0, seed = SEED, err = 0, cmp = 0, nrun = 0, naw = 0, nbw = 0, nflt = 0, ncf = 0, nrst = 0, rlo = 0, win = 0, pre = 0;
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
    if (rv0) nrun = nrun + 1; if (aw0) naw = naw + 1; if (bw0) nbw = nbw + 1; if (f0) nflt = nflt + 1; if (cf0) ncf = ncf + 1;
  end
  if (cyc >= NCYC) begin
    $display("RSYNC_CMD RSMUT=%0d cycles %0d compared %0d resets %0d run_v %0d a_we %0d b_we %0d configured_cycles %0d fault_cycles %0d errors %0d %s",
             RSMUT, cyc, cmp, nrst + 1, nrun, naw, nbw, ncf, nflt, err,
             (err == 0 && nrun >= 20 && nrst >= 10) ? "RSYNC_LOCKSTEP PASS" : "RSYNC_LOCKSTEP FAIL");
    $finish;
  end
end
task automatic frame(input [11:0] a);
  begin @(negedge clk); d_cfg = 1; cfg_addr = a; cfg_data = {8{$urandom(seed)}}; @(negedge clk); d_cfg = 0; end
endtask
integer n, b, l;
initial begin
  @(posedge rst_n);
  forever begin
    while (hold) @(negedge clk);
    cfg_target = (($urandom(seed) % 20) == 0) ? 8'd65 : 8'd64;
    repeat (1 + $urandom(seed) % 6) frame(($urandom(seed) % 2) ? 12'($urandom(seed) % 1024) : 12'h400 + 12'($urandom(seed) % 128));
    if (($urandom(seed) % 25) == 0) frame(12'hC00);                          // illegal window: sticky fault
    cfg_target = 8'd64;
    b = $urandom(seed) % 100; l = b + 1 + $urandom(seed) % 28;
    @(negedge clk); desc_base = 12'(b); desc_limit = 13'(l); desc_loops = (($urandom(seed) % 30) == 0) ? 16'd2 : 16'd1;
    d_desc = 1; @(negedge clk); d_desc = 0; repeat ($urandom(seed) % 3) @(negedge clk);
    d_launch = 1; @(negedge clk); d_launch = 0;
    repeat (5 + $urandom(seed) % 20) begin @(negedge clk); d_act = 2'($urandom(seed) % 4 == 0 ? $urandom(seed) : 0); end
    d_act = 0; d_flt = (($urandom(seed) % 60) == 0); @(negedge clk); d_flt = 0; repeat (4) @(negedge clk);
  end
end
endmodule
