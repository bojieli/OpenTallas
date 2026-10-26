`timescale 1ps/1fs
module dsdv_eng_rr_e #(parameter integer RETURN_AGE=640,parameter[29:0]PCBASE=0,parameter integer XQ_MUT=0)(
input wire ck,rst_n,cfg_en,cfg_layer,input wire[1:0]cfg_rank,input wire[52:0]f_ks,
output wire[38:0]rco,input wire[263:0]pci,input wire[275:0]vi_s,output wire[275:0]vo_s,
input wire[275:0]vi_n,output wire[275:0]vo_n,output wire[3:0]st,output wire[67:0]hx_w,input wire[1151:0]hx_res);
assign rco=pci[38:0];assign vo_s=vi_s;assign vo_n=vi_n;assign st=0;assign hx_w=0;
endmodule
module dsdv_eng_rr_h0(input wire ck,input wire[67:0]in_w,output wire[575:0]out_res);assign out_res=0;endmodule
module dsdv_eng_rr_h1(input wire ck,input wire[67:0]in_w,output wire[575:0]out_res);assign out_res=0;endmodule
