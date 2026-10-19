`timescale 1ns/1ps
`default_nettype none
module ot_hgi_coll_ctl_v5_core_safephys #(parameter integer NPT=3,SOLO=1,ND=NPT+13,VM_RT=74,SAFE_DELAY=1)(
 input wire clk_control,rst_n,input wire [1535:0] inst,input wire [31:0] tap_iteration,input wire [87:0] tap_steps,
 input wire hgi_start,hgi_busy,issue_done,tkm_done,tkm_busy,input wire [ND-1:0] dest_v,
 input wire rc_v,input wire [2:0] rc_tag,input wire [7:0] vm_rv,
 output wire [135:0] vm_req_pin,output wire [1:0] inj_req_pin,output wire [31:0] inj_idx_pin,
 output wire [159:0] inj_addr_pin,delivery_obase_pin,rgx_addr_pin,
 output wire [1:0] inj_source_v,output wire [65:0] inj_source_meta,output wire [131:0] vm_source_meta,
 output wire [3:0] vm_assembled_v,output wire [NPT*8-1:0] held_epoch,
 output wire [NPT*16-1:0] wr_sequence_pin,rd_sequence_pin,rx_sequence_pin,
 output wire protocol_fault,output wire [31:0] cycles,output wire [23:0] vm_sel_d);
 wire [15:0] m_idx,m_vm,m_iaddr_h,m_del_h,m_rgx_h;wire [31:0] m_iaddr_l,m_del_l,m_rgx_l;wire [23:0] m_lk_l,m_lk_h;
 ot_hgi_coll_iter_mul_safephys u_mul(.clk(clk_control),.iteration(tap_iteration),.s_idx(tap_steps[0+:16]),
  .s_vm(tap_steps[16+:16]),.s_iaddr(tap_steps[32+:16]),.s_del(tap_steps[48+:16]),.s_rgx(tap_steps[64+:16]),
  .s_lk(tap_steps[80+:8]),.m_idx(m_idx),.m_vm(m_vm),.m_iaddr_l(m_iaddr_l),.m_del_l(m_del_l),.m_rgx_l(m_rgx_l),
  .m_iaddr_h(m_iaddr_h),.m_del_h(m_del_h),.m_rgx_h(m_rgx_h),.m_lk_l(m_lk_l),.m_lk_h(m_lk_h));
 // V6: inst / hgi_start / hgi_busy arrive at the issuer's d2 edge and are captured at the pin (= the d3 edge the
 // other children see); products from ot_hgi_coll_iter_mul_safephys land on the same edge.
 reg [1535:0] inst_q;reg hs_q,hb_q;
 // V7: rst_n loads only the D1 reset flops (async assert, synchronous release one edge later).
 // LH-SMATT 10-19 (SAFE item 1/3; was ONE rst_l driving 155/164 loads): nine KEPT identical D1 copies, each in its own
 // keep_hierarchy instance so synthesis cannot merge them; u_rst8 resets hs_q/hb_q, rst_v[k] the leaf groups.
 wire [7:0] rst_v;wire rst_l;
 for(genvar r=0;r<8;r=r+1)begin:g_rst
  (* keep_hierarchy="yes", dont_touch="yes" *) ot_hgi_coll_rst_copy_safephys u_rst(.clk(clk_control),.rst_n(rst_n),.q(rst_v[r]));
 end
 (* keep_hierarchy="yes", dont_touch="yes" *) ot_hgi_coll_rst_copy_safephys u_rst8(.clk(clk_control),.rst_n(rst_n),.q(rst_l));
 always @(posedge clk_control) inst_q<=inst;
 always @(posedge clk_control or negedge rst_l) if(!rst_l)begin hs_q<=0;hb_q<=0;end else begin hs_q<=hgi_start;hb_q<=hgi_busy;end
 ot_hgi_coll_q_static_ctl_v5_safephys #(.NPT(NPT),.SOLO(SOLO),.INJLAT(12),.VM_RT(VM_RT),.SAFE_DELAY(SAFE_DELAY)) u(.clk_control(clk_control),.rst_v(rst_v),
  .inst(inst_q),.m_idx(m_idx),.m_vm(m_vm),.m_iaddr_l(m_iaddr_l),.m_del_l(m_del_l),.m_rgx_l(m_rgx_l),
  .m_iaddr_h(m_iaddr_h),.m_del_h(m_del_h),.m_rgx_h(m_rgx_h),.m_lk_l(m_lk_l),.m_lk_h(m_lk_h),
  .hgi_start(hs_q),.hgi_busy(hb_q),.issue_done(issue_done),.tkm_done(tkm_done),.tkm_busy(tkm_busy),
  .dest_v(dest_v),.rc_v(rc_v),.rc_tag(rc_tag),.vm_rv(vm_rv),.vm_req_pin(vm_req_pin),.inj_req_pin(inj_req_pin),
  .inj_idx_pin(inj_idx_pin),.inj_addr_pin(inj_addr_pin),.delivery_obase_pin(delivery_obase_pin),
  .rgx_addr_pin(rgx_addr_pin),.inj_source_v(inj_source_v),.inj_source_meta(inj_source_meta),
  .vm_source_meta(vm_source_meta),.vm_assembled_v(vm_assembled_v),
  .held_epoch(held_epoch),.wr_sequence_pin(wr_sequence_pin),.rd_sequence_pin(rd_sequence_pin),
  .rx_sequence_pin(rx_sequence_pin),.protocol_fault(protocol_fault),.cycles(cycles),.vm_sel_d(vm_sel_d));
endmodule
module ot_hgi_coll_ctl_v5r_n1s0_safephys #(parameter integer VM_RT=74,SAFE_DELAY=1)(
 input wire clk_control,rst_n,input wire [1535:0] inst,input wire [31:0] tap_iteration,input wire [87:0] tap_steps,
 input wire hgi_start,hgi_busy,issue_done,tkm_done,tkm_busy,input wire [13:0] dest_v,
 input wire rc_v,input wire [2:0] rc_tag,input wire [7:0] vm_rv,
 output wire [135:0] vm_req_pin,output wire [1:0] inj_req_pin,output wire [31:0] inj_idx_pin,
 output wire [159:0] inj_addr_pin,delivery_obase_pin,rgx_addr_pin,
 output wire [1:0] inj_source_v,output wire [65:0] inj_source_meta,output wire [131:0] vm_source_meta,
 output wire [3:0] vm_assembled_v,output wire [7:0] held_epoch,
 output wire [15:0] wr_sequence_pin,rd_sequence_pin,rx_sequence_pin,
 output wire protocol_fault,output wire [31:0] cycles,output wire [23:0] vm_sel_d);
 ot_hgi_coll_ctl_v5_core_safephys #(.NPT(1),.SOLO(0),.VM_RT(VM_RT),.SAFE_DELAY(SAFE_DELAY)) u(.*);
endmodule
module ot_hgi_coll_ctl_v5r_n2s1_safephys #(parameter integer VM_RT=74,SAFE_DELAY=1)(
 input wire clk_control,rst_n,input wire [1535:0] inst,input wire [31:0] tap_iteration,input wire [87:0] tap_steps,
 input wire hgi_start,hgi_busy,issue_done,tkm_done,tkm_busy,input wire [14:0] dest_v,
 input wire rc_v,input wire [2:0] rc_tag,input wire [7:0] vm_rv,
 output wire [135:0] vm_req_pin,output wire [1:0] inj_req_pin,output wire [31:0] inj_idx_pin,
 output wire [159:0] inj_addr_pin,delivery_obase_pin,rgx_addr_pin,
 output wire [1:0] inj_source_v,output wire [65:0] inj_source_meta,output wire [131:0] vm_source_meta,
 output wire [3:0] vm_assembled_v,output wire [15:0] held_epoch,
 output wire [31:0] wr_sequence_pin,rd_sequence_pin,rx_sequence_pin,
 output wire protocol_fault,output wire [31:0] cycles,output wire [23:0] vm_sel_d);
 ot_hgi_coll_ctl_v5_core_safephys #(.NPT(2),.SOLO(1),.VM_RT(VM_RT),.SAFE_DELAY(SAFE_DELAY)) u(.*);
endmodule
(* keep_hierarchy="yes" *)
module ot_hgi_coll_rst_copy_safephys(input wire clk,rst_n,output reg q);
 always @(posedge clk or negedge rst_n) if(!rst_n)q<=1'b0;else q<=1'b1;
endmodule
`default_nettype wire
