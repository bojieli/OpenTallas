`timescale 1ns/1ps
// Native S81 host ABI. Sector outputs are the real unchanged dsfd_host die
// face, with its three-domain FIFO crossings. This default-off successor holds
// fenced completions until TRUE source-owned host-sector physical write ACKs.
// i_rv/i_rd remain present; dsfd_host has RMW_EN0 and rejects read descriptors.
module dsfd_host_native #(parameter integer ENABLE=0)(
 input wire rst_n,clk_h,h_v,input wire[1:0] h_cls,input wire[511:0] h_d,
 output wire[4:0] h_crn,output wire t_v,output wire[63:0] t_d,input wire t_cr,
 input wire clk_i,ck,output wire o_v,o_we,output wire[31:0] o_addr,output wire[255:0] o_d,
 input wire o_cr,i_rv,input wire[255:0] i_rd,input wire[7:0] host_ack_n,
 output wire fault
);
 wire uv,uc,uf,ff;wire[63:0] ud;wire[31:0] landed;
 dsfd_host host(.rst_n(rst_n),.clk_h(clk_h),.h_v(h_v&&ENABLE),.h_cls(h_cls),.h_d(h_d),.h_crn(h_crn),
  .t_v(uv),.t_d(ud),.t_cr(uc),.clk_i(clk_i),.ck(ck),.o_v(o_v),.o_we(o_we),.o_addr(o_addr),.o_d(o_d),.o_cr(o_cr),.i_rv(i_rv),.i_rd(i_rd),.fault(uf));
 ot_s81_ingest_visibility_fence #(.ENABLE(ENABLE)) fence(.rst_n(rst_n),.ck(ck),.clk_h(clk_h),.ack_n(host_ack_n),
  .in_v(uv),.in_d(ud),.in_cr(uc),.out_v(t_v),.out_d(t_d),.out_cr(t_cr),.fault(ff),.landed_debug(landed));
 assign fault=uf|ff;
endmodule
