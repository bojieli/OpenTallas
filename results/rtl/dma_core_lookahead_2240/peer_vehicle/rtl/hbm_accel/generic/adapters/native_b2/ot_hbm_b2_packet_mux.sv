`timescale 1ns/1ps
`default_nettype none
// SPEC results/arch/hbm_native_1013/adapters/SPEC.md. One actual hub client,
// four in-order credits. Issuer IDs are stored locally, never in transport tags.
module ot_hbm_b2_packet_mux #(
 parameter integer K=2, parameter integer MUT=0
)(
 input wire clk,rst_n,
 input wire [K-1:0] req_v, output reg [K-1:0] req_r,
 input wire [K*337-1:0] req,
 output reg [K-1:0] rsp_v, output reg [K*273-1:0] rsp,
 output reg [337:0] cq, input wire [273:0] cr,
 output reg fault, output wire drained
);
 localparam integer IW=$clog2(K>1?K:2);
 reg [IW-1:0] owner[0:3]; reg [15:0] tag[0:3]; reg echo[0:3];
 reg [1:0] head,tail; reg [2:0] count; reg [IW-1:0] rr;
 integer pick,j,idx; reg found;
 wire bad_rsp=cr[273]&&(count==0||cr[272:257]!=tag[head]||cr[256]!=echo[head]);
 wire pop=cr[273]&&count!=0&&!bad_rsp&&!fault;
 wire push=found&&!fault;
 assign drained=count==0&&!cq[337];
 always @*begin
  req_r='0;pick=0;found=0;
  if(!fault&&!bad_rsp&&count<4)begin
   for(j=0;j<K;j=j+1)begin
    idx=(integer'(rr)+j)%K;
    if(!found&&req_v[idx])begin pick=idx;found=1;end
   end
   if(found)req_r[pick]=1;
  end
 end
 always @(posedge clk)begin
  if(push) cq[336:0]<=req[pick*337+:337];
  if(pop) rsp[(MUT==1?(integer'(owner[head])+1)%K:integer'(owner[head]))*273+:273]<=cr[272:0];
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin head<=0;tail<=0;count<=0;rr<=0;cq[337]<=0;rsp_v<=0;fault<=0;end
  else begin
   cq[337]<=push;rsp_v<=0;
   if(bad_rsp)fault<=1;
   case({push,pop})
    2'b10:count<=count+1'b1;
    2'b01:count<=count-1'b1;
    default:begin end
   endcase
   if(push)begin
    owner[tail]<=IW'(pick);tag[tail]<=req[pick*337+:16];echo[tail]<=req[pick*337+336];
    tail<=tail+1'b1;rr<=IW'((pick+1)%K);
   end
   if(pop)begin
    rsp_v[MUT==1?(integer'(owner[head])+1)%K:integer'(owner[head])]<=1;
    head<=head+1'b1;
   end
  end
 end
 initial if(K<1)$fatal(1,"K must be positive");
endmodule
`default_nettype wire
