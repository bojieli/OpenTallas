`timescale 1ns/1ps
`default_nettype none
// Local SO copy must retain a word for the actual matched peer age.
// D32 covers the N0/E17 window; D8 would overwrite that word before read.
// Source-only assembly; no CLOSED landing view is claimed.
module dsdv_pv_local_land_276(input wire ck_f,input wire[275:0] i,
 input wire ck,rs,input wire[5:0] k,output wire[275:0]o,output wire fault);
 ot_s81_land #(.W(276),.D(32),.KW(6)) u_ring(.ck_f(ck_f),.i(i),.ck(ck),.rs(rs),.k(k),.o(o),.fault(fault));
endmodule
`default_nettype wire
