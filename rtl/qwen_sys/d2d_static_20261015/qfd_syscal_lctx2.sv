`timescale 1ns/1ps
// Same-edge functional adapter to the existing one-hot, local-read calendar.
// Replicated adapter wires are functional aliases, not independent native
// publications. Full mapped fanout qualification remains mandatory.
module qfd_syscal_lctx2 #(parameter integer NE=32, AW=$clog2(NE),G=NE/16,NB=(NE+31)/32)(
 input wire ck,cfg_we,input wire[3+2*G-1:0]rst_n,input wire[AW:0]cfg_addr,input wire[31:0]cfg_data,
 input wire start,start_seg,halt,
 output wire ev_v,output wire[2:0]ev_port,output wire[3:0]ev_kind,output wire[4:0]ev_beat,
 output wire running,fault
);
 ot_qwen_d2d_cal_sysface32 #(.NE(NE)) u_local(
 .ck(ck),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_addr(cfg_addr),
 .cfg_data_k({NB{cfg_data}}),.cfg_seg_k({(3*G+1){cfg_data[AW-1:0]}}),
 .start_k({(6+2*G){start}}),.halt_k({(6+2*G){halt}}),.seg_k({(4+G){start_seg}}),
 .ev_v(ev_v),.ev_port(ev_port),.ev_kind(ev_kind),.ev_beat(ev_beat),.running(running),.fault(fault));
endmodule
