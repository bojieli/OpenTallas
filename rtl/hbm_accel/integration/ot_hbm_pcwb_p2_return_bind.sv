`timescale 1ps/1fs
`default_nettype none
// Sole-calendar export, default OFF. NO calendar, row grant, FIFO or SRAM.
// The PHY contract is ordered, untagged returns PER PC. Ordinals are minted
// only on actual READ acceptance and returned for the oldest accepted READ.
// Model-before-RTL: hbm_pcwb_p2_return_binding_model; 2448 codedFF at NP32.
module ot_hbm_pcwb_p2_return_bind #(parameter ENABLE=0,NP=32)(
 input wire clk,por_n,bind_v,input wire [72:0] bind_frame,
 input wire [NP-1:0] issue_v,return_v,input wire [NP*3-1:0] freed,
 output wire [NP-1:0] issue_permit,return_permit,
 output wire [NP*16-1:0] next_ordinal,return_ordinal,
 output wire [NP*73-1:0] return_frame,
 output wire [NP-1:0] empty,output wire drained,fault
);
 generate if(!ENABLE)begin:off
 assign issue_permit=0;assign return_permit=0;assign next_ordinal=0;
 assign return_ordinal=0;assign return_frame=0;assign empty=0;assign drained=0;assign fault=0;
 end else begin:on
 wire [74:0] owner;reg [74:0] owner_next;wire owner_good,owner_ce,owner_due;
 wire [NP-1:0] pc_fault;
 wire valid=owner[73];assign drained=(&empty)&&owner_good&&!fault;
 assign fault=owner_due||owner[74]||(|pc_fault);
 always @*begin
  owner_next=owner;
  if(bind_v)begin
   if(!drained)owner_next[74]=1;
   else begin owner_next[72:0]=bind_frame;owner_next[73]=1;end
  end
 end
 ot_hbm_accel_gu_metadata #(.WIDTH(75)) frame(
  .clk(clk),.rst_n(por_n),.we(owner_good&&owner_next!=owner),.next_data(owner_next),
  .data(owner),.good(owner_good),.ce(owner_ce),.due(owner_due));
 for(genvar p=0;p<NP;p++)begin:pc
  wire [48:0] q;reg [48:0] n;wire good,ce,due;
  wire [15:0] issued=q[15:0],returned=q[31:16],released=q[47:32];
  wire [15:0] phy_debt=issued-returned,seat_debt=issued-released,land_debt=returned-released;
  wire [2:0] free_count=freed[p*3+:3];
  assign empty[p]=good&&!due&&!q[48]&&seat_debt==0&&phy_debt==0;
  assign pc_fault[p]=due||q[48];
  wire allowed=good&&owner_good&&valid&&!fault&&!bind_v;
  // No return-derived credit: a seat is recovered only by P2 landing rd_freed.
  assign issue_permit[p]=allowed&&seat_debt<32;
  assign return_permit[p]=allowed&&phy_debt!=0;
  assign next_ordinal[p*16+:16]=issued;
  assign return_ordinal[p*16+:16]=returned;
  assign return_frame[p*73+:73]=owner[72:0];
  always @*begin
   n=q;
   if(issue_v[p]&&!issue_permit[p])n[48]=1;
   if(return_v[p]&&!return_permit[p])n[48]=1;
   if(free_count>land_debt||phy_debt>32||seat_debt>32)n[48]=1;
   if(issue_v[p]&&issue_permit[p])n[15:0]=issued+1'b1;
   if(return_v[p]&&return_permit[p])n[31:16]=returned+1'b1;
   n[47:32]=released+16'(free_count);
  end
  ot_hbm_accel_gu_metadata #(.WIDTH(49)) state(
   .clk(clk),.rst_n(por_n),.we(good&&n!=q),.next_data(n),
   .data(q),.good(good),.ce(ce),.due(due));
 end
 end endgenerate
endmodule
`default_nettype wire
