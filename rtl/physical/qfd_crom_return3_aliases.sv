`timescale 1ns/1ps
// Distinct real physical leaf names for two assigned pin-map variants.
// Exact canonical pipeline body; no LEF-only rename or added stage.
module qfd_crom_return3_above #(parameter integer MUT=0)(
 input wire ck,rst_n,input wire[512:0]a,output wire[512:0]b);
 (* keep *) reg reset_q;
 always @(posedge ck or negedge rst_n)
 if(!rst_n)reset_q<=0;else reset_q<=1;
 (* keep *) reg[512:0]p0,p1,p2;
 always @(posedge ck or negedge reset_q)
 if(!reset_q)begin p0<=0;p1<=0;p2<=0;end
 else begin p0<=a;p1<=p0;p2<=p1;end
 assign b=(MUT!=0)?p1:p2;
endmodule

module qfd_crom_return3_below #(parameter integer MUT=0)(
 input wire ck,rst_n,input wire[512:0]a,output wire[512:0]b);
 (* keep *) reg reset_q;
 always @(posedge ck or negedge rst_n)
 if(!rst_n)reset_q<=0;else reset_q<=1;
 (* keep *) reg[512:0]p0,p1,p2;
 always @(posedge ck or negedge reset_q)
 if(!reset_q)begin p0<=0;p1<=0;p2<=0;end
 else begin p0<=a;p1<=p0;p2<=p1;end
 assign b=(MUT!=0)?p1:p2;
endmodule

