`timescale 1ns/1ps
// WINDOW-only ordered replay. Four credit slots include issued reads awaiting
// the two-cycle bank reply. No producer writes are permitted during this job.
module ot_chip_v41x_window_stream #(
 parameter integer POS_W=21, USER_W=10
)(input wire clk,rst_n,start_v,output wire start_ready,
 input wire [USER_W-1:0] start_user,input wire [POS_W-1:0] start_first,
 input wire [7:0] start_count,
 output wire req_v,input wire req_ready,output wire [USER_W-1:0] req_user,
 output wire [POS_W-1:0] req_first,output wire [3:0] req_mask,
 input wire rsp_v,input wire [USER_W-1:0] rsp_user,input wire [POS_W-1:0] rsp_first,
 input wire [3:0] rsp_mask,rsp_valid_mask,input wire [16895:0] rsp_rows,
 input wire rsp_fault,output wire kv_v,input wire kv_ready,
 output wire [3:0] kv_m,output reg [16959:0] kv_w,
 output reg done,fault);
 reg busy;
 reg [USER_W-1:0] user;
 reg [POS_W-1:0] first;
 reg [8:0] count;
 reg [6:0] issued,received,consumed,total;
 reg [16895:0] data[0:3];reg [3:0] masks[0:3];
 wire [6:0] reserved=issued-consumed;
 assign start_ready=!busy&&!fault;
 assign req_v=busy&&!fault&&issued<total&&reserved<4;
 assign req_user=user;
 assign req_first=first+POS_W'(issued*4);
 wire [8:0] remaining=count-9'(issued*4);
 assign req_mask=remaining>=4?4'hf:remaining==3?4'h7:remaining==2?4'h3:4'h1;
 assign kv_v=busy&&!fault&&received>consumed;
 assign kv_m=masks[consumed[1:0]];
 always @* begin
  kv_w=0;
  for(integer l=0;l<4;l=l+1)
   for(integer g=0;g<16;g=g+1)
    kv_w[(l*16+g)*265+:265]={1'b0,data[consumed[1:0]][l*4224+4096+g*8+:8],data[consumed[1:0]][l*4224+g*256+:256]};
 end
 always @(posedge clk or negedge rst_n) begin
  if(!rst_n) begin busy<=0;fault<=0;done<=0;issued<=0;received<=0;consumed<=0;total<=0;count<=0;first<=0;user<=0;end
  else begin
   done<=0;
   if(start_v&&start_ready) begin
    if(start_count==0||start_count>128) fault<=1;
    else begin busy<=1;issued<=0;received<=0;consumed<=0;total<=7'((9'(start_count)+9'd3)>>2);count<=9'(start_count);first<=start_first;user<=start_user;end
   end
   if(req_v&&req_ready) issued<=issued+1;
   if(rsp_v) begin
    if(!busy||rsp_fault||received>=issued||received-consumed>=4||rsp_user!=user||rsp_first!=first+POS_W'(received*4)||rsp_mask!=((count-received*4>=4)?4'hf:(count-received*4==3)?4'h7:(count-received*4==2)?4'h3:4'h1)||(rsp_valid_mask&rsp_mask)!=rsp_mask) fault<=1;
    else begin data[received[1:0]]<=rsp_rows;masks[received[1:0]]<=rsp_mask;received<=received+1;end
   end
   if(kv_v&&kv_ready) begin consumed<=consumed+1;if(consumed+1==total)begin busy<=0;done<=1;end end
  end
 end
endmodule
