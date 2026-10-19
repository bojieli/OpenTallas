`timescale 1ns/1ps
// Default-off static identity/lifetime contract. This module never delays work.
// Upstream accepted tuple must be from the validated observer, not live host wires.
module qfd_mu_embedding_ledger #(parameter ENABLE=0)(
 input wire ck,rst_n,
 input wire accept_v,input wire [1:0] accept_user,
 input wire [17:0] accept_token,input wire [15:0] accept_epoch,
 input wire fetch_slot,input wire [1:0] fetch_user,
 input wire consume_slot,input wire [1:0] consume_user,
 input wire [17:0] consume_token,input wire [15:0] consume_epoch,
 input wire release_slot,
 output wire fill_begin,output wire [17:0] fill_token,output wire [15:0] fill_epoch,
 output wire [17:0] expected_token,output wire [15:0] expected_epoch,
 output reg fault
);
 reg [3:0] valid;
 reg [17:0] tokens[0:3]; reg [15:0] epochs[0:3];
 reg reserved,consumed; reg [1:0] owner;
 reg [17:0] row_token; reg [15:0] row_epoch;
 assign fill_begin=ENABLE && fetch_slot;
 assign fill_token=tokens[fetch_user]; assign fill_epoch=epochs[fetch_user];
 assign expected_token=row_token; assign expected_epoch=row_epoch;
 // Acceptance and fetch on the same edge is deliberately illegal: the compiler
 // must price publication-to-ledger before fetching, including physical landings.
 always @(posedge ck or negedge rst_n)
  if(!rst_n)begin valid<=0;reserved<=0;consumed<=0;owner<=0;row_token<=0;row_epoch<=0;fault<=0;end
  else if(ENABLE)begin
   if(accept_v)begin
    if(accept_epoch[1:0]!=accept_user || accept_token>=151936)fault<=1;
    valid[accept_user]<=1; tokens[accept_user]<=accept_token; epochs[accept_user]<=accept_epoch;
   end
   if(fetch_slot)begin
    if(reserved || !valid[fetch_user] || (accept_v && accept_user==fetch_user) || consume_slot || release_slot)fault<=1;
    reserved<=1;consumed<=0;owner<=fetch_user;
    row_token<=tokens[fetch_user];row_epoch<=epochs[fetch_user];
   end
   if(consume_slot)begin
    if(!reserved || consumed || consume_user!=owner || consume_token!=row_token || consume_epoch!=row_epoch || fetch_slot || release_slot)fault<=1;
    consumed<=1;
   end
   if(release_slot)begin
    if(!reserved || !consumed || fetch_slot || consume_slot)fault<=1;
    reserved<=0;consumed<=0;
   end
  end
endmodule
