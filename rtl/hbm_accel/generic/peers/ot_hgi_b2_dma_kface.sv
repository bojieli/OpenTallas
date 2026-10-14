`timescale 1ns/1ps
`default_nettype none
// Independent hard-face clock root. Each accepted request retains all342 payload bits.
// Registered ready stops external backpressure at this two-slot station.
module ot_hgi_b2_dma_kface(
 input wire clk,rst_n,input wire [342:0] request,output reg request_ready,
 output reg k_req_v,input wire k_req_rdy,output wire k_req_we,
 output wire [36:0] k_req_addr,output wire [255:0] k_req_wdata,
 output wire [31:0] k_req_wstrb,output wire [15:0] k_req_tag,
 input wire k_rsp_v,k_rsp_we,input wire [255:0] k_rsp_data,output reg [257:0] response
);
 reg [1:0] reset_release;always @(posedge clk or negedge rst_n)
   if(!rst_n) reset_release<=0;else reset_release<={reset_release[0],1'b1};
 wire rn=reset_release[1];
 reg [1:0] count;reg [341:0] head,tail;
 wire push=request[342]&&request_ready,pop=k_req_v&&k_req_rdy;
 wire [1:0] next_count=count+{1'b0,push}-{1'b0,pop};
 always @(posedge clk or negedge rn) begin
   if(!rn)begin count<=0;request_ready<=0;k_req_v<=0;end
   else begin
     count<=next_count;request_ready<=next_count<2;k_req_v<=next_count!=0;
     case({push,pop})
       2'b10:if(count==0)head<=request[341:0];else tail<=request[341:0];
       2'b01:head<=tail;
       2'b11:if(count==1)head<=request[341:0];else begin head<=tail;tail<=request[341:0];end
       default:begin end
     endcase
   end
 end
 assign {k_req_we,k_req_addr,k_req_wdata,k_req_wstrb,k_req_tag}=head;
 always @(posedge clk or negedge rn)if(!rn)response[257]<=0;else response[257]<=k_rsp_v;
 always @(posedge clk)response[256:0]<={k_rsp_we,k_rsp_data};
endmodule
`default_nettype wire
