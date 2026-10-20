`timescale 1ns/1ps
`default_nettype none
// HBM-ELEMOWN3/COLLQ3 (10-19): hardening leaves for the SAFE successor of the COLL quadrant landed parents
// (ot_hfd_coll_q3_lp_ar / ot_hfd_coll_q2_lp_ar).  The ar128 parent gates failed CTS with
//   "OT_HYBRID: CTS source ck_sw must reach only standard-cell clock pins"
// because 14 raw SRAM macros (issuer 6 + link_e retry stores 2 x 4) sat in the parent's SOFT glue on the sw region
// root (multiple_cts_roots admits only hard-child clock pins), and ck_sw carried 76.4k soft flops (issuer 21.5k,
// reduce 21.2k, links 13.3k, fj 4.6k).  Each soft mass becomes ONE hard child with ONE scalar clock pin and NO
// parameters on its instance (exact view names; yosys renames parameterised modules, memory yosys-keep-paramod):
//   ot_hgi_coll_issuer_m_r128   = ot_hgi_coll_issuer_m128v7 (v7 core; 10 SRAMs, was issuer_m #(ROWS 128) v6)
//   ot_hgi_coll_fj_n2s1_r128    = ot_hgi_coll_fj_n2s1 #(ROWS 128)             (q3 programme target / fault join)
//   ot_hgi_coll_fj_q2_r128      = ot_hgi_coll_fj_q2 #(ROWS 128)               (q2)
//   ot_hgi_coll_link_e1         = ot_hgi_coll_link_e with its 5 entry clocks on ONE pin (4 SRAMs inside the leaf)
//   ot_hgi_coll_reduce_lane     = one of the 16 lanes of ot_hgi_coll_reduce_static (16 x 32 b tagged state +
//                                 the LAT-8 FP32 add lane), hardened once, replicated 16x
//   ot_hgi_coll_reduce_static_ctl = the reduce control (tags / faults / 8-edge writeback pipe / out_flit), soft
// Every wrapper / split is EXACT (same edges, same bits): tb_hgi_coll_reduce_split_eq proves the reduce split
// against ot_hgi_coll_reduce_static; the parent lockstep (tb_hfd_coll_<v>_lpf_ars_eq) proves the whole parent.

module ot_hgi_coll_issuer_m_r128(
 input wire clk_control,input wire rst_n,
 input wire [36:0] cfg,input wire start,input wire [6:0] start_pc,
 output wire busy,done,fault,uop_v,
 output wire [6:0] uop_pc,
 output wire [1535:0] uop_d1,
 output wire busy_d3,done_d3,start_d3,
 output wire busy_d2,start_d2,
 output wire [31:0] tap_iteration,
 output wire [87:0] tap_steps
);
 // HBM-COLLQ3-V7 (10-19, LEAD3-HBM "SRAM v7"): the leaf body is the v7 core (ot_hgi_coll_static_issuer_v7r128.sv:
 // metadata in 4 x 128x64 SRAM copies with a registered C/CT/CN lookahead, loop counters by id, programme words in
 // 6 x 128x256 SRAM), port- and edge-identical to ot_hgi_coll_issuer_m #(ROWS 128) (v6, 16 kb runtime-indexed flop tables =
 // SAFE item 5 FAIL; kept only as the miter / lockstep reference). Instance name u unchanged.
 ot_hgi_coll_issuer_m128v7 u(.clk_control(clk_control),.rst_n(rst_n),.cfg(cfg),.start(start),.start_pc(start_pc),
  .busy(busy),.done(done),.fault(fault),.uop_v(uop_v),.uop_pc(uop_pc),.uop_d1(uop_d1),.busy_d3(busy_d3),.done_d3(done_d3),
  .start_d3(start_d3),.busy_d2(busy_d2),.start_d2(start_d2),.tap_iteration(tap_iteration),.tap_steps(tap_steps));
endmodule

module ot_hgi_coll_fj_n2s1_r128(
 input wire clk,rst_n,input wire [1:0] qid,
 input wire cfg_v,input wire [7:0] cfg_target,input wire [11:0] cfg_addr,input wire [255:0] cfg_data,
 input wire desc_v,input wire [11:0] desc_base,input wire [12:0] desc_limit,input wire [15:0] desc_loops,
 input wire launch_v,program_active,issuer_busy,issuer_fault,issuer_uop_v,input wire [6:0] issuer_uop_pc,
 output wire [36:0] issuer_cfg,output wire issuer_start,output wire [6:0] issuer_start_pc,
 output wire configured,init_busy,program_fault,
 input wire protocol_fault,input wire [9:0] capture_fault,input wire [17:0] select_fault,unavailable_fault,
 input wire [1:0] link_abort,input wire ring_fault,writer_fault,reduce_fault,arg_fault,tkm_fault,
 output wire fault,output wire [15:0] fault_cause);
 ot_hgi_coll_fj_n2s1 #(.ROWS(128)) u(.clk(clk),.rst_n(rst_n),.qid(qid),.cfg_v(cfg_v),.cfg_target(cfg_target),
  .cfg_addr(cfg_addr),.cfg_data(cfg_data),.desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),
  .desc_loops(desc_loops),.launch_v(launch_v),.program_active(program_active),.issuer_busy(issuer_busy),
  .issuer_fault(issuer_fault),.issuer_uop_v(issuer_uop_v),.issuer_uop_pc(issuer_uop_pc),.issuer_cfg(issuer_cfg),
  .issuer_start(issuer_start),.issuer_start_pc(issuer_start_pc),.configured(configured),.init_busy(init_busy),
  .program_fault(program_fault),.protocol_fault(protocol_fault),.capture_fault(capture_fault),
  .select_fault(select_fault),.unavailable_fault(unavailable_fault),.link_abort(link_abort),.ring_fault(ring_fault),
  .writer_fault(writer_fault),.reduce_fault(reduce_fault),.arg_fault(arg_fault),.tkm_fault(tkm_fault),
  .fault(fault),.fault_cause(fault_cause));
endmodule

module ot_hgi_coll_fj_q2_r128(
 input wire clk,rst_n,input wire [1:0] qid,
 input wire cfg_v,input wire [7:0] cfg_target,input wire [11:0] cfg_addr,input wire [255:0] cfg_data,
 input wire desc_v,input wire [11:0] desc_base,input wire [12:0] desc_limit,input wire [15:0] desc_loops,
 input wire launch_v,program_active,issuer_busy,issuer_fault,issuer_uop_v,input wire [6:0] issuer_uop_pc,
 output wire [36:0] issuer_cfg,output wire issuer_start,output wire [6:0] issuer_start_pc,
 output wire configured,init_busy,program_fault,
 input wire protocol_fault,input wire [8:0] capture_fault,input wire [17:0] select_fault,unavailable_fault,
 input wire [1:0] link_abort,input wire ring_fault,writer_fault,reduce_fault,
 input wire arg_capture_slot,tkm_start,input wire [3:0] tkm_del_slot,tkm_dest_v,
 output wire fault,output wire [15:0] fault_cause);
 ot_hgi_coll_fj_q2 #(.ROWS(128)) u(.clk(clk),.rst_n(rst_n),.qid(qid),.cfg_v(cfg_v),.cfg_target(cfg_target),
  .cfg_addr(cfg_addr),.cfg_data(cfg_data),.desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),
  .desc_loops(desc_loops),.launch_v(launch_v),.program_active(program_active),.issuer_busy(issuer_busy),
  .issuer_fault(issuer_fault),.issuer_uop_v(issuer_uop_v),.issuer_uop_pc(issuer_uop_pc),.issuer_cfg(issuer_cfg),
  .issuer_start(issuer_start),.issuer_start_pc(issuer_start_pc),.configured(configured),.init_busy(init_busy),
  .program_fault(program_fault),.protocol_fault(protocol_fault),.capture_fault(capture_fault),
  .select_fault(select_fault),.unavailable_fault(unavailable_fault),.link_abort(link_abort),.ring_fault(ring_fault),
  .writer_fault(writer_fault),.reduce_fault(reduce_fault),.arg_capture_slot(arg_capture_slot),.tkm_start(tkm_start),
  .tkm_del_slot(tkm_del_slot),.tkm_dest_v(tkm_dest_v),.fault(fault),.fault_cause(fault_cause));
endmodule

// link_e with its five same-region entry clocks (control + 4 retry-store banks) on ONE scalar clock pin: the leaf's
// own CTS tree balances the control flops and the 4 SRAM clock pins (the parent gate's link graph read the 5-bit
// {5{ck_sw}} pin as "no region": u_link0/1 (None) in every unlanded-link FAIL of the lpk6 / ar128 gates).
module ot_hgi_coll_link_e1(
 input wire clk,input wire rst_n,epoch_begin,input wire [7:0] epoch_new,held_epoch,
 input wire wr_v,wr_observed_v,input wire [15:0] wr_seq,input wire [544:0] wr_flit,
 input wire rd_v,input wire [15:0] rd_seq,input wire rx_expect_v,input wire [15:0] rx_expect_seq,
 input wire phy_up,output wire tx_pin_v,output wire [611:0] tx_pin_flit,
 input wire rx_pin_v,input wire [611:0] rx_pin_flit,output wire rx_v,output wire [544:0] rx_flit,
 output wire epoch_abort,retry_requested,output wire [10:0] fault_cause);
 ot_hgi_coll_link_e u(.ck({5{clk}}),.rst_n(rst_n),.epoch_begin(epoch_begin),.epoch_new(epoch_new),.held_epoch(held_epoch),
  .wr_v(wr_v),.wr_observed_v(wr_observed_v),.wr_seq(wr_seq),.wr_flit(wr_flit),.rd_v(rd_v),.rd_seq(rd_seq),
  .rx_expect_v(rx_expect_v),.rx_expect_seq(rx_expect_seq),.phy_up(phy_up),.tx_pin_v(tx_pin_v),.tx_pin_flit(tx_pin_flit),
  .rx_pin_v(rx_pin_v),.rx_pin_flit(rx_pin_flit),.rx_v(rx_v),.rx_flit(rx_flit),.epoch_abort(epoch_abort),
  .retry_requested(retry_requested),.fault_cause(fault_cause));
endmodule

// One reduce lane: the 16 x 32-b tagged state (ot_hgi_coll_reduce_static_state_lane) and its LAT-8 FP32 add lane
// (ot_hgi_coll_pring_static_add_lane).  in_data = in_flit[l*32+:32] (the state lane's load_data AND external_data:
// one pin).  wb / wb_tag come from the control's 8-edge pipe (aligned with the add lane LAT 8, as in reduce_static).
module ot_hgi_coll_reduce_lane(
 input wire clk,rst_n,
 input wire load_v,input wire [3:0] load_tag,input wire [31:0] in_data,
 input wire wb,input wire [3:0] wb_tag,
 input wire add_read,input wire [3:0] read_tag,input wire add_issue,
 input wire pub_read,input wire [3:0] pub_tag_a,pub_tag_b,
 output wire [31:0] pub_a,pub_b,
 output wire add_valid
);
 wire [31:0] acc,operand,sum;
 wire [31:0] ext_data;
`ifdef OT_COLL_RLANE_MUT_EXT
 assign ext_data={in_data[30:0],in_data[31]};   // bench mutant: the external operand rotated (must FAIL every EQ)
`else
 assign ext_data=in_data;
`endif
 ot_hgi_coll_reduce_static_state_lane u_state(
  .clk(clk),.load_v(load_v),.load_tag(load_tag),.load_data(in_data),
  .wb(wb),.wb_tag(wb_tag),.wb_data(sum),
  .add_read(add_read),.read_tag(read_tag),.external_data(ext_data),
  .pub_read(pub_read),.pub_tag_a(pub_tag_a),.pub_tag_b(pub_tag_b),
  .acc(acc),.operand(operand),.pub_a(pub_a),.pub_b(pub_b));
 ot_hgi_coll_pring_static_add_lane #(.LAT(8)) u_add(
  .clk(clk),.rst_n(rst_n),.valid_in(add_issue),.a(acc),.b(operand),.y(sum),.valid_out(add_valid));
endmodule

// The control of ot_hgi_coll_reduce_static, verbatim, with the 16 lanes outside (wb / wb_tag out, add_valid /
// pub_a / pub_b in).
module ot_hgi_coll_reduce_static_ctl #(parameter integer MUT_TAG=0,MUT_BF16=0)(
 input wire clk_control,
 input wire rst_n,clear,in_v,
 input wire load_v,input wire [3:0] load_tag,
 input wire add_read,input wire [3:0] read_tag,input wire add_issue,
 input wire pub_read,input wire [3:0] pub_tag_a,pub_tag_b,
 input wire pub_bf16,input wire [32:0] pub_meta,input wire pub_release,pub_issue,
 input wire [15:0] add_valid,input wire [511:0] pub_a,pub_b,
 output wire wb,output wire [3:0] wb_tag,
 output reg out_v,output reg [544:0] out_flit,
 output wire fault,output reg [7:0] fault_cause
);
 reg [15:0] valid,pending;
 reg read_v,pub_v;
 reg [3:0] read_tag_q,pub_a_q,pub_b_q;
 reg pub_bf_q,pub_release_q;
 reg [32:0] pub_meta_q;
 reg [7:0] pipe_v;
 reg [3:0] pipe_tag[0:7];
 assign wb=pipe_v[7];
 assign wb_tag=pipe_tag[7] ^ (MUT_TAG?4'd1:4'd0);
 function automatic [15:0] bf16(input [31:0] x);
  reg [31:0] rounded;
  begin
   if(x[30:23]==8'hff)bf16={x[31:16]} | ((|x[22:0])?16'h0040:16'h0000);
   else begin
    rounded=x+(MUT_BF16?32'h8000:(32'h7fff+{31'b0,x[16]}));
    bf16=rounded[31:16];
   end
  end
 endfunction
 wire [511:0] bf_packed;
 for(genvar l=0;l<16;l=l+1)begin:g_bf
  assign bf_packed[l*16+:16]=bf16(pub_a[l*32+:32]);
  assign bf_packed[256+l*16+:16]=bf16(pub_b[l*32+:32]);
 end
 assign fault=|fault_cause;
 always @(posedge clk_control or negedge rst_n)begin:control
  reg [7:0] nf;
  if(!rst_n)begin
   valid<=0;pending<=0;read_v<=0;pub_v<=0;pipe_v<=0;
   read_tag_q<=0;pub_a_q<=0;pub_b_q<=0;pub_bf_q<=0;pub_release_q<=0;pub_meta_q<=0;
   out_v<=0;fault_cause<=0;
   for(integer k=0;k<8;k=k+1)pipe_tag[k]<=0;
  end else begin
   nf=0;
   if(in_v!==(load_v|add_read))nf[0]=1;
   if(add_issue!==read_v || pub_issue!==pub_v)nf[1]=1;
   if(add_read && (!valid[read_tag]||pending[read_tag]))nf[2]=1;
   if(pub_read && (!valid[pub_tag_a]||pending[pub_tag_a]||
      (pub_bf16 && (!valid[pub_tag_b]||pending[pub_tag_b]))))nf[2]=1;
   if(load_v && (valid[load_tag]||pending[load_tag]))nf[4]=1;
   if(load_v && add_read)nf[3]=1;
   if(load_v && wb && load_tag==wb_tag)nf[3]=1;
   if(add_issue && ((wb&&wb_tag==read_tag_q)||(load_v&&load_tag==read_tag_q)))nf[3]=1;
   if(add_read && add_issue && read_tag==read_tag_q)nf[3]=1;
   if(pub_read && add_issue && (pub_tag_a==read_tag_q||(pub_bf16&&pub_tag_b==read_tag_q)))nf[3]=1;
   if(pub_read && pub_issue && pub_release_q &&
      (pub_tag_a==pub_a_q||(pub_bf_q&&pub_tag_a==pub_b_q)||
       (pub_bf16&&(pub_tag_b==pub_a_q||(pub_bf_q&&pub_tag_b==pub_b_q)))))nf[3]=1;
   if(add_read && ((load_v&&load_tag==read_tag)||(wb&&wb_tag==read_tag)))nf[3]=1;
   if(pub_read && ((load_v&&(load_tag==pub_tag_a||(pub_bf16&&load_tag==pub_tag_b)))||
      (wb&&(wb_tag==pub_tag_a||(pub_bf16&&wb_tag==pub_tag_b)))))nf[3]=1;
   if(add_issue && pub_issue && pub_release_q &&
      (read_tag_q==pub_a_q||(pub_bf_q&&read_tag_q==pub_b_q)))nf[3]=1;
   if(add_read && pub_issue && pub_release_q &&
      (read_tag==pub_a_q||(pub_bf_q&&read_tag==pub_b_q)))nf[3]=1;
   if(clear && ((|pending)||(|pipe_v)||read_v||pub_v||load_v||add_read||pub_read||add_issue||pub_issue))nf[5]=1;
   if(add_valid!={16{wb}})nf[6]=1;
   if(wb && (!pending[wb_tag]||valid[wb_tag]))nf[7]=1;
   fault_cause<=fault_cause|nf;
   read_v<=add_read;read_tag_q<=read_tag;
   pub_v<=pub_read;pub_a_q<=pub_tag_a;pub_b_q<=pub_tag_b;
   pub_bf_q<=pub_bf16;pub_meta_q<=pub_meta;pub_release_q<=pub_release;
   pipe_v<={pipe_v[6:0],add_issue};pipe_tag[0]<=read_tag_q;
   for(integer k=1;k<8;k=k+1)pipe_tag[k]<=pipe_tag[k-1];
   for(integer t=0;t<16;t=t+1)begin
    if(clear)begin valid[t]<=0;pending[t]<=0;end
    else begin
     if((load_v&&load_tag==t)||(wb&&wb_tag==t)||
        (add_issue&&read_tag_q==t)||(pub_issue&&pub_release_q&&(pub_a_q==t||(pub_bf_q&&pub_b_q==t))))
      valid[t]<=((load_v&&load_tag==t)||(wb&&wb_tag==t)) &&
        !(add_issue&&read_tag_q==t) && !(pub_issue&&pub_release_q&&(pub_a_q==t||(pub_bf_q&&pub_b_q==t)));
     if((add_issue&&read_tag_q==t)||(wb&&wb_tag==t))
      pending[t]<=(add_issue&&read_tag_q==t) && !(wb&&wb_tag==t);
    end
   end
   out_v<=pub_issue;
  end
 end
 always @(posedge clk_control)out_flit<={pub_meta_q,pub_bf_q?bf_packed:pub_a};
endmodule

// Bench vehicle only: the split reduce (control + 16 hardened lanes) with the ports of ot_hgi_coll_reduce_static.
module ot_hgi_coll_reduce_split #(parameter integer MUT_TAG=0,MUT_BF16=0)(
 input wire clk_control,input wire [15:0] clk_state,clk_add,
 input wire rst_n,clear,in_v,input wire [544:0] in_flit,
 input wire load_v,input wire [3:0] load_tag,
 input wire add_read,input wire [3:0] read_tag,input wire add_issue,
 input wire pub_read,input wire [3:0] pub_tag_a,pub_tag_b,
 input wire pub_bf16,input wire [32:0] pub_meta,input wire pub_release,pub_issue,
 output wire out_v,output wire [544:0] out_flit,
 output wire fault,output wire [7:0] fault_cause
);
 wire wb;wire [3:0] wb_tag;wire [15:0] add_valid;wire [511:0] pub_a,pub_b;
 for(genvar l=0;l<16;l=l+1)begin:g_lane
  ot_hgi_coll_reduce_lane u_lane(.clk(clk_state[l]),.rst_n(rst_n),.load_v(load_v),.load_tag(load_tag),
   .in_data(in_flit[l*32+:32]),.wb(wb),.wb_tag(wb_tag),.add_read(add_read),.read_tag(read_tag),.add_issue(add_issue),
   .pub_read(pub_read),.pub_tag_a(pub_tag_a),.pub_tag_b(pub_tag_b),.pub_a(pub_a[l*32+:32]),.pub_b(pub_b[l*32+:32]),
   .add_valid(add_valid[l]));
 end
 ot_hgi_coll_reduce_static_ctl #(.MUT_TAG(MUT_TAG),.MUT_BF16(MUT_BF16)) u_ctl(.clk_control(clk_control),.rst_n(rst_n),
  .clear(clear),.in_v(in_v),.load_v(load_v),.load_tag(load_tag),.add_read(add_read),.read_tag(read_tag),
  .add_issue(add_issue),.pub_read(pub_read),.pub_tag_a(pub_tag_a),.pub_tag_b(pub_tag_b),.pub_bf16(pub_bf16),
  .pub_meta(pub_meta),.pub_release(pub_release),.pub_issue(pub_issue),.add_valid(add_valid),.pub_a(pub_a),.pub_b(pub_b),
  .wb(wb),.wb_tag(wb_tag),.out_v(out_v),.out_flit(out_flit),.fault(fault),.fault_cause(fault_cause));
endmodule
`default_nettype wire
