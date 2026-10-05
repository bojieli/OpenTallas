`timescale 1ps/1fs
// Actual SER<->FAST<->CORE CDC. All two-entry memories plus route holding
// registers are counted in r14 preflight. No asynchronous multibit sampling.
module ot_hbm_r14_clock_bridge #(parameter integer WIDTH=471)(
 input wire src_clk,fast_clk,dst_clk,rst_n,
 input wire iv,output wire ir,input wire [WIDTH-1:0] id,
 output wire ov,input wire ore,output wire [WIDTH-1:0] od);
 wire fv,fr,rv,rr;wire [WIDTH-1:0] fd,rd;
 ot_hbm_r14_fifo2 #(.WIDTH(WIDTH)) first(.wc(src_clk),.wrn(rst_n),.wv(iv),.wr(ir),.wd(id),
   .rc(fast_clk),.rrn(rst_n),.rv(fv),.rr(fr),.rd(fd));
 ot_hbm_r14_route #(.WIDTH(WIDTH),.EDGES(38)) route(.clk(fast_clk),.rst_n(rst_n),.iv(fv),.ir(fr),.id(fd),.ov(rv),.ore(rr),.od(rd));
 ot_hbm_r14_fifo2 #(.WIDTH(WIDTH)) second(.wc(fast_clk),.wrn(rst_n),.wv(rv),.wr(rr),.wd(rd),
   .rc(dst_clk),.rrn(rst_n),.rv(ov),.rr(ore),.rd(od));
endmodule
