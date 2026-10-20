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
 (* keep="true" *) wire c0=(p0>p1)&&((IGNORE_R!=0)||(p0>r));
 (* keep="true" *) wire c1=(p0<=p1)&&((IGNORE_R!=0)||(p1>r));
 (* keep="true" *) wire cr=!(c0||c1);
 assign y=(a0&{16{c0}})|(a1&{16{c1}})|(ar&{16{cr}});
endmodule
module ot_qkd_pvfin_calendar_plus #(parameter integer C=9)(input wire [15:0] a,output wire [15:0] y);
 assign y=a+16'(C);
endmodule
// Calendar acceptance without a wide absolute-value/max-word selection.
// Seventeen-bit distance equality prevents cross-zero wrap acceptance.
module ot_qkd_pvfin_calendar_check #(
 parameter integer SKEW=2,ADD_LAT=7,MUL_LAT=6,IGNORE_R=0)(
 input wire [15:0] p0,p1,r,output wire bad);
 localparam integer MAX_AGE=65535-64-ADD_LAT-MUL_LAT;
 wire [SKEW:0] near0,near1;
 generate for(genvar d=0;d<=SKEW;d=d+1)begin:g_distance
  assign near0[d]=({1'b0,p0}+17'(d))=={1'b0,p1};
  assign near1[d]=({1'b0,p1}+17'(d))=={1'b0,p0};
 end endgenerate
 assign bad=(p0==0)||(p1==0)||(r==0)||!(|(near0|near1))||
  (p0>16'(MAX_AGE))||(p1>16'(MAX_AGE))||((IGNORE_R==0)&&(r>16'(MAX_AGE)));
endmodule
