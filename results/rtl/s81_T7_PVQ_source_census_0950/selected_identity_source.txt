module dsdv_pv_source_identity #(parameter integer ENABLE=0)(
 input wire clk,rst_n,cfg_v,input wire[19:0]cfg_owner,input wire cfg_valid,
 input wire launch,launch_ok,input wire[9:0]user_id,input wire[7:0]tag_id,
 input wire[1:0]quarter,input wire[3:0]tile,input wire[20:0]position,
 output wire[439:0]provenance,output wire bad
);
 generate if(ENABLE==0)begin:g_disabled assign provenance=440'd0;assign bad=1'b0;end
 else begin:g_enabled
  reg[19:0]pending,owner;reg valid,live;reg[1:0]q;reg[3:0]t;reg[20:0]pos;
  always @(posedge clk or negedge rst_n)if(!rst_n)begin pending<=0;owner<=0;valid<=0;live<=0;q<=0;t<=0;pos<=0;end
  else begin
   if(cfg_v)begin pending<=cfg_owner;valid<=cfg_valid;end
   if(launch)begin owner<=pending;live<=launch_ok && valid && pending[17:0]=={user_id,tag_id};q<=quarter;t<=tile;pos<=position;end
  end
  assign provenance={392'd0,pos,live,t,q,owner};
  assign bad=launch && (!launch_ok || !valid || pending[17:0]!={user_id,tag_id});
 end endgenerate
endmodule
