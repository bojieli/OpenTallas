`timescale 1ns/1ps
// PATH-QC-SRAMIF vmr miter: ORIG_vmr (main) vs qfd_dv_s8x_vmr #(.MIF(1)), lockstep random stimulus; q(t+1) == orig q(t),
// fault equal.  Rows restricted to 0..15 so reads hit written rows and read/write collisions occur.
module tb;
  parameter integer N = 20000;
  reg ck = 0; always #1 ck = ~ck;
  reg rst_n;
  reg [7:0] re; reg [8*24-1:0] addr; reg [7:0] vm_we; reg [8*24-1:0] vm_waddr; reg [8*32-1:0] vm_wdata;
  reg w16_we; reg [23:0] w16_addr; reg [511:0] w16_data; reg w1_we; reg [23:0] w1_addr; reg [31:0] w1_data;
  wire [255:0] o_q, n_q; wire o_f, n_f;
  ORIG_vmr ov (.ck(ck), .rst_n(rst_n), .re(re), .addr(addr), .q(o_q), .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata),
    .w16_we(w16_we), .w16_addr(w16_addr), .w16_data(w16_data), .w1_we(w1_we), .w1_addr(w1_addr), .w1_data(w1_data), .fault(o_f));
  qfd_dv_s8x_vmr #(.MIF(1)) nv (.ck(ck), .rst_n(rst_n), .re(re), .addr(addr), .q(n_q), .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata),
    .w16_we(w16_we), .w16_addr(w16_addr), .w16_data(w16_data), .w1_we(w1_we), .w1_addr(w1_addr), .w1_data(w1_data), .fault(n_f));
  wire [255:0] z_q;
  qfd_dv_s8x_vmr #(.MIF(0)) zv (.ck(ck), .rst_n(rst_n), .re(re), .addr(addr), .q(z_q), .vm_we(vm_we), .vm_waddr(vm_waddr), .vm_wdata(vm_wdata),
    .w16_we(w16_we), .w16_addr(w16_addr), .w16_data(w16_data), .w1_we(w1_we), .w1_addr(w1_addr), .w1_data(w1_data), .fault());
  reg [255:0] o_q_d; always @(posedge ck) o_q_d <= o_q;
  integer c, i, e = 0, ef = 0, ez = 0, nz = 0, seed = 1;
  reg [63:0] xs;
  function [31:0] r32; input dummy; begin xs = xs ^ (xs << 13); xs = xs ^ (xs >> 7); xs = xs ^ (xs << 17); r32 = xs[31:0]; end endfunction
  reg [23:0] base; reg [3:0] row;
  task rnd; begin
    // reads: lanes share row / bank (legal), offsets per lane; occasionally illegal
    row = r32(0); base = {10'd0, 6'd0, row, 4'd0} | (r32(0) & 24'h8);
    re = (r32(0) & 3) == 0 ? 8'd0 : ((r32(0) & 15) == 0 ? r32(0) : 8'hff);
    for (i = 0; i < 8; i = i + 1) addr[24*i +: 24] = ((r32(0) & 63) == 0) ? r32(0) : (base | (r32(0) & 7));
    // VM writes
    row = r32(0);
    vm_we = (r32(0) & 3) == 0 ? r32(0) : 8'd0;
    for (i = 0; i < 8; i = i + 1) vm_waddr[24*i +: 24] = ((r32(0) & 63) == 0) ? r32(0) : ({10'd0, 6'd0, row, 4'd0} | (r32(0) & 15));
    for (i = 0; i < 8; i = i + 1) vm_wdata[32*i +: 32] = r32(0);
    w16_we = (r32(0) & 15) == 0; w16_addr = ((r32(0) & 31) == 0) ? r32(0) : {10'd0, 6'd0, row, 4'd0};
    for (i = 0; i < 16; i = i + 1) w16_data[32*i +: 32] = r32(0);
    w1_we = (r32(0) & 7) == 0; w1_addr = ((r32(0) & 31) == 0) ? r32(0) : ({10'd0, 6'd0, 4'(r32(0)), 4'd0} | (r32(0) & 15)); w1_data = r32(0);
  end endtask
  initial begin
    if (!$value$plusargs("seed=%d", seed)) seed = 1;
    xs = 64'h9E3779B97F4A7C15 ^ {32'd0, seed};
    rst_n = 0; rnd;
    for (c = 0; c < N; c = c + 1) begin
      @(negedge ck);
      if (c > 4) rst_n = 1;
      if (c > 12) begin
        if (n_q !== o_q_d) begin e = e + 1; if (e < 4) $display("VMR MISMATCH c=%0d", c); end
        if (n_f !== o_f) begin ef = ef + 1; if (ef < 4) $display("FAULT MISMATCH c=%0d", c); end
        if (z_q !== o_q) ez = ez + 1;
        if (o_q_d != 0) nz = nz + 1;
      end
      rnd;
    end
    $display("MITER_VMR N=%0d seed=%0d q_mism=%0d fault_mism=%0d mif0_vs_orig=%0d nonzero_cmp=%0d", N, seed, e, ef, ez, nz);
    $finish;
  end
endmodule
