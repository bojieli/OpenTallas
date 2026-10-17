`timescale 1ns/1ps
`default_nettype none
// H-NETLIST/COLL 1045 V5 issue timing (uniform +2 issue latency vs V4): the V4 protocol leaf computed six
// field + iteration*step terms (32x16 multiply + 40b add) from the issuer flops in one 833 ps cycle (gate:
// in->reg -959 ps, 38 levels). V5 moves the multiplies into ot_hgi_coll_iter_mul (pin capture, then registered
// 16-bit partial products) and delays the whole uop stream 2 edges in ot_hgi_coll_issuer_m, so the products and
// the delayed instruction arrive together and ctl_v5 keeps only field+partial adders. Every expression keeps the
// V4 truncation exactly: 16'(it*s)=low16(it[15:0]*s); 40'(it*s) = zext(low32(it*s)) = zext(low32(pl+(ph<<16)));
// link 40'(it)*40'(s8) = pl8+(ph8<<16).
module ot_hgi_coll_iter_mul(
 input wire clk,
 input wire [31:0] iteration,
 input wire [15:0] s_idx,s_vm,s_iaddr,s_del,s_rgx,
 input wire [7:0] s_lk,
 output reg [15:0] m_idx,m_vm,
 output reg [31:0] m_iaddr_l,m_del_l,m_rgx_l,
 output reg [15:0] m_iaddr_h,m_del_h,m_rgx_h,
 output reg [23:0] m_lk_l,m_lk_h
);
 // V5b (H-NETLIST 1315, ctl3 gate reg->reg -181.2 ps: it[3] -> m_rgx_l[30], 16x16 product, 24 levels ~872 ps):
 // the registered stage holds 16x8 partial products only; the combine is folded into ot_hgi_coll_ctl_v5_combine
 // (same edge, in front of the field adders, which now read a pin-captured instruction). Exact V4 truncation:
 //   16'(it_l*a)            = 16'(pa0 + {pa1,8'd0})                     pa0 = 16'(it_l*a[7:0]), pa1 = 8'(it_l*a[15:8])
 //   32'(it_l*b + {16'(it_h*b),16'd0}) = 32'(pl0 + {pl1,8'd0} + {ph0,16'd0} + {ph1,24'd0})
 //                         pl0 = it_l*b[7:0] (24b), pl1 = it_l*b[15:8] (24b), ph0 = 16'(it_h*b[7:0]), ph1 = 8'(it_h*b[15:8])
 // The m_* ports keep their names and edges: m_*_l carries the full 32-bit offset, m_*_h is 0 (ctl_v5 adds it, a no-op).
 // V6c (ctl V6 gate: 16x8 partial stage ~793-817 ps / 22-23 lv, reg->reg -45.6 / -95.7): every product is split into
 // registered 8x8 byte partials (one 8x8 multiplier per stage-2 flop group), combined in stage 3. Exact V4 truncation:
 //   off32 = 32'(it_l*b + {16'(it_h*b),16'd0}) = low32(it*b) = 32'(sum_{i<4,j<2,i+j<4} it_i*b_j << 8(i+j))
 //   16'(it_l*a) = 16'(it_0*a_0 + (it_1*a_0 + it_0*a_1) << 8)
 //   it_l*k = it_0*k + it_1*k << 8 (24b);   it_h*k = it_2*k + it_3*k << 8 (24b)
 reg [31:0] it;reg [15:0] a,v,b,c,d;reg [7:0] k;
 function automatic [7:0] by(input [31:0] x,input integer i);by=x[i*8+:8];endfunction
 reg [15:0] pa[0:2],pv[0:2];                 // 00,10,01
 reg [15:0] pb[0:6],pc[0:6],pd[0:6];         // (i,j): 00,10,20,30,01,11,21
 reg [15:0] pk[0:3];                         // it_0..3 * k
 always @(posedge clk)begin
  it<=iteration;a<=s_idx;v<=s_vm;b<=s_iaddr;c<=s_del;d<=s_rgx;k<=s_lk;
  pa[0]<=by(it,0)*by(a,0);pa[1]<=by(it,1)*by(a,0);pa[2]<=by(it,0)*by(a,1);
  pv[0]<=by(it,0)*by(v,0);pv[1]<=by(it,1)*by(v,0);pv[2]<=by(it,0)*by(v,1);
  for(integer i=0;i<4;i=i+1)begin
   pb[i]<=by(it,i)*by(b,0);pc[i]<=by(it,i)*by(c,0);pd[i]<=by(it,i)*by(d,0);pk[i]<=by(it,i)*k;
  end
  for(integer i=0;i<3;i=i+1)begin
   pb[4+i]<=by(it,i)*by(b,1);pc[4+i]<=by(it,i)*by(c,1);pd[4+i]<=by(it,i)*by(d,1);
  end
 end
 function automatic [31:0] off(input [15:0] p0,p1,p2,p3,q0,q1,q2);
  off=32'({16'd0,p0}+{8'd0,p1,8'd0}+{p2,16'd0}+{p3[7:0],24'd0}+{8'd0,q0,8'd0}+{q1,16'd0}+{q2[7:0],24'd0});
 endfunction
 always @(posedge clk)begin
  m_idx<=16'(pa[0]+{pa[1][7:0],8'd0}+{pa[2][7:0],8'd0});
  m_vm<=16'(pv[0]+{pv[1][7:0],8'd0}+{pv[2][7:0],8'd0});
  m_iaddr_l<=off(pb[0],pb[1],pb[2],pb[3],pb[4],pb[5],pb[6]);
  m_del_l<=off(pc[0],pc[1],pc[2],pc[3],pc[4],pc[5],pc[6]);
  m_rgx_l<=off(pd[0],pd[1],pd[2],pd[3],pd[4],pd[5],pd[6]);
  m_iaddr_h<=16'd0;m_del_h<=16'd0;m_rgx_h<=16'd0;
  m_lk_l<=24'({8'd0,pk[0]}+{pk[1],8'd0});m_lk_h<=24'({8'd0,pk[2]}+{pk[3],8'd0});
 end
endmodule

module ot_hgi_coll_q_static_ctl_v5 #(
 parameter integer NPT=3,SOLO=1,INJLAT=12,NS=NPT+8,ND=NPT+13
)(
 input wire clk_control,rst_n,
 input wire [1535:0] inst,
 // registered iteration products from ot_hgi_coll_iter_mul (aligned with inst):
 input wire [15:0] m_idx,m_vm,
 input wire [31:0] m_iaddr_l,m_del_l,m_rgx_l,
 input wire [15:0] m_iaddr_h,m_del_h,m_rgx_h,
 input wire [23:0] m_lk_l,m_lk_h,
 input wire hgi_start,hgi_busy,issue_done,tkm_done,tkm_busy,
 input wire [ND-1:0] dest_v,
 input wire rc_v,input wire [2:0] rc_tag,
 input wire [7:0] vm_rv,                    // V6: VM read valid bits only (data -> ot_hgi_coll_vmasm)
 // V7 (native ctl2 1ae51f9c3 capture 503.6 ps on 44 pins): (a) vm_sel removed -- the assembly leaf takes the pair
 // select from the uop pipe's d3 word (the same register edge as this leaf's inst_q), so no inst bit is pulled to an
 // output face; (b) every OBSERVED protocol input (vm_rv, dest_v, rc_v/rc_tag, tkm_done/tkm_busy, issue_done) is
 // captured at its pin and checked against the matching EXPECTED predicate delayed one edge: the observed-input
 // protocol checks raise protocol_fault one edge later (fault ABI +1, scenario 2), inst-only checks unchanged;
 // (c) rst_n reaches one synchroniser flop (core), never the register array.
 output wire [135:0] vm_req_pin,
 output reg [1:0] inj_req_pin,
 output reg [31:0] inj_idx_pin,
 output reg [159:0] inj_addr_pin,
 output reg [159:0] delivery_obase_pin,rgx_addr_pin,
 output wire [1:0] inj_source_v,
 output wire [65:0] inj_source_meta,
 output wire [131:0] vm_source_meta,
 output reg [3:0] vm_assembled_v,
 output wire [NPT*8-1:0] held_epoch,
 output reg [NPT*16-1:0] wr_sequence_pin,rd_sequence_pin,rx_sequence_pin,
 output reg protocol_fault,
 output reg [31:0] cycles
);
 wire [9:0] p_capture_slot=inst[0 +: 10];
 wire [15:0] p_sink_slot=inst[10 +: 16];
 wire [63:0] p_sink_select=inst[26 +: 64];
 wire [1:0] p_inj_rd=inst[90 +: 2];
 wire [31:0] p_inj_idx=inst[92 +: 32];
 wire [159:0] p_inj_addr=inst[124 +: 160];
 wire [65:0] p_inj_meta=inst[284 +: 66];
 wire [2:0] p_lk_wr_v=inst[350 +: 3];
 wire [17:0] p_lk_wr_slot=inst[353 +: 18];
 wire [2:0] p_lk_rd_v=inst[371 +: 3];
 wire [17:0] p_lk_rd_slot=inst[374 +: 18];
 wire [2:0] p_lk_rx_expect=inst[392 +: 3];
 wire [17:0] p_lk_rx_slot=inst[395 +: 18];
 wire [2:0] p_lk_epoch_begin=inst[413 +: 3];
 wire [7:0] p_lk_epoch=inst[416 +: 8];
 wire [159:0] p_rgx_addr=inst[424 +: 160];
 wire [0:0] p_rgx_vm=inst[584 +: 1];
 wire [4:0] p_vm_ingress_slot=inst[585 +: 5];
 wire [7:0] p_vm_slot_valid=inst[590 +: 8];
 wire [31:0] p_vm_slot_owner=inst[598 +: 32];
 wire [87:0] p_ring=inst[630 +: 88];
 wire [0:0] p_tkm_start=inst[718 +: 1];
 wire [3:0] p_tkm_del_slot=inst[719 +: 4];
 wire [11:0] p_tkm_cfg_n=inst[723 +: 12];
 wire [12:0] p_tkm_cfg_k=inst[735 +: 13];
 wire [12:0] p_tkm_cfg_nout=inst[748 +: 13];
 wire [7:0] p_tkm_cfg_g=inst[761 +: 8];
 wire [7:0] p_tkm_cfg_gbase=inst[769 +: 8];
 wire [15:0] p_tkm_cfg_pf=inst[777 +: 16];
 wire [39:0] p_tkm_cfg_obase=inst[793 +: 40];
 wire [39:0] p_tkm_cfg_rbase=inst[833 +: 40];
 wire [0:0] p_tkm_cfg_has_r=inst[873 +: 1];
 wire [159:0] p_del_obase=inst[874 +: 160];
 wire [135:0] p_vm_rq=inst[1034 +: 136];
 wire [131:0] p_vm_meta=inst[1170 +: 132];
 wire [15:0] p_iter_vm_step=inst[1302 +: 16];
 wire [15:0] p_iter_rgx_step=inst[1318 +: 16];
 wire [15:0] p_iter_inj_idx_step=inst[1334 +: 16];
 wire [15:0] p_iter_del_step=inst[1350 +: 16];
 wire [15:0] p_iter_inj_addr_step=inst[1366 +: 16];
 wire [0:0] p_tkm_done_slot=inst[1382 +: 1];
 wire [7:0] p_iter_link_slot_step=inst[1407 +: 8];
 wire [39:0] link_slot_offset=40'(m_lk_l)+(40'(m_lk_h)<<16);
 wire [39:0] off_iaddr=40'(32'(m_iaddr_l+{m_iaddr_h,16'd0}));
 wire [39:0] off_del=40'(32'(m_del_l+{m_del_h,16'd0}));
 wire [39:0] off_rgx=40'(32'(m_rgx_l+{m_rgx_h,16'd0}));
 wire [23:0] p_vm_pair_select=inst[1383 +: 24];
 wire [29:0] p_lk_wr_seq_high=inst[1415 +: 30];
 wire [29:0] p_lk_rd_seq_high=inst[1445 +: 30];
 wire [29:0] p_lk_rx_seq_high=inst[1475 +: 30];
 wire [30:0] p_ar_low=inst[1505 +: 31];
 wire [54:0] ar={p_ring[81:58],p_ar_low};
 wire [0:0] a_load_v=ar[0 +: 1];
 wire [3:0] a_load_tag=ar[1 +: 4];
 wire [0:0] a_add_read=ar[5 +: 1];
 wire [3:0] a_read_tag=ar[6 +: 4];
 wire [0:0] a_add_issue=ar[10 +: 1];
 wire [0:0] a_pub_read=ar[11 +: 1];
 wire [3:0] a_pub_tag_a=ar[12 +: 4];
 wire [3:0] a_pub_tag_b=ar[16 +: 4];
 wire [0:0] a_pub_bf16=ar[20 +: 1];
 wire [0:0] a_pub_release=ar[21 +: 1];
 wire [0:0] a_pub_issue=ar[22 +: 1];
 wire [7:0] a_pub_src=ar[23 +: 8];
 wire [15:0] a_pub_index=ar[31 +: 16];
 wire [0:0] a_arg_mode=ar[47 +: 1];
 wire [0:0] a_arg_start=ar[48 +: 1];
 wire [0:0] a_arg_flush=ar[49 +: 1];
 wire [0:0] a_arg_publish=ar[50 +: 1];
 wire [3:0] a_arg_in_slot=ar[51 +: 4];
 wire [0:0] r_lp_we=p_ring[0 +: 1];
 wire [2:0] r_lp_tag=p_ring[1 +: 3];
 wire [0:0] r_state_read_add=p_ring[4 +: 1];
 wire [2:0] r_state_add_tag=p_ring[5 +: 3];
 wire [1:0] r_state_add_src=p_ring[8 +: 2];
 wire [0:0] r_state_add_rhs_acc=p_ring[10 +: 1];
 wire [0:0] r_state_read_tx=p_ring[11 +: 1];
 wire [2:0] r_state_tx_tag=p_ring[12 +: 3];
 wire [0:0] r_state_tx_acc=p_ring[15 +: 1];
 wire [0:0] r_state_read_rr=p_ring[16 +: 1];
 wire [2:0] r_state_rr_tag=p_ring[17 +: 3];
 wire [0:0] r_add_v=p_ring[20 +: 1];
 wire [2:0] r_add_tag=p_ring[21 +: 3];
 wire [1:0] r_add_src=p_ring[24 +: 2];
 wire [0:0] r_add_rhs_acc=p_ring[26 +: 1];
 wire [1:0] r_tx_inject=p_ring[27 +: 2];
 wire [1:0] r_tx_forward=p_ring[29 +: 2];
 wire [2:0] r_tx_tag=p_ring[31 +: 3];
 wire [1:0] r_tx_dst=p_ring[34 +: 2];
 wire [0:0] r_tx_result=p_ring[36 +: 1];
 wire [0:0] r_tx_acc=p_ring[37 +: 1];
 wire [1:0] r_rx_slot=p_ring[38 +: 2];
 wire [3:0] r_rx_kind=p_ring[40 +: 4];
 wire [3:0] r_rx_src=p_ring[44 +: 4];
 wire [5:0] r_rx_tag=p_ring[48 +: 6];
 wire [0:0] r_rr_local=p_ring[54 +: 1];
 wire [2:0] r_rr_local_tag=p_ring[55 +: 3];

 reg [1:0] inj_valid_pipe[0:INJLAT-1];
 reg [65:0] inj_meta_pipe[0:INJLAT-1];
 reg [131:0] vm_meta_pipe[0:9];
 reg [23:0] vm_select_pipe[0:8];
 reg [7:0] vm_raw_valid;
 reg [7:0] vm_valid_pipe[0:8];
 // V7 pin captures of observed inputs + one-edge-delayed expected predicates
 reg [ND-1:0] dest_q;reg rc_v_q;reg [2:0] rc_tag_q;reg tkm_done_q,tkm_busy_q,issue_done_q;
 reg [2:0] lk_wr_v_e;reg lp_we_e;reg [2:0] lp_tag_e;reg tkm_done_slot_e,arg_active_e,arg_start_e;
 reg arg_active;
 reg [NPT-1:0] wr_sequence_overflow,rd_sequence_overflow,rx_sequence_overflow;
 reg [127:0] vm_req_sector;
 reg [7:0] vm_req_valid;
 for(genvar bank=0;bank<8;bank=bank+1)assign vm_req_pin[bank*17+:17]={vm_req_valid[bank],vm_req_sector[bank*16+:16]};
 reg [7:0] link_epoch[0:NPT-1];
 // Registered requests and metadata have one real, explicit protocol root.
 // Request launch P ->SU source capture P+INJLAT; VM capture P+10.
 always @(posedge clk_control) begin
  for(integer k=0;k<NPT;k=k+1)begin
   wr_sequence_pin[k*16+:16]<=16'(40'({p_lk_wr_seq_high[k*10+:10],p_lk_wr_slot[k*6+:6]})+link_slot_offset);
   rd_sequence_pin[k*16+:16]<=16'(40'({p_lk_rd_seq_high[k*10+:10],p_lk_rd_slot[k*6+:6]})+link_slot_offset);
   rx_sequence_pin[k*16+:16]<=16'(40'({p_lk_rx_seq_high[k*10+:10],p_lk_rx_slot[k*6+:6]})+link_slot_offset);
  end

  for(integer j=0;j<2;j=j+1)begin
   inj_idx_pin[j*16+:16]<=p_inj_idx[j*16+:16]+m_idx;
   for(integer h=0;h<2;h=h+1)
    inj_addr_pin[j*80+h*40+:40]<=p_inj_addr[j*80+h*40+:40]+off_iaddr;
   inj_meta_pipe[0][j*33+:33]<={p_inj_meta[j*33+16+:17],
     16'(p_inj_meta[j*33+:16]+m_idx)};
  end
  for(integer j=1;j<INJLAT;j=j+1)inj_meta_pipe[j]<=inj_meta_pipe[j-1];
  for(integer j=0;j<4;j=j+1)begin
   delivery_obase_pin[j*40+:40]<=p_del_obase[j*40+:40]+off_del;
   rgx_addr_pin[j*40+:40]<=p_rgx_addr[j*40+:40]+off_rgx;
  end
  vm_meta_pipe[0]<=p_vm_meta;
  for(integer j=1;j<10;j=j+1)vm_meta_pipe[j]<=vm_meta_pipe[j-1];
  vm_select_pipe[0]<=p_vm_pair_select;
  for(integer j=1;j<9;j=j+1)vm_select_pipe[j]<=vm_select_pipe[j-1];
  for(integer b=0;b<8;b=b+1)
   vm_req_sector[b*16+:16]<=p_vm_rq[b*17+:16]+m_vm;
 end
 always @(posedge clk_control or negedge rst_n)begin
  if(!rst_n)begin
   protocol_fault<=0;cycles<=0;arg_active<=0;wr_sequence_overflow<=0;rd_sequence_overflow<=0;rx_sequence_overflow<=0;inj_req_pin<=0;vm_assembled_v<=0;vm_raw_valid<=0;
   for(integer j=0;j<INJLAT;j=j+1)inj_valid_pipe[j]<=0;
   for(integer j=0;j<9;j=j+1)vm_valid_pipe[j]<=0;
   dest_q<=0;rc_v_q<=0;rc_tag_q<=0;tkm_done_q<=0;tkm_busy_q<=0;issue_done_q<=0;
   lk_wr_v_e<=0;lp_we_e<=0;lp_tag_e<=0;tkm_done_slot_e<=0;arg_active_e<=0;arg_start_e<=0;
   for(integer b=0;b<8;b=b+1)vm_req_valid[b]<=0;
   for(integer k=0;k<NPT;k=k+1)link_epoch[k]<=0;
  end else begin
   if(hgi_start)cycles<=0;else if(hgi_busy)cycles<=cycles+1;
   dest_q<=dest_v;rc_v_q<=rc_v;rc_tag_q<=rc_tag;tkm_done_q<=tkm_done;tkm_busy_q<=tkm_busy;issue_done_q<=issue_done;
   lk_wr_v_e<=3'(p_lk_wr_v);lp_we_e<=r_lp_we;lp_tag_e<=r_lp_tag;tkm_done_slot_e<=p_tkm_done_slot;
   arg_active_e<=arg_active;arg_start_e<=a_arg_start;
   inj_req_pin<=p_inj_rd;
   for(integer b=0;b<8;b=b+1)vm_raw_valid[b]<=vm_rv[b];
   inj_valid_pipe[0]<=p_inj_rd;
   for(integer j=1;j<INJLAT;j=j+1)inj_valid_pipe[j]<=inj_valid_pipe[j-1];
   for(integer b=0;b<8;b=b+1)begin
    vm_req_valid[b]<=p_vm_rq[b*17+16];
    vm_valid_pipe[0][b]<=p_vm_rq[b*17+16];
`ifdef OT_COLL_V7_MUT_OBS_NOALIGN
    if(vm_raw_valid[b]!=vm_valid_pipe[7][b])protocol_fault<=1;   // mutant: observed captured, expected not delayed
`else
    if(vm_raw_valid[b]!=vm_valid_pipe[8][b])protocol_fault<=1;
`endif
   end
   for(integer j=1;j<9;j=j+1)vm_valid_pipe[j]<=vm_valid_pipe[j-1];
   for(integer j=0;j<4;j=j+1)begin
    vm_assembled_v[j]<=vm_raw_valid[vm_select_pipe[8][j*6+:3]] &&
                        vm_raw_valid[vm_select_pipe[8][j*6+3+:3]] &&
                        vm_select_pipe[8][j*6+:3]!=vm_select_pipe[8][j*6+3+:3];
    if(vm_select_pipe[8][j*6+:3]!=vm_select_pipe[8][j*6+3+:3] &&
       vm_raw_valid[vm_select_pipe[8][j*6+:3]] !=
       vm_raw_valid[vm_select_pipe[8][j*6+3+:3]])protocol_fault<=1;

   end
   for(integer k=0;k<NPT;k=k+1)begin
    if(p_lk_epoch_begin[k])link_epoch[k]<=p_lk_epoch;
    if(dest_q[k]!=lk_wr_v_e[k])protocol_fault<=1;
    wr_sequence_overflow[k]<=(40'({p_lk_wr_seq_high[k*10+:10],p_lk_wr_slot[k*6+:6]})+link_slot_offset)>=65536;
    rd_sequence_overflow[k]<=(40'({p_lk_rd_seq_high[k*10+:10],p_lk_rd_slot[k*6+:6]})+link_slot_offset)>=65536;
    rx_sequence_overflow[k]<=(40'({p_lk_rx_seq_high[k*10+:10],p_lk_rx_slot[k*6+:6]})+link_slot_offset)>=65536;
    if((p_lk_wr_v[k] && wr_sequence_overflow[k]) ||
       (p_lk_rd_v[k] && rd_sequence_overflow[k]) ||
       (p_lk_rx_expect[k] && rx_sequence_overflow[k]))protocol_fault<=1;
   end
`ifndef OT_COLL_V7_MUT_RCDROP
   if(rc_v_q!=lp_we_e || (rc_v_q && rc_tag_q!=lp_tag_e))protocol_fault<=1;
`endif
   if(tkm_done_q!=tkm_done_slot_e || (issue_done_q && (tkm_busy_q || arg_active_e)) || (arg_start_e && tkm_busy_q))
    protocol_fault<=1;
   if(a_arg_start)arg_active<=1'b1;
   if(a_arg_publish)arg_active<=1'b0;
   if((a_arg_start && (!a_arg_mode || p_tkm_start)) ||
      (a_arg_mode && (p_tkm_start || (|p_tkm_del_slot) || p_tkm_done_slot)) || (p_tkm_start && arg_active) ||
      (!a_arg_mode && (a_arg_flush || a_arg_publish || (|a_arg_in_slot))))protocol_fault<=1;
   if(SOLO==0 && (a_arg_mode || a_arg_start || a_arg_flush || a_arg_publish ||
      (|a_arg_in_slot) || p_ring[82]))protocol_fault<=1;
   if(SOLO==0 && (p_tkm_start || (|p_tkm_del_slot)))protocol_fault<=1;
   if(SOLO==0 && (|dest_q[NPT+8+:4]))protocol_fault<=1;
   if(|p_ring[87:84])protocol_fault<=1;
   if(NPT==2 && (p_capture_slot[9] || p_sink_slot[15] || |p_sink_select[63:60] ||
      p_lk_wr_v[2] || p_lk_rd_v[2] || p_lk_rx_expect[2] || p_lk_epoch_begin[2]))protocol_fault<=1;

  end
 end
 assign inj_source_v=inj_valid_pipe[INJLAT-1];
 assign inj_source_meta=inj_meta_pipe[INJLAT-1];
 assign vm_source_meta=vm_meta_pipe[9];
 for(genvar k=0;k<NPT;k=k+1)assign held_epoch[k*8+:8]=link_epoch[k];
endmodule
// V6: VM read-data assembly leaf (moved out of the protocol leaf: 2,048 data bits in and out made that leaf pin-bound,
// 380x280 at util 7%). Same edges as the V5 protocol-leaf code: sel = the protocol leaf's instruction field (flop Q),
// sp[0] = vm_select_pipe[0]; raw = vm_raw_data; assembled 9 edges after the select.
module ot_hgi_coll_vmasm(
 // BIT-INTERLEAVED faces (the parent permutes, wires only): rd_il[i*8+b] = bank b bit i, as_il[i*8+2j+h] = output pair j
 // half h (h 0 = low 256) bit i. A 256-column bit slice holds its 8 inputs, its 8:1 muxes and its 8 outputs, so the
 // pin order along the face keeps every mux local (no 2,048-wire cross-tile shuffle).
 input wire clk,input wire [23:0] sel,input wire [2047:0] rd_il,output reg [2047:0] as_il);
 reg [23:0] sp[0:8];reg [2047:0] raw;
 localparam integer SPX=8;
`ifdef OT_COLL_V6_MUT_VMSEL
 localparam integer HL=3;                     // mutant: the two halves of every pair swapped
`else
 localparam integer HL=0;
`endif
 always @(posedge clk)begin
  sp[0]<=sel;for(integer j=1;j<9;j=j+1)sp[j]<=sp[j-1];
  raw<=rd_il;
  for(integer i=0;i<256;i=i+1)
   for(integer j=0;j<4;j=j+1)begin
    as_il[i*8+2*j]  <=raw[i*8+int'(sp[SPX][j*6+HL+:3])];
    as_il[i*8+2*j+1]<=raw[i*8+int'(sp[SPX][j*6+3-HL+:3])];
   end
 end
endmodule
`default_nettype wire
