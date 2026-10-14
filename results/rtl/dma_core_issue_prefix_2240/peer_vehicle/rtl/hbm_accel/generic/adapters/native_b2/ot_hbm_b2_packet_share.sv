`timescale 1ns/1ps
`default_nettype none
// Selected xload/publication peers have pulse-only vmq, no ready. Four
// ingress seats per peer retain each request until the shared hub can issue it.
module ot_hbm_b2_packet_share #(parameter integer K=2,parameter integer MUT=0)(
 input wire clk,rst_n,input wire [K*338-1:0] c_cq,
 output wire [K*274-1:0] c_cr,
 output wire [337:0] cq,input wire [273:0] cr,
 output wire fault,output wire drained
);
 reg [336:0] seats[0:K-1][0:3];
 reg [1:0] head[0:K-1],tail[0:K-1];
 reg [2:0] queued[0:K-1],permissions[0:K-1];
 reg sticky;
 wire [K-1:0] iv,ir,ov;wire [K*337-1:0] iq;wire [K*273-1:0] op;
 wire mf,md;wire [K-1:0] empty;
 assign fault=sticky||mf;assign drained=md&&(&empty);
 for(genvar c=0;c<K;c=c+1)begin:client
  wire arrival=c_cq[c*338+337];wire leave=iv[c]&&ir[c];
  wire legal=permissions[c]<4||ov[c];
  assign iv[c]=queued[c]!=0&&!fault;
  assign iq[c*337+:337]=seats[c][head[c]];
  assign c_cr[c*274+:274]={ov[c],op[c*273+:273]};
  assign empty[c]=permissions[c]==0;
  always @(posedge clk)if(arrival&&legal&&!fault)seats[c][tail[c]]<=c_cq[c*338+:337];
  always @(posedge clk or negedge rst_n)begin
   if(!rst_n)begin head[c]<=0;tail[c]<=0;queued[c]<=0;permissions[c]<=0;end
   else if(!fault)begin
    if(arrival&&legal)tail[c]<=tail[c]+1'b1;
    if(leave)head[c]<=head[c]+1'b1;
    case({arrival&&legal,leave})
     2'b10:queued[c]<=queued[c]+1'b1;
     2'b01:queued[c]<=queued[c]-1'b1;
     default:begin end
    endcase
    case({arrival&&legal,ov[c]})
     2'b10:permissions[c]<=permissions[c]+1'b1;
     2'b01:permissions[c]<=permissions[c]-1'b1;
     default:begin end
    endcase
   end
  end
 end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)sticky<=0;
  else for(integer c=0;c<K;c=c+1)
   if((c_cq[c*338+337]&&permissions[c]==4&&!ov[c])||(ov[c]&&permissions[c]==0))sticky<=1;
 end
 ot_hbm_b2_packet_mux #(.K(K),.MUT(MUT)) u_mux(.clk(clk),.rst_n(rst_n),.req_v(iv),.req_r(ir),.req(iq),
  .rsp_v(ov),.rsp(op),.cq(cq),.cr(cr),.fault(mf),.drained(md));
endmodule
`default_nettype wire
