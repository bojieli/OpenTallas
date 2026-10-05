`timescale 1ns/1ps
// Finite, registered request queue per actual 128-byte-interleaved partition.
// Original die-global addresses/tags are retained. Backend ACKs are never synthesized.
module ot_hbm_accel_partition_ports #(parameter integer ENABLE=0, NS=2, DEPTH=4, TW=16)(
 input wire clk,rst_n,
 input wire req_v,output wire req_rdy,input wire req_we,input wire[31:0] req_addr,
 input wire[255:0] req_wdata,input wire[31:0] req_wstrb,input wire[TW-1:0] req_tag,
 output wire rsp_v,input wire rsp_rdy,output wire rsp_we,output wire[TW-1:0] rsp_tag,output wire[255:0] rsp_data,
 output wire[NS-1:0] p_req_v,input wire[NS-1:0] p_req_rdy,output wire[NS-1:0] p_req_we,
 output wire[NS*32-1:0] p_req_addr,output wire[NS*256-1:0] p_req_wdata,
 output wire[NS*32-1:0] p_req_wstrb,output wire[NS*TW-1:0] p_req_tag,
 input wire[NS-1:0] p_rsp_v,output wire[NS-1:0] p_rsp_rdy,input wire[NS-1:0] p_rsp_we,
 input wire[NS*TW-1:0] p_rsp_tag,input wire[NS*256-1:0] p_rsp_data);
 generate if(!ENABLE)begin:g_off
 assign req_rdy=0;assign rsp_v=0;assign rsp_we=0;assign rsp_tag='0;assign rsp_data='0;
 assign p_req_v='0;assign p_req_we='0;assign p_req_addr='0;assign p_req_wdata='0;
 assign p_req_wstrb='0;assign p_req_tag='0;assign p_rsp_rdy='0;
 end else begin:g_on
 localparam integer PW=$clog2(DEPTH), LW=(NS>1)?$clog2(NS):1, RW=1+32+256+32+TW;
 initial if(DEPTH<2 || (DEPTH&(DEPTH-1)) || (NS&(NS-1)))$fatal(1,"partition queue geometry");
 wire[LW-1:0] target=LW'((req_addr>>7)&(NS-1));
 wire[NS-1:0] room;
 assign req_rdy=rst_n&&room[target];
 for(genvar p=0;p<NS;p=p+1)begin:g_p
 reg[RW-1:0] q[DEPTH];reg[PW-1:0] wr=0,rd=0;reg[PW:0] count=0;
 wire push=req_v&&req_rdy&&target==LW'(p),pop=p_req_v[p]&&p_req_rdy[p];
 assign room[p]=count<DEPTH;
 assign p_req_v[p]=rst_n&&count!=0;
 assign {p_req_we[p],p_req_addr[p*32+:32],p_req_wdata[p*256+:256],p_req_wstrb[p*32+:32],p_req_tag[p*TW+:TW]}=q[rd];
 always @(posedge clk or negedge rst_n)if(!rst_n)begin wr<=0;rd<=0;count<=0;end else begin
 if(push)begin q[wr]<={req_we,req_addr,req_wdata,req_wstrb,req_tag};wr<=wr+1'b1;end
 if(pop)rd<=rd+1'b1;
 count<=count+push-pop;
 end
 end
 reg[LW-1:0] rr=0,held=0;reg locked=0;
 reg[LW-1:0] pick;reg found;integer k,ix;
 always @*begin
 pick=held;found=locked;
 if(!locked)begin
 pick=rr;found=0;
 for(k=0;k<NS;k=k+1)begin ix=(int'(rr)+k)%NS;if(!found&&p_rsp_v[ix])begin pick=LW'(ix);found=1;end end
 end
 end
 assign rsp_v=rst_n&&found&&p_rsp_v[pick];
 assign rsp_we=p_rsp_we[pick];assign rsp_tag=p_rsp_tag[pick*TW+:TW];assign rsp_data=p_rsp_data[pick*256+:256];
 for(genvar p=0;p<NS;p=p+1)assign p_rsp_rdy[p]=rsp_v&&rsp_rdy&&pick==LW'(p);
 always @(posedge clk or negedge rst_n)if(!rst_n)begin rr<=0;held<=0;locked<=0;end else begin
 if(rsp_v&&!rsp_rdy)begin held<=pick;locked<=1;end
 if(rsp_v&&rsp_rdy)begin locked<=0;rr<=pick==NS-1?LW'(0):pick+1'b1;end
 end
 end endgenerate
endmodule
