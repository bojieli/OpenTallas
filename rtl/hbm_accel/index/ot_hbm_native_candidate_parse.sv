`timescale 1ps/1fs
`default_nettype none
// Actual15-slot TU decoder. Invalid/padding slots remain explicit lv0 records;
// quarter completion is emitted only with acceptance of the final literal slot.
module ot_hbm_native_candidate_parse #(parameter integer ENABLE=0)(
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
 wire allowed=ENABLE&&owner_valid&&!owner_fault&&!sticky_fault;
 wire valid_header=flit_owner==owner_frame&&flit[544]==expected_kind&&
   flit[543:536]==expected_dst&&flit[535:528]<96&&!flit[510];
 assign flit_r=allowed&&!busy;
 assign tuple_v=allowed&&busy&&held_owner==owner_frame;
 assign tuple=held[34*slot+:34];assign tuple_src=held[535:528];
 assign tuple_index=held[527:512];assign tuple_slot=slot;
 assign quarter_last=held[511]&&slot==14;
 assign tuple_owner=held_owner;assign drained=ENABLE&&!busy;
 assign fault=ENABLE&&(sticky_fault||owner_fault);
 always @(posedge clk or negedge por_n)begin
  if(!por_n)begin busy<=0;sticky_fault<=0;held<=0;held_owner<=0;slot<=0;end
  else if(ENABLE)begin
   if(owner_fault||(busy&&(!owner_valid||held_owner!=owner_frame)))sticky_fault<=1;
   if(flit_v&&flit_r)begin
    if(!valid_header)sticky_fault<=1;
    else begin held<=flit;held_owner<=flit_owner;slot<=0;busy<=1;end
   end
   if(tuple_v&&tuple_r)begin if(slot==14)busy<=0;else slot<=slot+1'b1;end
  end
 end
endmodule
`default_nettype wire
