`timescale 1ns/1ps
// IDs identify independently kept consumers; registers capture the original
// producer NEXT value at its existing edge. No additional staging is inserted.
(* keep_hierarchy="yes" *)
module ot_s81pa_copy #(parameter integer W=21,ID=0)(input wire clk,input wire[W-1:0]d,output wire[W-1:0]q);
 (* keep *) reg[W-1:0]r;
 always @(posedge clk)r<=d;
 assign q=r;
endmodule

// [ELEM-BKG] kept same-edge copy of a RESET register: same D, same reset value, reset by the consumer's leaf
// (all profile leaves release on the same edge).
(* keep_hierarchy="yes" *)
module ot_s81pa_rcopy #(parameter integer W=3,parameter[W-1:0]INIT=0,parameter integer ID=0)(
 input wire clk,rst_n,input wire[W-1:0]d,output wire[W-1:0]q);
 (* keep *) reg[W-1:0]r;
 always @(posedge clk or negedge rst_n) if(!rst_n)r<=INIT;else r<=d;
 assign q=r;
endmodule

(* keep_hierarchy="yes" *)
module ot_s81pa_prio16 #(parameter integer W=2,ID=0)(
 input wire clk,input wire[15:0]compare_next,input wire[16*W-1:0]data,
 input wire[W-1:0]fallback,output reg[W-1:0]value,output reg[3:0]bin,output wire valid);
 (* keep *)reg[15:0]ge;
 always @(posedge clk)ge<=compare_next;
 wire[15:0]highest;
 generate for(genvar n=0;n<16;n=n+1)begin:g_high
  if(n==15)assign highest[n]=ge[n];
  else assign highest[n]=ge[n]&&!(|ge[15:n+1]);
 end endgenerate
 assign valid=|ge;
 always @*begin
  value=0;bin=0;
  for(integer n=0;n<16;n=n+1)begin
   bin=bin|(4'(n)&{4{highest[n]}});
   if(n==15)value=value|(fallback&{W{highest[n]}});
   else value=value|(data[W*(n+1)+:W]&{W{highest[n]}});
  end
  // Original priority loop defaults bin0 when no compare succeeds; its suffix
  // mux still picks word1. Preserve that behavior, including invalid searches.
  if(!( |ge))value=data[W+:W];
 end
endmodule

(* keep_hierarchy="yes" *)
module ot_s81pa_bin16 #(parameter integer W=2,ID=0)(
 input wire clk,input wire[3:0]selector_next,input wire[16*W-1:0]data,output reg[W-1:0]value);
 (* keep *)reg[3:0]sel;
 always @(posedge clk)sel<=selector_next;
 wire[3:0]lo,hi;
 generate for(genvar n=0;n<4;n=n+1)begin:g_decode
  assign lo[n]=(sel[1:0]==2'(n));
  assign hi[n]=(sel[3:2]==2'(n));
 end endgenerate
 always @*begin
  value=0;
  for(integer n=0;n<16;n=n+1)value=value|(data[W*n+:W]&{W{lo[n%4]&&hi[n/4]}});
 end
endmodule
