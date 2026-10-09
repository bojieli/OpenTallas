`timescale 1ps/1fs
`default_nettype none
// Actual15-slot TU decoder. Invalid/padding slots remain explicit lv0 records;
// quarter completion is emitted only with acceptance of the final literal slot.
// strip-protect 2026-10-09 (REVIEW_20261009 S4/X3): PROTECT=0 (default) removes the rejected flop-level protection;
// PROTECT=1 is the original, bit for bit.  Fault-free behaviour is identical (physical/strip_protect/bench.py).
module ot_hbm_native_candidate_parse #(parameter integer ENABLE=0,PROTECT=0)(
 input wire clk,por_n,input wire owner_valid,owner_fault,
 input wire [72:0] owner_frame,input wire expected_kind,input wire [7:0] expected_dst,
 input wire flit_v,output wire flit_r,input wire [544:0] flit,
 input wire [72:0] flit_owner,
 output wire tuple_v,input wire tuple_r,output wire [33:0] tuple,
 output wire [7:0] tuple_src,output wire [15:0] tuple_index,
 output wire [3:0] tuple_slot,output wire quarter_last,
 output wire [72:0] tuple_owner,output wire drained,output wire fault
);
 reg busy,sticky_fault;reg[544:0]held;reg[72:0]held_owner;reg[3:0]slot;
  reg [0:0] busy_n;
 reg [0:0] sticky_fault_n;
 reg [544:0] held_n;
 reg [72:0] held_owner_n;
 reg [3:0] slot_n;
 wire coded_ok=(PROTECT==0)||((busy_n==~busy)&&(sticky_fault_n==~sticky_fault)&&(held_n==~held)&&(held_owner_n==~held_owner)&&(slot_n==~slot));
 wire allowed=ENABLE&&owner_valid&&!owner_fault&&!sticky_fault&&coded_ok;
 wire valid_header=flit_owner==owner_frame&&flit[544]==expected_kind&&
   flit[543:536]==expected_dst&&flit[535:528]<96&&!flit[510];
 assign flit_r=allowed&&!busy;
 assign tuple_v=allowed&&busy&&held_owner==owner_frame;
 assign tuple=held[34*slot+:34];assign tuple_src=held[535:528];
 assign tuple_index=held[527:512];assign tuple_slot=slot;
 assign quarter_last=held[511]&&slot==14;
 assign tuple_owner=held_owner;assign drained=ENABLE&&!fault&&!busy;
 assign fault=ENABLE&&(sticky_fault||owner_fault||!coded_ok);
 always @(posedge clk or negedge por_n)begin
  if(!por_n)begin begin busy<=0;busy_n<=~(0); end begin sticky_fault<=0;sticky_fault_n<=~(0); end begin held<=0;held_n<=~(0); end begin held_owner<=0;held_owner_n<=~(0); end begin slot<=0;slot_n<=~(0); end end
  else if(ENABLE)begin
   if(!coded_ok||owner_fault||(busy&&(!owner_valid||held_owner!=owner_frame)))begin sticky_fault<=1;sticky_fault_n<=~(1); end 
   if(flit_v&&flit_r)begin
    if(!valid_header)begin sticky_fault<=1;sticky_fault_n<=~(1); end 
    else begin begin held<=flit;held_n<=~(flit); end begin held_owner<=flit_owner;held_owner_n<=~(flit_owner); end begin slot<=0;slot_n<=~(0); end begin busy<=1;busy_n<=~(1); end end
   end
   if(tuple_v&&tuple_r)begin if(slot==14)begin busy<=0;busy_n<=~(0); end else begin slot<=slot+1'b1;slot_n<=~(slot+1'b1); end end
  end
 end
endmodule
`default_nettype wire
