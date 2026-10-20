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
//   ot_hgi_coll_fj_n2s1_r128    = ot_hgi_coll_fj_n2s1 #(ROWS 128) edge-identical (q3 programme target / fault join); HBM-COLLFJ2
//                                 10-19: body ot_hgi_coll_fj_core_s128 (below: 12 kept reset copies, flow
//                                 store in a 128x64 SRAM, registered frame decode)
//   ot_hgi_coll_fj_q2_r128      = ot_hgi_coll_fj_q2 #(ROWS 128) edge-identical (q2; same SAFE body)
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

// HBM-COLLQ3-5 10-20: RC 32 reset copies (was default 20): r128u/u2 post-GRT census showed pin_reg_split RESETN clones
// (+13/+10) on 24..27-load copies -> 37/34; 527 loads / 32 = <=17 per copy (+13 reserve <= 30). rst_n drives exactly 32 copies.
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
 ot_hgi_coll_fj_core_s128 #(.NPT(2),.SOLO(1),.NS(10),.NSL(18),.RC(32)) u(.clk(clk),.rst_n(rst_n),.qid(qid),.cfg_v(cfg_v),.cfg_target(cfg_target),
  .cfg_addr(cfg_addr),.cfg_data(cfg_data),.desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),
  .desc_loops(desc_loops),.launch_v(launch_v),.program_active(program_active),.issuer_busy(issuer_busy),
  .issuer_fault(issuer_fault),.issuer_uop_v(issuer_uop_v),.issuer_uop_pc(issuer_uop_pc),.issuer_cfg(issuer_cfg),
  .issuer_start(issuer_start),.issuer_start_pc(issuer_start_pc),.configured(configured),.init_busy(init_busy),
  .program_fault(program_fault),.protocol_fault(protocol_fault),.capture_fault(capture_fault),
  .select_fault(select_fault),.unavailable_fault(unavailable_fault),.link_abort(link_abort),.ring_fault(ring_fault),
  .writer_fault(writer_fault),.reduce_fault(reduce_fault),.arg_fault(arg_fault),.tkm_fault(tkm_fault),
  .arg_capture_slot(1'b0),.tkm_start(1'b0),.tkm_del_slot(4'd0),.tkm_dest_v(4'd0),
  .fault(fault),.fault_cause(fault_cause));
endmodule

// HBM-COLLQ3-5 10-20: RC 32 reset copies (see ot_hgi_coll_fj_n2s1_r128).
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
 ot_hgi_coll_fj_core_s128 #(.NPT(2),.SOLO(0),.NS(9),.NSL(18),.RC(32)) u(.clk(clk),.rst_n(rst_n),.qid(qid),.cfg_v(cfg_v),.cfg_target(cfg_target),
  .cfg_addr(cfg_addr),.cfg_data(cfg_data),.desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),
  .desc_loops(desc_loops),.launch_v(launch_v),.program_active(program_active),.issuer_busy(issuer_busy),
  .issuer_fault(issuer_fault),.issuer_uop_v(issuer_uop_v),.issuer_uop_pc(issuer_uop_pc),.issuer_cfg(issuer_cfg),
  .issuer_start(issuer_start),.issuer_start_pc(issuer_start_pc),.configured(configured),.init_busy(init_busy),
  .program_fault(program_fault),.protocol_fault(protocol_fault),.capture_fault(capture_fault),
  .select_fault(select_fault),.unavailable_fault(unavailable_fault),.link_abort(link_abort),.ring_fault(ring_fault),
  .writer_fault(writer_fault),.reduce_fault(reduce_fault),.arg_capture_slot(arg_capture_slot),.tkm_start(tkm_start),
  .tkm_del_slot(tkm_del_slot),.tkm_dest_v(tkm_dest_v),.arg_fault(1'b0),.tkm_fault(1'b0),.fault(fault),.fault_cause(fault_cause));
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

// ---------------------------------------------------------------------------------------------------------------
// HBM-COLLFJ2 (10-19, LEAD3-HBM: SAFE-DESIGN items 3/4/5 binding, no waiver): the ROWS-128 programme target of the SAFE
// fj leaves (ot_hgi_coll_fj_n2s1_r128 / ot_hgi_coll_fj_q2_r128, via ot_hgi_coll_fj_core_s128).  PORT- AND EDGE-
// IDENTICAL to ot_hgi_coll_static_program_target #(ROWS 128) (the closed form, kept unchanged for every other user and as
// the v8x/v8g lockstep reference): every output equals the reference every cycle (tb_hfd_coll_q{3,2}_lpf_ars_eq).
// Instantiated by ot_hgi_coll_fj_core_s128 (below) only.
// Structural changes (r128w gates: setup +1.2 / +4.7 ps, worst endpoints u_program.assembly[*] / flow[*][*] / fault D =
// the frame-accept cone addr_q -> loaded[a_row] (128:1) / spare-zero OR192 / target compare -> 1.5k+2k flop enables):
//  (a) flow store: the 128 x 16-b flow words (2 kb of runtime-indexed flops, item 5 borderline) live in ONE
//      ot_sram_1rw_128x64_m2_r2c2_p192_mir (u_flow, as ROWS 256 does): the macro read IS the scan lookahead (row 0 read at
//      descriptor accept, row+1 while scanning); the loaded bit of the scanned row is the registered lookahead ld_la.
//      The flow WRITE is registered one edge after the accepted segment-6 frame (fw_q / fa_q / fd_q: macro write pins are
//      flop Q): invisible, because a descriptor scan (the only reader) needs seen==0, i.e. >= 54 edges after that frame.
//  (b) registered decode: every frame / descriptor check that depends only on the captured inputs is computed one edge
//      early from this module's input ports (the same values the capture rung registers): tm_q (target match), seg_q
//      (one-hot segment), ahb_q (address high bits), dsp_q (metadata spare / data[255:64] nonzero), dbad_q (descriptor
//      range / loops), ldh_q = loaded[row of cfg_addr] with the same-edge drain completion forwarded (the only writer of
//      loaded).  Exact: each is a pure function of values the reference reads one edge later.
// Schedule: 0 port edges moved -> 0 cycles DS / Qwen.  Reset: this module's flops reset from rst_n, which ot_hgi_coll_fj_core_s128
// drives from bit 0 of its KEPT copy family rst__ot_rlv; ot_rst_copies.tcl re-points the loads over the copies.
module ot_hgi_coll_static_program_target_s128 #(
    parameter [7:0] TARGET=8'd52,
    parameter integer MUT_DATA=0,
    parameter integer ASSEMBLY_PIPE=0
)(
    input wire clk,rst_n,
    input wire cfg_v,
    input wire [7:0] cfg_target,
    input wire [11:0] cfg_addr,
    input wire [31:0] cfg_lookup_addr,
    input wire [255:0] cfg_data,
    input wire desc_v,
    input wire [11:0] desc_base,
    input wire [12:0] desc_limit,
    input wire [15:0] desc_loops,
    input wire launch_v,program_active,
    input wire issuer_busy,issuer_fault,issuer_uop_v,
    input wire [6:0] issuer_uop_pc,
    output reg [36:0] issuer_cfg,
    output reg issuer_start,
    output reg [6:0] issuer_start_pc,
    output reg configured,init_busy,fault
);
    localparam integer ROWS=128, PW=7, FW=16;
    localparam [12:0] MSPARE=13'h1ff8;
    // capture rung (as the reference) + the registered decode of the captured values
    reg cv,dv,lv;
    reg [11:0] addr_q,base_q;
    reg [12:0] limit_q;
    reg [255:0] data_q;
    reg tm_q,ahb_q,dsp_q,dbad_q,ldh_q;
    reg [7:0] seg_q;
    reg [1535:0] assembly;
    reg [63:0] metadata;
    reg [6:0] seen;
    reg [PW-1:0] row;
    reg [ROWS-1:0] loaded;
    reg checking,check_bad;
    reg [PW-1:0] check_row;
    reg draining;
    reg [5:0] step;
    reg [PW-1:0] base;
    reg [PW:0] limit;
    reg ld_la;
    reg fw_q;reg [PW-1:0] fa_q;reg [FW-1:0] fd_q;
`ifdef OT_PT_MUT_LATE_SPC
    localparam integer PCREG=1;
`else
    localparam integer PCREG=(ASSEMBLY_PIPE==0);
`endif
    generate if(PCREG==0)begin:g_start_pc_alias
        assign issuer_start_pc=base;
    end endgenerate
    integer k;
    wire [PW-1:0] c_row=cfg_addr[PW+2:3];
    wire drain_done=draining && step==6'd53;
    wire cfg_loaded;
    wire scan_loaded;
    wire [6:0] scan_next=check_row+1'b1;
    generate if(ASSEMBLY_PIPE!=0)begin:g_loaded_banks
        (* keep = "true" *) reg [3:0] scan_addr[0:3];
        (* keep = "true" *) reg [3:0] write_addr[0:3];
        wire [7:0] cfg_bits,scan_bits;
        (* keep = "true" *) reg [1:0] checking_copy;
        for(genvar cc=0;cc<2;cc=cc+1)begin:g_check_copy
            always @(posedge clk or negedge rst_n)
                if(!rst_n)checking_copy[cc]<=0;
                else begin
                    if(checking && check_row==127)checking_copy[cc]<=0;
                    if(dacc)checking_copy[cc]<=1;
                end
        end
        for(genvar ac=0;ac<4;ac=ac+1)begin:g_addr
            // Loaded write occurs only at drain step53, long after row settled.
            // Unconditional local copies avoid a shared frame-accept hold mux.
            always @(posedge clk)write_addr[ac]<=row[3:0];
            always @(posedge clk or negedge rst_n)
                if(!rst_n)begin scan_addr[ac]<=1;end
                else begin
                    if(checking_copy[ac/2] && check_row!=127)scan_addr[ac]<=check_row[3:0]+4'd2;
                    else scan_addr[ac]<=1;
                end
        end
        for(genvar bk=0;bk<8;bk=bk+1)begin:g_bank
            reg [15:0] loaded_local;
            assign loaded[bk*16+:16]=loaded_local;
            always @(posedge clk or negedge rst_n)
                if(!rst_n)loaded_local<=0;
                else if(drain_done && row[6:4]==3'(bk))loaded_local[write_addr[bk/2]]<=1;
            assign cfg_bits[bk]=loaded[bk*16+cfg_lookup_addr[bk*4+:4]];
            assign scan_bits[bk]=loaded[bk*16+scan_addr[bk/2]];
        end
        assign cfg_loaded=cfg_bits[c_row[6:4]];
        assign scan_loaded=scan_bits[scan_next[6:4]];
    end else begin:g_loaded_binary
        assign cfg_loaded=loaded[c_row];
        assign scan_loaded=loaded[scan_next];
    end endgenerate
    always @(posedge clk)begin
        addr_q<=cfg_addr;data_q<=cfg_data;base_q<=desc_base;limit_q<=desc_limit;
        tm_q<=(cfg_target==TARGET);
        seg_q<=8'b1<<cfg_addr[2:0];
        ahb_q<=(cfg_addr[11:10]!=2'b00);
        dsp_q<=(cfg_data[255:64]!=0) || ((cfg_data[63:51]&MSPARE)!=0);
        dbad_q<=(desc_base>=ROWS) || (desc_limit>ROWS) || (desc_limit<={1'b0,desc_base}) || (desc_loops!=1);
`ifdef OT_PT_MUT_LDH_NOFWD
        ldh_q<=cfg_loaded;                                      // mutant: same-edge drain completion not forwarded
`else
        ldh_q<=cfg_loaded || (drain_done && row==c_row);
`endif
    end
    wire [PW-1:0] a_row=addr_q[PW+2:3];
    wire in_range={1'b0,check_row}>=base && {1'b0,check_row}<limit;
    wire [63:0] rd;
    wire [FW-1:0] f=rd[FW-1:0];
    wire ld=ld_la;
    wire [PW-1:0] f_nx=f[PW-1:0],f_tg=f[2*PW-1:PW];wire f_halt=f[FW-1],f_rep=f[FW-2];
    wire row_bad=in_range && (!ld ||
        (!f_halt && (f_nx<base || {1'b0,f_nx}>=limit ||
          (f_rep && (f_tg<base || {1'b0,f_tg}>=limit)))) ||
        ({1'b0,check_row}==limit-1'b1 && !f_halt));
    wire occupied=program_active || issuer_busy || issuer_start;
    // frame / descriptor accept (the reference's fault conditions, on the registered decode)
    wire frame=cv && tm_q;
    wire frame_bad=occupied || lv || draining || checking || fault || dv || ahb_q || seg_q[7] || ldh_q ||
        (seen!=0 && row!=a_row) || ((seen & seg_q[6:0])!=0) || (seg_q[6] && dsp_q);
    wire desc=dv && tm_q;
    wire desc_guard=!(occupied || lv || draining || checking || seen!=0 || fault || cv || dbad_q);
    wire dacc=desc && desc_guard;
    generate if(ASSEMBLY_PIPE!=0)begin:g_descriptor_fields
        // Two copies of the existing descriptor capture edge give each held
        // field its own physical accept cone; no shared 38-load mux enable.
        (* keep = "true" *) reg [1:0] desc_copy;
        always @(posedge clk or negedge rst_n)
            if(!rst_n)desc_copy<=0;
            else desc_copy<={2{desc_v}};
        always @(posedge clk or negedge rst_n)
            if(!rst_n)begin base<=0;limit<=0;end
            else begin
                if(desc_copy[0] && tm_q && desc_guard)base<=base_q[PW-1:0];
                if(desc_copy[1] && tm_q && desc_guard)limit<=limit_q[PW:0];
            end
    end endgenerate
    // COLLFJ native census 10-20: six 256-bit write enables had logical fanout 264.
    // Sixteen kept write-enable copies per segment each serve one 16-bit chunk.
    // The SRAM-style write landing is one internal edge later; first assembly read
    // is drain step 1, two edges after the final accepted frame, so output edges stay exact.
    generate if(ASSEMBLY_PIPE!=0)begin:g_assembly_pipe
        (* keep = "true" *) reg [95:0] we_copy;
        reg [255:0] payload;
        always @(posedge clk) payload<=data_q;
        (* keep = "true" *) reg [3:0] meta_we;
        for(genvar mc=0;mc<4;mc=mc+1)begin:g_metadata
            always @(posedge clk or negedge rst_n)
                if(!rst_n)meta_we[mc]<=0;
                else meta_we[mc]<=frame && !frame_bad && seg_q[6];
            always @(posedge clk)
                if(meta_we[mc])metadata[mc*16+:16]<=payload[mc*16+:16];
        end
        for(genvar sg=0;sg<6;sg=sg+1)begin:g_seg
            for(genvar ch=0;ch<16;ch=ch+1)begin:g_chunk
                always @(posedge clk or negedge rst_n)
                    if(!rst_n)we_copy[sg*16+ch]<=0;
                    else we_copy[sg*16+ch]<=frame && !frame_bad && seg_q[sg];
                always @(posedge clk)
                    if(we_copy[sg*16+ch])assembly[sg*256+ch*16+:16]<=payload[ch*16+:16];
            end
        end
    end endgenerate
    wire [31:0] assembly_word;
    generate if(ASSEMBLY_PIPE!=0)begin:g_drain_onehot
        // Kept read selectors are prepared at the previous drain step, avoiding
        // the runtime divide/modulo -> 48:1 word mux control broadcasts.
        (* keep = "true" *) reg [5:0] step_copy[0:1];
        (* keep = "true" *) reg [95:0] rd_select;
        (* keep = "true" *) reg [1:0] drain_copy;
        for(genvar dc=0;dc<2;dc=dc+1)begin:g_drain_copy
            always @(posedge clk or negedge rst_n)
                if(!rst_n)drain_copy[dc]<=0;
                else begin
                    if(draining && step==53)drain_copy[dc]<=0;
                    if(frame && !frame_bad && ((seen|seg_q[6:0])==7'h7f))drain_copy[dc]<=1;
                end
        end
        for(genvar cg=0;cg<2;cg=cg+1)begin:g_counter
            always @(posedge clk or negedge rst_n)
                if(!rst_n)step_copy[cg]<=0;
                else if(frame && !frame_bad && ((seen|seg_q[6:0])==7'h7f))step_copy[cg]<=0;
                else if(draining && step!=53)step_copy[cg]<=step+1'b1;
        end
        for(genvar wd=0;wd<48;wd=wd+1)begin:g_word
            for(genvar half=0;half<2;half=half+1)begin:g_half
                always @(posedge clk or negedge rst_n)
                    if(!rst_n)rd_select[wd*2+half]<=0;
                    else rd_select[wd*2+half]<=drain_copy[wd/24] && step_copy[wd/24]==6'(wd+wd/16);
            end
        end
        reg [31:0] word_or;
        integer rw,rb;
        always @* begin
            word_or=0;
            for(rw=0;rw<48;rw=rw+1)
                for(rb=0;rb<32;rb=rb+1)
                    word_or[rb]=word_or[rb] | (assembly[rw*32+rb] && rd_select[rw*2+rb/16]);
        end
        assign assembly_word=word_or;
    end else begin:g_drain_binary
        assign assembly_word=assembly[(step/17)*512+(step%17-1)*32+:32];
    end endgenerate
    wire fw=frame && !frame_bad && seg_q[6];
    wire [FW-1:0] fwd={data_q[44],|data_q[43:12],data_q[52],data_q[11:6],data_q[51],data_q[5:0]};
`ifdef OT_PT_MUT_LA_STALE
    wire fr=dacc;                                                  // mutant: lookahead never advances
`else
    wire fr=dacc || (checking && check_row!=PW'(ROWS-1));
`endif
    wire [PW-1:0] fa=dacc ? {PW{1'b0}} : PW'(check_row+1'b1);
    always @(posedge clk)begin fa_q<=a_row;fd_q<=fwd;end
    ot_sram_1rw_128x64_m2_r2c2_p192_mir u_flow(.clk(clk),.ce_in(fw_q || fr),.we_in(fw_q),.addr_in(fw_q ? fa_q : fa),
        .wd_in(64'(fd_q)),.w_mask_in({64{1'b1}}),.rd_out(rd),
        .rr_en(2'b0),.rr_addr(12'b0),.cr_en(2'b0),.cr_sel(12'b0));
    always @(posedge clk or negedge rst_n)begin
        if(!rst_n)begin
            cv<=0;dv<=0;lv<=0;issuer_cfg<=0;issuer_start<=0;
            if(PCREG!=0)issuer_start_pc<=0;configured<=0;init_busy<=0;fault<=0;
            seen<=0;if(ASSEMBLY_PIPE==0)loaded<=0;row<=0;draining<=0;step<=0;
            if(ASSEMBLY_PIPE==0)begin base<=0;limit<=0;end checking<=0;check_bad<=0;check_row<=0;ld_la<=0;fw_q<=0;
        end else begin
            cv<=cfg_v;dv<=desc_v;lv<=launch_v;
            issuer_cfg<=0;issuer_start<=0;fw_q<=fw;
            if(issuer_fault)fault<=1;
            if(checking)begin
                if(row_bad)check_bad<=1;
                if(check_row==PW'(ROWS-1))begin
                    checking<=0;init_busy<=0;
                    if(check_bad || row_bad)fault<=1;
                    else if(!fault)configured<=1;
                end else begin
                    check_row<=check_row+1'b1;
`ifndef OT_PT_MUT_LA_STALE
                    ld_la<=scan_loaded;
`endif
                end
            end
            if(issuer_uop_v && (!configured || issuer_uop_pc<base || {1'b0,issuer_uop_pc}>=limit))fault<=1;
            if(draining)begin
                if(step<51)begin
                    if(step%17==0)issuer_cfg<={1'b1,4'd0,23'b0,row[PW-1],2'(step/17),row[5:0]};
                    else issuer_cfg<={1'b1,4'd1,assembly_word ^ ((MUT_DATA!=0 && step==1)?32'b1:32'b0)};
                end else if(step==51)issuer_cfg<={1'b1,4'd2,metadata[31:0]};
                else if(step==52)issuer_cfg<={1'b1,4'd3,metadata[63:32]};
                // step53 ensures the issuer has sampled its final metadata.
                if(step==53)begin
                    draining<=0;if(ASSEMBLY_PIPE==0)loaded[row]<=1;seen<=0;init_busy<=0;
                end else step<=step+1'b1;
            end
            if(frame)begin
                if(frame_bad)fault<=1;
                else begin
                    row<=a_row;seen<=seen | seg_q[6:0];init_busy<=1;
                    if(ASSEMBLY_PIPE==0 && seg_q[6])metadata<=data_q[63:0];
                    if(ASSEMBLY_PIPE==0)for(k=0;k<6;k=k+1) if(seg_q[k]) assembly[k*256+:256]<=data_q;
                    if((seen | seg_q[6:0])==7'h7f)begin draining<=1;step<=0;end
                end
            end
            if(desc)begin
                if(!dacc)fault<=1;
                else begin
                    if(ASSEMBLY_PIPE==0)begin base<=base_q[PW-1:0];limit<=limit_q[PW:0];end configured<=0;
`ifndef OT_PT_MUT_LATE_SPC
                    if(PCREG!=0)issuer_start_pc<=base_q[PW-1:0];                     // mutant: start_pc only at launch (v7 start faults)
`endif
                    checking<=1;check_row<=0;check_bad<=0;init_busy<=1;
                    ld_la<=loaded[0];
                end
            end
            if(lv && configured)begin
                if(occupied || draining || checking || seen!=0 || fault || cv || dv)fault<=1;
                else begin issuer_start<=1;if(PCREG!=0)issuer_start_pc<=base;end
            end else if(lv && (seen!=0 || draining || checking))fault<=1;
        end
    end
endmodule

// ---------------------------------------------------------------------------------------------------------------
// HBM-COLLFJ2 (10-19): ot_hgi_coll_fj_core_s128 = ot_hgi_coll_fj_core #(ROWS 128) (ot_hfd_coll_q_hard_v5.sv, unchanged for
// every other user and as the v8x/v8g lockstep reference) with (1) the reset family rst__ot_rlv and (2) the programme target
// ot_hgi_coll_static_program_target_s128 above.  Same pin capture rung, same fault join, same edges.  Instantiated by the
// SAFE leaves ot_hgi_coll_fj_n2s1_r128 / ot_hgi_coll_fj_q2_r128 (ot_hgi_coll_safe_leaves.sv) as instance u.
module ot_hgi_coll_fj_core_s128 #(parameter integer NPT=3,SOLO=1,NS=11,NSL=18,RC=20,PW=7)(
 input wire clk,rst_n,
 input wire [1:0] qid,
 input wire cfg_v,
 input wire [7:0] cfg_target,
 input wire [11:0] cfg_addr,
 input wire [255:0] cfg_data,
 input wire desc_v,
 input wire [11:0] desc_base,
 input wire [12:0] desc_limit,
 input wire [15:0] desc_loops,
 input wire launch_v,program_active,
 input wire issuer_busy,issuer_fault,issuer_uop_v,
 input wire [PW-1:0] issuer_uop_pc,
 output wire [36:0] issuer_cfg,
 output wire issuer_start,
 output wire [PW-1:0] issuer_start_pc,
 output wire configured,init_busy,program_fault,
 // child fault faces (each a registered child output)
 input wire protocol_fault,
 input wire [NS-1:0] capture_fault,
 input wire [NSL-1:0] select_fault,unavailable_fault,
 input wire [NPT-1:0] link_abort,
 input wire ring_fault,writer_fault,reduce_fault,
 input wire arg_fault,tkm_fault,                 // q3 engines (SOLO!=0)
 input wire arg_capture_slot,                    // q2: compiled arg capture reservation (no arg source exists)
 input wire tkm_start,                           // q2: compiled tkm start
 input wire [3:0] tkm_del_slot,tkm_dest_v,       // q2: compiled tkm delivery reservation / tkm sinks
 output reg fault,
 output reg [15:0] fault_cause
);
 // Every input is captured at its pin (coordinator native audit of fj_q2 54f035ca0: 71 unregistered inputs, capture
 // 512.9 ps). rst_n: synchronous D-pin flop. HOST frames: +1 edge (target remap after capture, against the static
 // qid strap). Issuer feedback and child faults: +1 edge (exceptional fault ABI +1, like qslots pin_v2).
 // SAFE item 1/3: rst_n (landed in 2 registered stages at the face by the kit's reset_landing) is sampled by RC KEPT,
 // identical copies (one edge, the same release edge as the reference's single rst_q); every reset load of this leaf hangs
 // off copy 0 in RTL and physical/common_flow/ot_rst_copies.tcl (kit reset_relay_split max_loads 32) re-points them by
 // hierarchical-name region over the RC copies (~300 loads / 12 = ~25 per copy).  Family name suffix __ot_rlv.
 (* keep = "true" *) reg [RC-1:0] rst__ot_rlv;
 always @(posedge clk) rst__ot_rlv<={RC{rst_n}};
 wire rst_q=rst__ot_rlv[0];
 reg cv_q,dv_q,lv_q,act_q,ibusy_q,ifault_q,iuv_q;
 reg [7:0] tgt_q;reg [1:0] qid_q;reg [11:0] addr_q,base_q;reg [255:0] data_q;reg [12:0] limit_q;reg [15:0] loops_q;
 (* keep = "true" *) reg [31:0] cfg_lookup_addr;
 always @(posedge clk)cfg_lookup_addr<={8{cfg_addr[6:3]}};
 reg [PW-1:0] iupc_q;
 reg prot_q,ring_q,writer_q,reduce_q,arg_q,tkm_q,argcap_q,tkmstart_q;
 reg [NS-1:0] cap_q;reg [NSL-1:0] sel_q,unav_q;reg [NPT-1:0] lk_q;reg [3:0] tdel_q,tdest_q;
 always @(posedge clk)begin
  tgt_q<=cfg_target;qid_q<=qid;addr_q<=cfg_addr;data_q<=cfg_data;base_q<=desc_base;limit_q<=desc_limit;
  loops_q<=desc_loops;iupc_q<=issuer_uop_pc;
 end
 always @(posedge clk or negedge rst_q)
  if(!rst_q)begin
   cv_q<=0;dv_q<=0;lv_q<=0;act_q<=0;ibusy_q<=0;ifault_q<=0;iuv_q<=0;prot_q<=0;ring_q<=0;writer_q<=0;reduce_q<=0;
   arg_q<=0;tkm_q<=0;argcap_q<=0;tkmstart_q<=0;cap_q<=0;sel_q<=0;unav_q<=0;lk_q<=0;tdel_q<=0;tdest_q<=0;
  end else begin
   cv_q<=cfg_v;dv_q<=desc_v;lv_q<=launch_v;act_q<=program_active;ibusy_q<=issuer_busy;ifault_q<=issuer_fault;
   iuv_q<=issuer_uop_v;prot_q<=protocol_fault;ring_q<=ring_fault;writer_q<=writer_fault;reduce_q<=reduce_fault;
   arg_q<=arg_fault;tkm_q<=tkm_fault;argcap_q<=arg_capture_slot;tkmstart_q<=tkm_start;cap_q<=capture_fault;
   sel_q<=select_fault;unav_q<=unavailable_fault;lk_q<=link_abort;tdel_q<=tkm_del_slot;tdest_q<=tkm_dest_v;
  end
 wire [7:0] target_eff=(tgt_q==(8'd52+{6'd0,qid_q}))?8'd52:8'd0;
 ot_hgi_coll_static_program_target_s128 #(.TARGET(8'd52),.ASSEMBLY_PIPE(1)) u_program(
  .clk(clk),.rst_n(rst_q),.cfg_v(cv_q),.cfg_target(target_eff),
  .cfg_addr(addr_q),.cfg_lookup_addr(cfg_lookup_addr),.cfg_data(data_q),.desc_v(dv_q),.desc_base(base_q),
  .desc_limit(limit_q),.desc_loops(loops_q),.launch_v(lv_q),
  .program_active(act_q),.issuer_busy(ibusy_q),.issuer_fault(ifault_q),
  .issuer_uop_v(iuv_q),.issuer_uop_pc(iupc_q),
  .issuer_cfg(issuer_cfg),.issuer_start(issuer_start),.issuer_start_pc(issuer_start_pc),
  .configured(configured),.init_busy(init_busy),.fault(program_fault));
 wire noengine_arg=(SOLO==0)&&argcap_q;
 wire noengine_tkm=(SOLO==0)&&(tkmstart_q || (|tdest_q) || (|tdel_q));
 wire [2:0] link3;
 for(genvar k=0;k<3;k=k+1)begin:g_l3
  if(k<NPT)begin:p assign link3[k]=lk_q[k]; end else begin:z assign link3[k]=1'b0; end
 end
 wire [15:0] cause_now;
 assign cause_now[0]=program_fault;
 assign cause_now[1]=ifault_q;
 assign cause_now[2]=prot_q;
`ifdef OT_COLL_V5_MUT_CAUSE_SWAP
 assign cause_now[3]=|sel_q;
 assign cause_now[4]=|cap_q;
`else
 assign cause_now[3]=|cap_q;
 assign cause_now[4]=|sel_q;
`endif
 assign cause_now[5]=|unav_q;
`ifdef OT_COLL_V5_MUT_DROP_LINK
 assign cause_now[8:6]=3'b000;
`else
 assign cause_now[8:6]=link3;
`endif
 assign cause_now[9]=ring_q;
 assign cause_now[10]=writer_q;
 assign cause_now[11]=reduce_q;
 assign cause_now[12]=(SOLO!=0)?arg_q:noengine_arg;
`ifdef OT_COLL_V5_MUT_DROP_TKM
 assign cause_now[13]=(SOLO!=0)?tkm_q:1'b0;
`else
 assign cause_now[13]=(SOLO!=0)?tkm_q:noengine_tkm;
`endif
 assign cause_now[15:14]=2'b00;
 always @(posedge clk or negedge rst_q)
  if(!rst_q)begin fault<=1'b0;fault_cause<=16'd0;end
  else begin fault<=fault | (|cause_now);fault_cause<=fault_cause | cause_now;end
endmodule
`default_nettype wire
