`timescale 1ns/1ps
`default_nettype none
// Native RED_CARRY composition only. The full-SU top connects its actual qcore
// scalar outputs and RF return pins here. Four real cxports cross related 3:4
// clocks; four actual captured-ring engines execute the V4 ring instruction.
// No producer values are synthesized by this adapter. Programme installation,
// links/VM/inject/delivery/SFU and complete token qualification remain outside
// this narrowly named composition.
module ot_hbm_su_collective_red_join(
 input wire clk_s,clk_q,rst_n,
 input wire [3:0] red_sv,
 input wire [127:0] red_tag,red_x,
 input wire [6143:0] collective_uop,
 output wire [3:0] rr_wv,
 output wire [19:0] rr_wa,
 output wire [1023:0] rr_wd,
 output wire [3:0] collective_rr_v,
 output wire [11:0] collective_rr_tag,
 output wire [1023:0] collective_rr_data,
 output wire [11:0] fault
);
 wire [279:0] co[0:3],no[0:3];
 function automatic integer prevq(input integer q);
  case(q)0:prevq=2;1:prevq=0;3:prevq=1;default:prevq=3;endcase
 endfunction
 function automatic integer nextq(input integer q);
  case(q)0:nextq=1;1:nextq=3;3:nextq=2;default:nextq=0;endcase
 endfunction
 for(genvar q=0;q<4;q=q+1)begin:g_q
  wire [87:0] r=collective_uop[1536*q+630+:88];
  wire cv;wire[2:0] ct;wire[255:0] cd;
  ot_hbm_su_static_cxport #(.QID(q),.B39_NOOP(q==0),.INJ_RET(q==0?9:11)) u_cx(
   .clk_s(clk_s),.clk_q(clk_q),.rst_n(rst_n),
   .inj_rd(2'd0),.inj_addr(160'd0),.del_valid(4'd0),.del_flit(2180'd0),.del_obase(160'd0),
   .rc_v(cv),.rc_tag(ct),.rc_d(cd),.rr_v(collective_rr_v[q]),.rr_tag(collective_rr_tag[q*3+:3]),.rr_d(collective_rr_data[q*256+:256]),
   .inj_q(4096'd0),.red_sv(red_sv[q]),.red_tag(red_tag[q*32+:32]),.red_x(red_x[q*32+:32]),
   .rr_wv(rr_wv[q]),.rr_wa(rr_wa[q*5+:5]),.rr_wd(rr_wd[q*256+:256]),
   .ro_v(16'd0),.ro_x(512'd0),.red_sel(12'd0),.fault(fault[q]));
  // Same mandatory fixed-slot agreement as ot_hgi_coll_q_static_ctl_v4.
  reg protocol_fault;
  always @(posedge clk_s or negedge rst_n)
   if(!rst_n)protocol_fault<=0;
   else if(cv!=r[0]||(cv&&ct!=r[3:1]))protocol_fault<=1;
  assign fault[8+q]=protocol_fault;
  ot_hgi_coll_pring_captured_static #(.SPLIT_CLOCKS(1)) u_ring(
   .clk(clk_s),.clk_state({8{clk_s}}),.clk_add({8{clk_s}}),.rst_n(rst_n),.qid(2'(q)),
   .cw_i(co[prevq(q)]),.ccw_i(no[nextq(q)]),.cw_o(co[q]),.ccw_o(no[q]),.lp_data(cd),
   .rr_v(collective_rr_v[q]),.rr_tag(collective_rr_tag[q*3+:3]),.rr_d(collective_rr_data[q*256+:256]),.fault(fault[4+q]),
   .lp_we(r[0+:1]),
   .lp_tag(r[1+:3]),
   .state_read_add(r[4+:1]),
   .state_add_tag(r[5+:3]),
   .state_add_src(r[8+:2]),
   .state_add_rhs_acc(r[10+:1]),
   .state_read_tx(r[11+:1]),
   .state_tx_tag(r[12+:3]),
   .state_tx_acc(r[15+:1]),
   .state_read_rr(r[16+:1]),
   .state_rr_tag(r[17+:3]),
   .add_v(r[20+:1]),
   .add_tag(r[21+:3]),
   .add_src(r[24+:2]),
   .add_rhs_acc(r[26+:1]),
   .tx_inject(r[27+:2]),
   .tx_forward(r[29+:2]),
   .tx_tag(r[31+:3]),
   .tx_dst(r[34+:2]),
   .tx_result(r[36+:1]),
   .tx_acc(r[37+:1]),
   .rx_slot(r[38+:2]),
   .rx_kind(r[40+:4]),
   .rx_src(r[44+:4]),
   .rx_tag(r[48+:6]),
   .rr_local(r[54+:1]),
   .rr_local_tag(r[55+:3]));
 end
endmodule
`default_nettype wire
