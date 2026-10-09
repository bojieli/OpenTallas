`timescale 1ns/1ps
// Native runtime source0 debt fence, BEFORE quadrant/registered svc relay.
// source_req_v is actualaccepted issuance, not arrival at the downstreammux.
// source_done is an owned physicalwd or tag/beat-validatedlastread; rk queue
// credits alone are never completion. source_quiescent MUST be an explicit
// upstream grantrevocation+transportdrain acknowledgment. No tieoff is safe.
module ot_s81_runtime_pc_lease64 #(parameter integer ENABLE=0)(
 input wire clk,rst_n,input wire[63:0] source_req_v,source_done,
 input wire[63:0] source_quiescent,decode_held,
 input wire[63:0] pc_want,pc_claim,pc_release,
 output wire[63:0] source_issue_enable,pc_available,pc_held,
 output wire fault
);
 reg[3:0] debt[0:63],debt_n[0:63];reg[63:0] held,held_n,bad;
 genvar g;
 generate for(g=0;g<64;g=g+1)begin:p
  wire ok=(debt_n[g]==~debt[g])&&(debt[g]<=8)&&(held_n[g]==!held[g]);
  assign source_issue_enable[g]=ENABLE&&!bad[g]&&ok&&!pc_want[g]&&!held[g]&&(debt[g]<8);
  assign pc_available[g]=ENABLE&&!bad[g]&&ok&&pc_want[g]&&!held[g]&&
   (debt[g]==0)&&source_quiescent[g]&&!decode_held[g]&&!source_req_v[g];
  assign pc_held[g]=ENABLE&&!bad[g]&&ok&&held[g];
  wire[3:0] next_debt=debt[g]+source_req_v[g]-source_done[g];
  wire next_held=pc_claim[g]?1'b1:pc_release[g]?1'b0:held[g];
  always @(posedge clk or negedge rst_n)begin
   if(!rst_n)begin debt[g]<=0;debt_n[g]<=4'hf;held[g]<=0;held_n[g]<=1;bad[g]<=0;end
   else if(!bad[g])begin
    if(!ok||(!ENABLE&&(source_req_v[g]||source_done[g]||pc_claim[g]||pc_release[g]))||
       (source_req_v[g]&&((debt[g]>=8&&!source_done[g])||held[g]||source_quiescent[g]))||
       (source_done[g]&&debt[g]==0)||
       (pc_claim[g]&&(!pc_available[g]||pc_release[g]))||
       (pc_release[g]&&!held[g])||(held[g]&&decode_held[g]))bad[g]<=1;
    else begin debt[g]<=next_debt;debt_n[g]<=~next_debt;
     held[g]<=next_held;held_n[g]<=!next_held;end
   end
  end
 end endgenerate
 assign fault=|bad;
endmodule
