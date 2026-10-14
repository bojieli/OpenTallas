`timescale 1ns/1ps
`default_nettype none
module ot_hgi_qdq_fr_capture_retire #(parameter integer MUT_ORDER=0) (
 input wire clk,rst_n,accept,accept_one,
 input wire [189:0] fast_payload,
 input wire general_v,input wire [189:0] general_payload,
 output reg s3_v,output reg [189:0] s3,output reg overflow
);
 reg f_rst;always @(posedge clk)f_rst<=rst_n;
 wire[0:0]rr_n;ot_rst_relay #(.REGIONS(1))u_rst(.clk(clk),.rst_n_in(f_rst),.rst_n(rr_n));
 // Every control input first lands in its own FF. Acceptance precedes fast payload
 // by one edge, allowing a direct fourth-edge output without using a raw valid pin.
 reg accept_c,one_c,gv_c;
 reg[189:0]fast_c,general_c;
 always @(posedge clk)begin fast_c<=fast_payload;general_c<=general_payload;one_c<=accept_one;end
 always @(posedge clk or negedge rr_n[0])
  if(!rr_n[0])begin accept_c<=0;gv_c<=0;end
  else begin accept_c<=accept;gv_c<=general_v;end
 reg[3:0]head,tail,tags[0:7];reg[4:0]count;
 reg[15:0]ready,classes;
 reg[189:0]payload[0:15];
 reg fv_c;
 wire direct=accept_c&&one_c&&(count==0||MUT_ORDER!=0);
 wire fh=fv_c&&tags[0]==head;
 wire gv=gv_c&&!classes[tags[7]];
 wire gh=gv&&tags[7]==head;
 wire pop=count!=0&&(ready[head]||fh||gh);
 wire[189:0]head_data=ready[head]?payload[head]:(fh?fast_c:general_c);
 // The only raw fast-data logic is this two-input mux with registered control.
 // Output and capture datapaths have no reset or enable feedback.
 always @(posedge clk)begin
  s3<=direct?fast_payload:head_data;
  if(fv_c&&!fh)payload[tags[0]]<=fast_c;
  if(gv&&!gh)payload[tags[7]]<=general_c;
 end
 integer k;
 always @(posedge clk or negedge rr_n[0])begin
  if(!rr_n[0])begin head<=0;tail<=0;count<=0;ready<=0;classes<=0;s3_v<=0;overflow<=0;fv_c<=0;
   for(k=0;k<8;k=k+1)tags[k]<=0;
  end else begin
   tags[0]<=tail;for(k=1;k<8;k=k+1)tags[k]<=tags[k-1];
   fv_c<=accept_c&&one_c&&!direct;
   s3_v<=direct||pop;
   if(pop||direct)begin head<=head+4'd1;ready[head]<=0;end
   if(fv_c&&!fh)ready[tags[0]]<=1;
   if(gv&&!gh)ready[tags[7]]<=1;
   if(accept_c)begin tail<=tail+4'd1;classes[tail]<=one_c;if(count==16&&!pop)overflow<=1;end
   case({accept_c&&!direct,pop})
    2'b10:count<=count+5'd1;
    2'b01:count<=count-5'd1;
    default:count<=count;
   endcase
  end
 end
endmodule
`default_nettype wire
