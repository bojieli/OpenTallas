`timescale 1ns/1ps
// Width-aware native 1R1W composition, same port/one-edge/read-before-write
// contract as qfd_dv_sram_bank64 at b99c1cb10. No command/output capture.
// One logical root owns every identifiable native clock sink in this group.
module ot_coll_sram_bank64 #(parameter integer W=546)(
 input wire clk,r_ce_in,w_ce_in,input wire[4:0] r_addr_in,w_addr_in,
 output wire[W-1:0] rd_out,input wire[W-1:0] wd_in,w_mask_in
);
 localparam integer N=(W+63)/64,P=64*N-W;
 wire[W-1:0] useful_data;
`ifdef OT_COLL_B4_MUT_R513
 assign useful_data=(W==514) ? (wd_in & ~(W'(1)<<513)) : wd_in;
`else
 assign useful_data=wd_in;
`endif
 wire[64*N-1:0] data={{P{1'b0}},useful_data},mask={{P{1'b0}},w_mask_in};
 wire[64*N-1:0] result;
 for(genvar b=0;b<N;b=b+1) begin:g_bank
  ot_sram_1r1w_32x64_m1 u_m(.clk(clk),.r_ce_in(r_ce_in),.r_addr_in(r_addr_in),
   .rd_out(result[64*b+:64]),.w_ce_in(w_ce_in),.w_addr_in(w_addr_in),
   .wd_in(data[64*b+:64]),.w_mask_in(mask[64*b+:64]));
 end
 assign rd_out=result[W-1:0];
 initial if(W<1 || W>546) $error("COLL_BANK64_WIDTH");
endmodule
