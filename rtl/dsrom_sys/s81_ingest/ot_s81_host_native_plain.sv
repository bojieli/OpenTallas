`timescale 1ns/1ps
// Reviewed native host: original format engine plus physical completion fence.
// Ordinary FIFO flops have no ECC/parity/mirrors. Source ACKs must retire in
// accepted order; later writes must not satisfy an earlier cumulative cutoff.
module ot_s81_host_native_plain #(
 parameter integer ENABLE=0,FENCE=1,AW=32,HDMAX=16,KVHMAX=1,QKV_EN=0,RMW_EN=0,HFA=4,OCRED=8,MUT=0
)(input wire rst_n,clk_h,h_v,input wire[1:0] h_cls,input wire[511:0]h_d,
 output wire[HFA:0]h_crn,output wire t_v,output wire[63:0]t_d,input wire t_cr,
 input wire clk_i,ck,output wire o_v,o_we,output wire[AW-1:0]o_addr,output wire[255:0]o_d,
 input wire o_cr,i_rv,input wire[255:0]i_rd,input wire[7:0]host_ack_n,output wire fault);
 wire uv,uc,uf,ff;wire[63:0]ud;wire[31:0]landed;
 ot_rom_host_ingest #(.AW(AW),.HDMAX(HDMAX),.KVHMAX(KVHMAX),.QKV_EN(QKV_EN),.RMW_EN(RMW_EN),.HFA(HFA),.OCRED(OCRED),.MUT(MUT)) host(
 .rst_n(rst_n),.clk_h(clk_h),.h_v(h_v&&ENABLE),.h_cls(h_cls),.h_d(h_d),.h_crn(h_crn),.t_v(uv),.t_d(ud),.t_cr(uc),
 .clk_i(clk_i),.ck(ck),.o_v(o_v),.o_we(o_we),.o_addr(o_addr),.o_d(o_d),.o_cr(o_cr),.i_rv(i_rv),.i_rd(i_rd),.fault(uf));
 generate if(FENCE)begin:gf
  ot_s81_ingest_visibility_fence_plain #(.ENABLE(ENABLE)) fence(rst_n,ck,clk_h,host_ack_n,uv,ud,uc,t_v,t_d,t_cr,ff,landed);
 end else begin:mutant_no_fence
  assign t_v=uv;assign t_d=ud;assign uc=t_cr;assign ff=0;assign landed=0;
 end endgenerate
 assign fault=uf|ff;
endmodule
