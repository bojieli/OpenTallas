`timescale 1ns/1ps
// Four existing HG4 groups, wiring identical to ot_hdc_v41x_attn_tile_s
// at H16, TD32, NBANK5, PWORDS2. The leaf remains unqualified until CLOSED.
module dsdv_svc_attw_hgrp8x_tile (
 input wire clk, rst_n, ld_v, ld_mode,
 input wire [2:0] ld_bank,
 input wire [7:0] ld_grp,
 input wire [1023:0] ld_w,
 input wire ld_w2v, iv,
 input wire [2:0] ibank,
 input wire [575:0] ib,
 output wire ov,
 output wire [511:0] oy,
 output wire [15:0] oflt
);
 wire [3:0] gov;
 for(genvar g=0;g<4;g=g+1)begin:g_g
  wire[255:0] wp;
  for(genvar hh=0;hh<4;hh=hh+1)begin:g_h
   for(genvar word=0;word<2;word=word+1)begin:g_w
    for(genvar row=0;row<2;row=row+1)begin:g_r
     assign wp[((hh*2+word)*2+row)*16+:16]=ld_w[word*512+(row*16+g*4+hh)*16+:16];
    end
   end
  end
  ot_s81svc8_hgrp8x_s81_bounded u_g (
   .clk(clk),.rst_n(rst_n),.gid(8'(g)),.ld_v(ld_v),.ld_mode(ld_mode),
   .ld_bank(ld_bank),.ld_grp(ld_grp),.ld_w(ld_w),.ld_wp(wp),
   .ld_w2v(ld_w2v),.iv(iv),.ibank(ibank),.ib(ib),.ov(gov[g]),
   .oy(oy[g*128+:128]),.oflt(oflt[g*4+:4]));
 end
 assign ov=gov[0];
endmodule
