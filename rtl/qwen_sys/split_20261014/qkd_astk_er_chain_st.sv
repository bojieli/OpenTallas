`timescale 1ns/1ps
// Wires-only reference composition. Die expansion replaces qkd_astk_delay by
// source-bound closed relay masters at actual locations; it must account RL.
module qkd_astk_er_chain_st #(parameter integer N=4, RL=3)(
 input wire ck,rst_n,
 input wire [N-1:0] read_v,
 input wire [11*N-1:0] read_addr,
 input wire [7:0] eso_v,
 input wire [127:0] com,
 input wire [511:0] esi,
 output wire [103:0] aso,
 output wire [N-1:0] response_v,
 output wire [11*N-1:0] response_addr,
 output wire [64*N-1:0] response_data,
 output wire fault
);
 wire [12*N-1:0] req[0:7], req_out[0:7];
 wire [76*N:0] rsp[0:7], rsp_out[0:7];
 assign req[0]={read_addr,read_v};
 assign rsp[0]=0;
 assign {fault,response_data,response_addr,response_v}=rsp_out[7];
 for(genvar e=0;e<8;e=e+1) begin:g_owner
  qkd_astk_er_owner_st #(.N(N)) u_owner(.ck(ck),.rst_n(rst_n),.owner_id(3'(e)),
   .read_v(req[e][0+:N]),.read_addr(req[e][N+:11*N]),
   .next_v(req_out[e][0+:N]),.next_addr(req_out[e][N+:11*N]),
   .prev_v(rsp[e][0+:N]),.prev_addr(rsp[e][N+:11*N]),.prev_data(rsp[e][12*N+:64*N]),.prev_fault(rsp[e][76*N]),
   .response_v(rsp_out[e][0+:N]),.response_addr(rsp_out[e][N+:11*N]),.response_data(rsp_out[e][12*N+:64*N]),.fault(rsp_out[e][76*N]),
   .eso_v(eso_v[e]),.com(com[16*e+:16]),.esi(esi[64*e+:64]),.aso(aso[13*e+:13]));
  if(e<7) begin:g_link
   qkd_astk_delay #(.W(12*N),.D(RL),.RESET(1)) u_req(.clk(ck),.rst_n(rst_n),.d(req_out[e]),.q(req[e+1]));
   qkd_astk_delay #(.W(76*N+1),.D(RL),.RESET(1)) u_rsp(.clk(ck),.rst_n(rst_n),.d(rsp_out[e]),.q(rsp[e+1]));
  end
 end
 initial if(RL<1) $fatal(1,"physical chain requires RL>=1");
endmodule
