module projection_miter(input wire clk,rst_n,input wire [135:0] obs136,
 input wire q_v,input wire[7:0]q_idx,input wire[31:0]q_d,output wire mismatch);
 wire[143:0]gold_obs={obs136[135:49], 2'b00, obs136[48:38], 2'b00, obs136[37:27], 2'b00, obs136[26:16], 2'b00, obs136[15:0]};
 wire[586:0]gs,cs;wire gv,cv;wire[7:0]gi,ci;wire[31:0]gd,cd;
 obs_gold_view #(.N(144),.LID(0),.SYNC_MASK(512'd0),.MUT(0)) g(
 .clk(clk),.rst_n(rst_n),.obs(gold_obs),.q_v(q_v),.q_idx(q_idx),.q_d(q_d),
 .r_v(gv),.r_idx(gi),.r_d(gd),.proof_state(gs));
 obs_candidate_view #(.LID(0),.SYNC_MASK(512'd0)) c(
 .clk(clk),.rst_n(rst_n),.obs(obs136),.q_v(q_v),.q_idx(q_idx),.q_d(q_d),
 .r_v(cv),.r_idx(ci),.r_d(cd),.proof_state(cs));
 // Only proof monitors initialize. DUT state is universally unconstrained.
 reg[2:0] reset_edges=0;reg qualified=0;
 always @(posedge clk)if(!qualified)begin
  if(!rst_n)begin if(reset_edges==3)qualified<=1;else reset_edges<=reset_edges+1'b1;end
  else reset_edges<=0;
 end
 assign mismatch=qualified && (gs!=cs || {gv,gi,gd}!={cv,ci,cd});
endmodule
