`timescale 1ns/1ps
// Epoch-only SYSFACE proposal. Accepted pending context is NOT an executing bank.
// publish_slot is an immutable scheduled CTLM bank-load edge, never feedback.
module qfd_mu_embedding_epoch_publication #(parameter ENABLE=0, parameter NU=4)(
 input wire ck,rst_n,
 input wire accepted_v,input wire [1:0] accepted_user,input wire [15:0] accepted_epoch,
 input wire publish_slot,input wire [3:0] publish_mask,
 input wire fetch_slot,input wire [1:0] fetch_user,
 input wire consume_slot,input wire [1:0] consume_user,input wire release_slot,
 input wire retire_slot,input wire [3:0] retire_mask,
 output wire [15:0] fetch_epoch,output wire [15:0] expected_epoch,
 output wire [15:0] core_epoch,output reg fault
);
 localparam [3:0] USERS=4'((1<<NU)-1);
 initial if(NU<1 || NU>4)$fatal(1,"NU must be 1..4");
 integer u;
 reg [15:0] pending[0:3],active[0:3];reg [3:0] pending_valid,active_valid;
 reg [15:0] resident_epoch;reg [1:0] resident_user;reg reserved,consumed;
 assign fetch_epoch=active[fetch_user];assign core_epoch=active[consume_user];assign expected_epoch=resident_epoch;
 always @(posedge ck or negedge rst_n)
  if(!rst_n)begin pending_valid<=0;active_valid<=0;resident_epoch<=0;resident_user<=0;reserved<=0;consumed<=0;fault<=0;end
  else if(ENABLE)begin
   if(accepted_v)begin
    if(accepted_user>=NU || pending_valid[accepted_user] || accepted_epoch[1:0]!=accepted_user || (publish_slot&&publish_mask[accepted_user]))fault<=1;
    pending[accepted_user]<=accepted_epoch;pending_valid[accepted_user]<=1;
   end
   if(publish_slot)begin
    if(publish_mask==0 || (publish_mask & ~USERS)!=0)fault<=1;
    for(u=0;u<NU;u=u+1)if(publish_mask[u])begin
     if(!pending_valid[u] || (reserved&&resident_user==u) || (fetch_slot&&fetch_user==u) || (consume_slot&&consume_user==u) || (retire_slot&&retire_mask[u]))fault<=1;
     active[u]<=pending[u];active_valid[u]<=1;pending_valid[u]<=0;
    end
   end
   if(fetch_slot)begin
    if(fetch_user>=NU || reserved || !active_valid[fetch_user] || consume_slot || release_slot)fault<=1;
    resident_epoch<=active[fetch_user];resident_user<=fetch_user;reserved<=1;consumed<=0;
   end
   if(consume_slot)begin
    if(consume_user>=NU || !reserved || consumed || consume_user!=resident_user || !active_valid[consume_user] || active[consume_user]!=resident_epoch || release_slot)fault<=1;
    consumed<=1;
   end
   if(retire_slot)begin
    if(retire_mask==0 || (retire_mask & ~USERS)!=0)fault<=1;
    for(u=0;u<NU;u=u+1)if(retire_mask[u])begin
     if((reserved&&resident_user==u) || (publish_slot&&publish_mask[u]) || (accepted_v&&accepted_user==u) || (fetch_slot&&fetch_user==u) || (consume_slot&&consume_user==u))fault<=1;
     active_valid[u]<=0;pending_valid[u]<=0;
    end
   end
   if(release_slot)begin
    if(!reserved || !consumed || fetch_slot || consume_slot)fault<=1;
    reserved<=0;consumed<=0;
   end
  end
endmodule
