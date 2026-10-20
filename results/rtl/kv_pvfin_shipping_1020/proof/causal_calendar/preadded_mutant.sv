`timescale 1ns/1ps
// Unsummed comparisons select pre-added16-bit candidates. This is exactly
// max(original P0,P1,R)+C modulo16, including overflow and original ties.
// Independent constant adders stop resource sharing from rebuilding the
// high-fanout max-word mux ahead of the carry chain.
module ot_qkd_pvfin_calendar_value #(parameter integer C=9,IGNORE_R=0)(
 input wire [15:0] p0,p1,r,output wire [15:0] y);
 wire [15:0] a0,a1,ar;
 (* keep_hierarchy="yes" *) ot_qkd_pvfin_calendar_plus #(.C(C)) u0(.a(p0),.y(a0));
 (* keep_hierarchy="yes" *) ot_qkd_pvfin_calendar_plus #(.C(C)) u1(.a(p1),.y(a1));
 (* keep_hierarchy="yes" *) ot_qkd_pvfin_calendar_plus #(.C(C)) ur(.a(r),.y(ar));
 (* keep="true" *) wire c0=(a0>a1)&&((IGNORE_R!=0)||(a0>ar));
 (* keep="true" *) wire c1=(a0<=a1)&&((IGNORE_R!=0)||(a1>ar));
 (* keep="true" *) wire cr=!(c0||c1);
 assign y=(a0&{16{c0}})|(a1&{16{c1}})|(ar&{16{cr}});
endmodule
module ot_qkd_pvfin_calendar_plus #(parameter integer C=9)(input wire [15:0] a,output wire [15:0] y);
 assign y=a+16'(C);
endmodule
