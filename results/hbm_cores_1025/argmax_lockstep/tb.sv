`timescale 1ns/1ps
module tb;
  parameter integer FAST = 0;
  localparam LP=8, IW=17;
  reg clk=0, rst_n=0; always #1 clk=~clk;
  reg in_v=0,in_last=0,in_bias_en=0; reg [LP-1:0] in_mask=0; reg [LP*32-1:0] in_vals=0,in_bias=0;
  wire ov_n,ov_r,on_n,on_r,f_n,f_r,rf_n,rf_r; wire [IW-1:0] oi_n,oi_r; wire [31:0] oval_n,oval_r;
  ot_hgi_argmax18_value_m   #(.FAST(FAST)) dut(.clk(clk),.rst_n(rst_n),.global_offset(25'd0),.out_range_fault(rf_n),.in_v(in_v),.in_last(in_last),.in_bias_en(in_bias_en),.in_mask(in_mask),.in_vals(in_vals),.in_bias(in_bias),.out_v(ov_n),.out_idx(oi_n),.out_nan(on_n),.out_value(oval_n),.fault(f_n));
  ot_hgi_argmax18_value_ref #(.FAST(FAST)) ref0(.clk(clk),.rst_n(rst_n),.global_offset(25'd0),.out_range_fault(rf_r),.in_v(in_v),.in_last(in_last),.in_bias_en(in_bias_en),.in_mask(in_mask),.in_vals(in_vals),.in_bias(in_bias),.out_v(ov_r),.out_idx(oi_r),.out_nan(on_r),.out_value(oval_r),.fault(f_r));
  function [32:0] okey(input [31:0] x); reg [31:0] c; begin
    if (x[30:23]==8'hFF && x[22:0]!=0) okey={1'b1,32'hFFFFFFFF};
    else begin c=(x==32'h80000000)?32'd0:x; okey={1'b0, c[31]?~c:(c|32'h80000000)}; end end endfunction
  // golden (bias_en=0 rows only)
  reg [IW-1:0] gq_idx[0:4095]; reg gq_chk[0:4095]; integer gw=0, gr=0;
  reg [32:0] bestk; reg [IW-1:0] besti; reg bestv; integer base;
  integer mism=0, gmism=0, nout=0, cyc=0, b, j, rows=0, seed;
  function [31:0] rv(input integer s); integer r; begin r=$random(seed);
    case (r & 7) 0: rv=32'h7FC00001; 1: rv=32'h80000000; 2: rv=32'h0; 3: rv=32'h3F800000 | (($random(seed)&3)<<21); default: rv=$random(seed) & 32'hC7FFFFFF; endcase end endfunction
  always @(posedge clk) if (rst_n) begin
    cyc=cyc+1;
    if ({ov_n,oi_n,on_n,oval_n,f_n,rf_n} !== {ov_r,oi_r,on_r,oval_r,f_r,rf_r}) begin mism=mism+1; if (mism<4) $display("MISMATCH cyc %0d new v%b i%0d ref v%b i%0d",cyc,ov_n,oi_n,ov_r,oi_r); end
    if (ov_r) begin nout=nout+1; if (gq_chk[gr] && oi_r !== gq_idx[gr]) begin gmism=gmism+1; if (gmism<4) $display("GOLDEN MISMATCH row %0d got %0d exp %0d",gr,oi_r,gq_idx[gr]); end gr=gr+1; end
  end
  integer nb, r, lb, gap; reg bias_nx;
  initial begin
    seed = 1025 + FAST;
    repeat(5) @(negedge clk); rst_n=1;
    for (r=0; r<400; r=r+1) begin if (r%100==0) $display("row %0d t=%0t", r, $time);
      nb = 1 + ($random(seed) & 3); bias_nx = (($random(seed) & 3)==0); bestv=0; base=0;
      for (b=0; b<nb; b=b+1) begin
        @(negedge clk);
        in_v=1; in_last=(b==nb-1); in_bias_en=bias_nx; in_mask = (b==nb-1) ? ({LP{1'b1}} >> ($random(seed)&7)) : {LP{1'b1}};
        if (in_mask==0) in_mask=1;
        for (j=0;j<LP;j=j+1) begin in_vals[32*j+:32]=rv(0); in_bias[32*j+:32]=rv(0);
          if (in_mask[j]) if (!bestv || okey(in_vals[32*j+:32]) > bestk) begin bestv=1; bestk=okey(in_vals[32*j+:32]); besti=base+j; end end
        base=base+LP;
      end
      gq_idx[gw]=besti; gq_chk[gw]=!bias_nx; gw=gw+1;
      gap=$random(seed)&3; if (gap) begin @(negedge clk); in_v=0; in_last=0; repeat(gap-1) @(negedge clk); end
    end
    @(negedge clk); in_v=0; in_last=0; repeat(60) @(negedge clk);
    $display("LOCKSTEP FAST=%0d rows %0d outs %0d new-vs-ref mismatches %0d golden mismatches %0d (golden-checked rows unbiased)", FAST, gw, nout, mism, gmism);
    $finish;
  end
endmodule
