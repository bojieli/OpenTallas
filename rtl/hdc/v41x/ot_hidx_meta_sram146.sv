`timescale 1ns/1ps
`default_nettype none
module ot_hidx_meta_sram146 #(parameter integer D=146)(input wire clk,clk_mem,input wire[24:0]d,output reg[24:0]q);
 reg[24:0]din;reg[7:0]wp;wire[7:0]rp=wp-8'(D-3);wire[255:0]wd,rd,mask;wire[35:0]repair_zero;
`ifndef SYNTHESIS
 initial wp=0;
`endif
 always@(posedge clk)begin din<=d;wp<=wp+1'b1;q<=rd[24:0];end
 assign wd[24:0]=din;
`ifdef SYNTHESIS
 for(genvar g=0;g<16;g=g+1)begin:g_hi
  wire one;(*keep=1,dont_touch=1*)TIEHIx1_ASAP7_75t_R u_t(.H(one));assign mask[16*g+:16]={16{one}};
 end
 for(genvar g=0;g<15;g=g+1)begin:g_lo
  wire zero;(*keep=1,dont_touch=1*)TIELOx1_ASAP7_75t_R u_t(.L(zero));
  for(genvar k=0;k<16;k=k+1)if(25+16*g+k<256)begin:g_bit assign wd[25+16*g+k]=zero;end
 end
 for(genvar g=0;g<3;g=g+1)begin:g_repair
  wire zero;(*keep=1,dont_touch=1*)TIELOx1_ASAP7_75t_R u_t(.L(zero));
  for(genvar k=0;k<12;k=k+1)begin:g_bit assign repair_zero[12*g+k]=zero;end
 end
`else
 assign wd[255:25]=0;assign mask={256{1'b1}};assign repair_zero=0;
`endif
 ot_sram_1r1w_256x256_m2_r2c2 u_mem(.clk(clk_mem),.r_ce_in(1'b1),.r_addr_in(rp),.rd_out(rd),.w_ce_in(1'b1),.w_addr_in(wp),.wd_in(wd),.w_mask_in(mask),.rr_en(repair_zero[1:0]),.rr_addr(repair_zero[15:2]),.cr_en(repair_zero[17:16]),.cr_sel(repair_zero[33:18]));
endmodule
`default_nettype wire
