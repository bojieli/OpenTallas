`timescale 1ns/1ps
// Isolated MODEL candidate: selected user0 pending prefetch, immutable until INIT.
// No production ABI or absolute schedule is enabled. Base steady ledger d53159bb5.
// publish_slot is an immutable scheduled CTLM bank-load edge, never feedback.
module qfd_mu_embedding_cold_epoch_model #(parameter ENABLE=0, parameter NU=4, parameter COLD_PENDING=0)(
 input wire ck,rst_n,
 input wire epoch_abort,new_epoch,
 input wire accepted_cold_role,input wire [17:0] accepted_token,input wire [1:0] accepted_generation,
 input wire fetch_pending,input wire [17:0] fetch_token,input wire [1:0] fetch_generation,
 input wire init_publication,input wire [17:0] init_token,input wire [1:0] init_generation,
 input wire [17:0] consume_token,
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
 reg [17:0] pending0_token,resident_token;
 reg [1:0] pending0_generation,resident_generation;
 reg pending0_cold_role,reserved_pending,resident_cold;
 wire cold_fetch=(COLD_PENDING!=0)&&fetch_pending;
 wire cold_promote=(COLD_PENDING!=0)&&reserved_pending&&reserved&&!consumed&&
  resident_user==0&&init_publication&&init_token==resident_token&&
  init_generation==resident_generation&&pending0_cold_role&&
  pending[0]==resident_epoch&&pending0_token==resident_token&&
  pending0_generation==resident_generation;
 assign fetch_epoch=cold_fetch?pending[0]:active[fetch_user];assign core_epoch=active[consume_user];assign expected_epoch=resident_epoch;
 always @(posedge ck or negedge rst_n)
  if(!rst_n)begin pending_valid<=0;active_valid<=0;resident_epoch<=0;resident_user<=0;reserved<=0;consumed<=0;fault<=0;pending0_cold_role<=0;reserved_pending<=0;resident_cold<=0;end
  else if(ENABLE)begin
   // Invalidation never clears a sticky identity fault. Payloads remain held.
   if(COLD_PENDING&&(epoch_abort||new_epoch))begin
    pending_valid<=0;active_valid<=0;reserved<=0;consumed<=0;
    pending0_cold_role<=0;reserved_pending<=0;resident_cold<=0;
   end else begin
   if(accepted_v)begin
    if(accepted_user>=NU || pending_valid[accepted_user] || accepted_epoch[1:0]!=accepted_user || (publish_slot&&publish_mask[accepted_user]))fault<=1;
    if(COLD_PENDING)begin
     if(accepted_user==0)begin
      if(!accepted_cold_role || reserved_pending)fault<=1;
      pending0_token<=accepted_token;pending0_generation<=accepted_generation;
      pending0_cold_role<=accepted_cold_role;
     end else if(accepted_cold_role)fault<=1;
    end
    pending[accepted_user]<=accepted_epoch;pending_valid[accepted_user]<=1;
   end
   if(publish_slot)begin
    if((publish_mask & ~USERS)!=0)fault<=1;
    for(u=0;u<NU;u=u+1)if(publish_mask[u])begin
     if(!pending_valid[u] || ((reserved&&resident_user==u)&&!(u==0&&cold_promote)) || (fetch_slot&&fetch_user==u) || (consume_slot&&consume_user==u) || (retire_slot&&retire_mask[u]))fault<=1;
     if(COLD_PENDING&&u==0)begin
      if((reserved_pending||pending0_cold_role)&&!cold_promote)fault<=1;
      if(init_publication&&!cold_promote)fault<=1;
      pending0_cold_role<=0;
      if(cold_promote)reserved_pending<=0;
     end
     active[u]<=pending[u];active_valid[u]<=1;pending_valid[u]<=0;
    end
   end
   if(COLD_PENDING&&init_publication&&(!publish_slot||!publish_mask[0]))fault<=1;
   if(fetch_slot)begin
    if(fetch_user>=NU || reserved || consume_slot || release_slot)fault<=1;
    if(cold_fetch)begin
     if(fetch_user!=0 || !pending_valid[0] || !pending0_cold_role ||
        fetch_token!=pending0_token || fetch_generation!=pending0_generation ||
        (accepted_v&&accepted_user==0) || (publish_slot&&publish_mask[0]))fault<=1;
     resident_epoch<=pending[0];resident_token<=pending0_token;
     resident_generation<=pending0_generation;reserved_pending<=1;resident_cold<=1;
    end else begin
     if(!active_valid[fetch_user])fault<=1;
     resident_epoch<=active[fetch_user];reserved_pending<=0;resident_cold<=0;
    end
    resident_user<=fetch_user;reserved<=1;consumed<=0;
   end
   if(consume_slot)begin
    if(consume_user>=NU || !reserved || consumed || consume_user!=resident_user || !active_valid[consume_user] || active[consume_user]!=resident_epoch || release_slot)fault<=1;
    if(COLD_PENDING&&(reserved_pending ||
       (resident_cold&&resident_token!=consume_token)))fault<=1;
    consumed<=1;
   end
   if(retire_slot)begin
    if((retire_mask & ~USERS)!=0)fault<=1;
    for(u=0;u<NU;u=u+1)if(retire_mask[u])begin
     if((reserved&&resident_user==u) || (publish_slot&&publish_mask[u]) || (accepted_v&&accepted_user==u) || (fetch_slot&&fetch_user==u) || (consume_slot&&consume_user==u))fault<=1;
     active_valid[u]<=0;pending_valid[u]<=0;
    end
   end
   if(release_slot)begin
    if(!reserved || !consumed || fetch_slot || consume_slot)fault<=1;
    reserved<=0;consumed<=0;reserved_pending<=0;resident_cold<=0;
   end
   end
  end
endmodule
