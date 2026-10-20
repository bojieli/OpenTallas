`timescale 1ns/1ps
// QW-N59-4 (10-19) HARDENED SPLIT of qfd_native59_dv_service_r1 (SAFE 2, ROOTS 1, RST_FOREST 1; NU / MCTX / EMB_RELAY as
// the r1 block).  Why: the one-root safe4 / safe4b gates (ot-agidock128, 10-19 20:59) built CTS but measured pin-flop
// TT 633..777 / FF 516..643 (spread 145 / 127 > 80), SS setup -635 ps after repair at u_qseat.select_q (owner_n -> beat
// mux -> select) and a 10,330 s hold repair (17.6k buffers): 24k flops on one root spread at 10 % std-cell density over
// the 518.4 x 648 macro-bound slot (average sink wire 585 um).  The split puts the Q-seat SRAM bank and the service in
// two HARD children, each with its own centre-fed root, and the parent is a landed parent (tools/landed_parent/lp.py).
//
//   qfd_native59_qbank  face registers (every port, S face) + the 8 Q-seat SRAMs (qfd_native59_qseat_sram function) in
//                       16 LANE SLICES (slice l = the 32 seats {16 b + l}: its scatter replica, owner / seen state, read
//                       select) + qctx / dup / range checks.  Every output is a flop: qb_* = the flat block's
//                       combinational Q value three edges earlier; dd_o / lcv_o / stage_o = three-edge relays.
//   qfd_native59_svc    everything else (command context, formatter, x3, static services, codecs, dr landing, embedding,
//                       dr_o), the same RTL text as qfd_native59_dv_service with the Q bank replaced by the qb_* inputs.
//   qfd_native59_split_flat  wires-only parent (lp.py input): u_qb + u_svc.
// EDGE CONTRACT of the flat split vs qfd_native59_dv_service_r1 (lockstep: rtl/test/qwen_split/run_native59_split_bench.sh):
//   bank ports (dd_i, layer_context_v, command_stage, q_slot, q_slot_beat) at the r1 edge (offset 0);
//   every other input port presented THREE edges later than at r1, every output THREE edges later.  (v2, QW-N59-4 22:55:
//   the bank lands every port in ONE face register stage at its S face and runs its whole Q-seat section one edge behind
//   it (+1); v3 23:55: two registered output stages (lane-side partials, then the N-face reductions / flops) (+2).)
//   => compiler: native59 is r1 with q_slot / q_slot_beat / dd_i / context THREE edges EARLIER relative to the rest of the
//   face (equivalently: every non-bank port +3 edges).  Q write -> Q read (Q-ready age) relation unchanged (both bank).
//   The landed parent (lp.py) adds E + 1 = 3 more edges on every service port (record: results/arch/landed_parent_1018/
//   qfd_native59_split_flat): +6 in all.  Reset: both children release on the same edge (the service's view: one edge earlier);
//   the static calendar has no event within 8 edges of reset release, so the offset is unobservable (bench idle window).
// Static schedule only: no ready / credit; every fault stays a sticky fault.

// ----------------------------------------------------------------------------------------------------------------------
// One LANE SLICE of the Q-seat store (v2): the 32 seats e = 16 b + L (b = 0..31) of lane L.  Exact function of the
// corresponding seats of qfd_native59_qseat_sram (REPLICATE 1): owner / seen state, write hits from this slice's scatter
// replica, and the read select of lane L computed from the REGISTERED owner (one-hot beat AND-OR) with the same-edge write
// override computed locally from the replica ({rb, L} compare) -- owner_n[16 rb + L] without the 512-seat cone (v1 / safe4
// worst path: replica -> 512 seat hits -> owner_n -> beat mux -> select, 2,076 ps placed).
module qfd_native59_qlane #(parameter integer L=0,MUT=0)(
 input wire ck,rst_n,
 input wire[71:0]elem,input wire[7:0]valid,input wire seen_clear,     // this slice's scatter replica (valid has !begin)
 input wire read_v,input wire[31:0]read_oh,input wire[4:0]read_beat,   // kept copies for this slice
 output reg[7:0]select_q,                                              // writer select of lane L (registered on read_v)
 output wire seen_rd,                                                  // qseen_n of seat (read_beat, L): the full check
 output wire all_seen,output wire dup                                  // &qseen (32 seats); any dup / double hit
);
 reg[2:0]owner[0:31];reg[31:0]seen;
 wire[31:0]seen_n,dupv;
 genvar b,w;
 generate for(b=0;b<32;b=b+1)begin:g_seat
  wire[7:0]hit;
  for(w=0;w<8;w=w+1)begin:g_hit
   assign hit[w]=valid[w]&&(elem[9*w+:9]==9'(16*b+L));
  end
  always @(posedge ck)owner[b]<=hit[7]?3'd7:hit[6]?3'd6:hit[5]?3'd5:hit[4]?3'd4:hit[3]?3'd3:hit[2]?3'd2:hit[1]?3'd1:hit[0]?3'd0:owner[b];
  assign seen_n[b]=seen[b]|(|hit);
  assign dupv[b]=(seen[b]&&(|hit))||(|(hit&(hit-8'd1)));
 end endgenerate
 always @(posedge ck or negedge rst_n)
  if(!rst_n)seen<=0;
  else if(seen_clear)seen<=0;
  else seen<=seen_n;
 // read select: registered owner of seat (rb, L) or the same-edge writer (highest lane wins, as owner_n)
 wire[2:0]oreg;wire srd;
 wire[2:0]ot[0:32];wire[32:0]st;assign ot[0]=3'd0;assign st[0]=1'b0;
 generate for(b=0;b<32;b=b+1)begin:g_rd
  assign ot[b+1]=ot[b]|({3{read_oh[b]}}&owner[b]);
  assign st[b+1]=st[b]|(read_oh[b]&seen[b]);
 end endgenerate
 assign oreg=ot[32];assign srd=st[32];
 wire[7:0]m;
 generate for(w=0;w<8;w=w+1)begin:g_m
  assign m[w]=valid[w]&&(elem[9*w+:9]=={read_beat,4'(L)});
 end endgenerate
 wire[2:0]onew=m[7]?3'd7:m[6]?3'd6:m[5]?3'd5:m[4]?3'd4:m[3]?3'd3:m[2]?3'd2:m[1]?3'd1:m[0]?3'd0:oreg;
 generate for(w=0;w<8;w=w+1)begin:g_sel
  always @(posedge ck)if(read_v)select_q[w]<=onew==3'((MUT==7)?((w+1)%8):w);
 end endgenerate
 assign seen_rd=srd|(|m);
 assign all_seen=&seen;
 assign dup=|dupv;
endmodule

// ----------------------------------------------------------------------------------------------------------------------
// Q-seat store (v2): 16 lane slices + the 8 masked-writer SRAMs + the read gather (function of qfd_native59_qseat_sram).
module qfd_native59_qseat_lanes #(parameter integer MUT=0)(
 input wire ck,rst_n,clear,
 input wire[7:0]write_v,input wire[71:0]write_element,input wire[255:0]write_data,
 input wire[1151:0]elem_l,input wire[127:0]valid_l,input wire[15:0]seen_clear_l,   // per lane slice replicas
 input wire[15:0]read_v_l,input wire[511:0]read_oh_l,input wire[79:0]read_beat_l,   // per lane slice read copies
 input wire[7:0]read_v_m,input wire[39:0]read_beat_m,input wire[39:0]bypass_beat_c,
 output wire[511:0]read_data,output wire[15:0]seen_rd_l,output wire[15:0]all_seen_l,output wire[15:0]dup_l
);
 wire[127:0]select_q;
 genvar l,w;
 generate for(l=0;l<16;l=l+1)begin:g_lane
  qfd_native59_qlane #(.L(l),.MUT(MUT)) u_lane(.ck(ck),.rst_n(rst_n),.elem(elem_l[72*l+:72]),.valid(valid_l[8*l+:8]),
   .seen_clear(seen_clear_l[l]),.read_v(read_v_l[l]),.read_oh(read_oh_l[32*l+:32]),.read_beat(read_beat_l[5*l+:5]),
   .select_q(select_q[8*l+:8]),.seen_rd(seen_rd_l[l]),.all_seen(all_seen_l[l]),.dup(dup_l[l]));
 end endgenerate
 wire[511:0]bank_data[0:7];
 reg[7:0]bypass_v;reg[31:0]bypass_lane;reg[255:0]bypass_data;
 always @(posedge ck)begin
  bypass_data<=write_data;
  for(integer k=0;k<8;k=k+1)begin
   bypass_v[k]<=write_v[k]&&!clear&&(write_element[9*k+4+:5]==bypass_beat_c[5*k+:5]);
   bypass_lane[4*k+:4]<=write_element[9*k+:4];
  end
 end
 generate for(w=0;w<8;w=w+1)begin:g_writer
  wire[511:0]mask;
  for(l=0;l<16;l=l+1)begin:g_mask
   assign mask[32*l+:32]={32{write_element[9*w+:4]==4'(l)}};
  end
  ot_sram_1r1w_32x512_m1 u_mem(.clk(ck),.r_ce_in(read_v_m[w]),.r_addr_in(read_beat_m[5*w+:5]),.rd_out(bank_data[w]),
   .w_ce_in(write_v[w]&&!clear),.w_addr_in(write_element[9*w+4+:5]),
   .wd_in({16{write_data[32*w+:32]}}),.w_mask_in(mask));
 end endgenerate
 generate for(l=0;l<16;l=l+1)begin:g_read
  wire[31:0]tree[0:8];assign tree[0]=32'd0;
  for(w=0;w<8;w=w+1)begin:g_gather
   wire[31:0]d=(bypass_v[w]&&bypass_lane[4*w+:4]==4'(l))?bypass_data[32*w+:32]:bank_data[w][32*l+:32];
   assign tree[w+1]=tree[w]|({32{select_q[8*l+w]}}&d);
  end
  assign read_data[32*l+:32]=tree[8];
 end endgenerate
endmodule

// ----------------------------------------------------------------------------------------------------------------------
// Q-seat bank child (v2).  Face registers f_* capture every port on one edge at the S face; the SAFE 2 Q-seat section of
// qfd_native59_dv_service then runs on them exactly as it ran on the raw pins (one edge later), with its kept same-edge
// replicas now per LANE SLICE.  Outputs registered (see the file header).
// QB_MUT (split-only mutants, lockstep must FAIL): 1 qb_row leaves unregistered (one edge early), 2 dd_o relay one stage short.
module qfd_native59_qbank #(parameter integer MUT=0,QB_MUT=0)(
 input wire ck,rst_n,
 input wire[547:0]dd_i,input wire layer_context_v,input wire[5:0]command_stage,
 input wire q_slot,input wire[4:0]q_slot_beat,
 output reg[547:0]dd_o,output reg lcv_o,output reg[5:0]stage_o,
 output reg qb_v,output reg[4:0]qb_beat,output wire[511:0]qb_row,output reg qb_full,output reg qb_committed,output reg qb_bad
);
 // reset copy forest (kept; ot_rst_copies <= 32 loads each): pin 472 + read copies ~700 + relays 7, seen 512 + controls
 (* keep = "true" *) reg[39:0]rst_cp_bp;(* keep = "true" *) reg[19:0]rst_cp_bs;
 always @(posedge ck or negedge rst_n)
  if(!rst_n)begin rst_cp_bp<='0;rst_cp_bs<='0;end
  else begin rst_cp_bp<='1;rst_cp_bs<='1;end
 wire rst_pin=rst_cp_bp[0],rst_top=rst_cp_bs[0];
 // ---------------------------------------------------------------- face registers (the only flops on the input pins)
 // NO reset on the face registers: they stand for the raw pins, which the flat block's kept replicas sample on every edge
 // (also in reset); the p_* stage below carries the flat block's pin-register reset.
 reg[547:0]f_dd;reg f_lcv;reg[5:0]f_stage;reg f_qs;reg[4:0]f_qb;
 always @(posedge ck)begin f_dd<=dd_i;f_lcv<=layer_context_v;f_stage<=command_stage;f_qs<=q_slot;f_qb<=q_slot_beat;end
 // relays to the service: face register + one more stage (two edges)
 // relays to the service: face register + two more stages (three edges, as every v3 bank output)
 reg[547:0]dd_m;reg lcv_m;reg[5:0]stage_m;
 always @(posedge ck)dd_m<=f_dd;
 generate if(QB_MUT!=2)begin:g_relay
  always @(posedge ck)dd_o<=dd_m;
 end else begin:g_m2
  always @*dd_o=dd_m;
 end endgenerate
 always @(posedge ck or negedge rst_pin)
  if(!rst_pin)begin lcv_m<=0;stage_m<=0;lcv_o<=0;stage_o<=0;end
  else begin lcv_m<=f_lcv;stage_m<=f_stage;lcv_o<=lcv_m;stage_o<=stage_m;end
 // ---------------------------------------------------------------- the flat block's Q-seat section (SAFE 2), on f_*
 reg[547:89]p_dd;reg p_lcv;reg[5:0]p_stage;reg p_qs;reg[4:0]p_qb;
 always @(posedge ck or negedge rst_pin)
  if(!rst_pin)begin p_dd<=0;p_lcv<=0;p_stage<=0;p_qs<=0;p_qb<=0;end
  else begin p_dd<=f_dd[547:89];p_lcv<=f_lcv;p_stage<=f_stage;p_qs<=f_qs;p_qb<=f_qb;end
 // kept per-slice copies, captured on the SAME edge as p_* (identical registers)
 (* keep = "true" *) reg[71:0]qe_rep[0:15];(* keep = "true" *) reg[7:0]qm_rep[0:15];
 (* keep = "true" *) reg[2:0]qd_rep[0:15];(* keep = "true" *) reg[6:0]qc_rep[0:15];
 (* keep = "true" *) reg[15:0]rv_l;(* keep = "true" *) reg[511:0]roh_l;(* keep = "true" *) reg[79:0]rb_l;
 (* keep = "true" *) reg[7:0]rv_m;(* keep = "true" *) reg[39:0]rb_m;(* keep = "true" *) reg[39:0]bb_c;
 genvar gr,gl;
 generate for(gr=0;gr<16;gr=gr+1)begin:g_seg
  always @(posedge ck)begin
   qc_rep[gr]<={f_lcv,f_stage};
   qd_rep[gr]<=f_dd[547:545];qm_rep[gr]<=f_dd[544:537];
   for(integer lane=0;lane<8;lane=lane+1)
    qe_rep[gr][9*lane+:9]<=f_dd[345+24*lane+:9]^9'(MUT==1);
  end
 end endgenerate
 always @(posedge ck or negedge rst_pin)
  if(!rst_pin)begin rv_l<=0;roh_l<=0;rb_l<=0;rv_m<=0;rb_m<=0;bb_c<=0;end
  else begin
   rv_l<={16{f_qs}};rv_m<={8{f_qs}};rb_m<={8{f_qb}};bb_c<={8{f_qb}};rb_l<={16{f_qb}};
   for(integer ci=0;ci<16;ci=ci+1)roh_l[32*ci+:32]<=32'd1<<f_qb;
  end
 wire dd_v=p_dd[547];wire[1:0]dd_kind=p_dd[546:545];wire[7:0]dd_mask=p_dd[544:537];
 wire dd_q=dd_v&&dd_kind==2'd0;
 wire begin_slot=p_lcv&&p_stage>=1&&p_stage<=36;
 wire[71:0]qe_all;wire[7:0]qhit_any,qhi_bad;
 wire[1151:0]elem_l;wire[127:0]valid_l;wire[15:0]clr_l;
 generate for(gr=0;gr<16;gr=gr+1)begin:g_bus
  wire qb=qc_rep[gr][6]&&qc_rep[gr][5:0]>=1&&qc_rep[gr][5:0]<=36;
  assign elem_l[72*gr+:72]=qe_rep[gr];
  assign valid_l[8*gr+:8]={8{qd_rep[gr]==3'b100&&!qb}}&qm_rep[gr];
  assign clr_l[gr]=qb;
 end endgenerate
 generate for(gl=0;gl<8;gl=gl+1)begin:g_qlane
  assign qe_all[9*gl+:9]=p_dd[345+24*gl+:9]^((MUT==1)?9'd1:9'd0);
  assign qhit_any[gl]=dd_q&&dd_mask[gl];
  assign qhi_bad[gl]=qhit_any[gl]&&(|p_dd[345+24*gl+9+:15]);
 end endgenerate
 reg qctx;
 always @(posedge ck or negedge rst_top)
  if(!rst_top)qctx<=0;
  else if(begin_slot)qctx<=1;
 wire[511:0]qrow;wire[15:0]seen_rd_l,all_seen_l,dup_l;
 qfd_native59_qseat_lanes #(.MUT(MUT)) u_qseat(
  .ck(ck),.rst_n(rst_top),.clear(begin_slot),.write_v(qhit_any),.write_element(qe_all),.write_data(p_dd[344:89]),
  .elem_l(elem_l),.valid_l(valid_l),.seen_clear_l(clr_l),.read_v_l(rv_l),.read_oh_l(roh_l),.read_beat_l(rb_l),
  .read_v_m(rv_m),.read_beat_m(rb_m),.bypass_beat_c(bb_c),
  .read_data(qrow),.seen_rd_l(seen_rd_l),.all_seen_l(all_seen_l),.dup_l(dup_l));
 reg q_read_valid;reg[4:0]q_read_beat;
 always @(posedge ck or negedge rst_pin)
  if(!rst_pin)begin q_read_valid<=0;q_read_beat<=0;end
  else begin q_read_valid<=p_qs;q_read_beat<=p_qb;end
 // ---------------------------------------------------------------- output pipeline (v3: two registered stages)
 // stage A, beside the lane slices / the gather: q row, per-slice reductions, read valid / beat, begin
 // stage B, at the N face: the final 16-way reductions and the output flops.  Every output = the flat block's value of
 // the corresponding edge, one edge later than v2 (uniform: the service runs three edges behind the bank ports).
 reg[511:0]qrow_a;reg[15:0]sr_a,as_a,dup_a;reg beg_a,qctx_a,qhi_a,qv_a;reg[4:0]qbt_a;
 always @(posedge ck)begin qrow_a<=qrow;sr_a<=seen_rd_l;beg_a<=begin_slot;end
 always @(posedge ck or negedge rst_top)
  if(!rst_top)begin as_a<=0;dup_a<=0;qctx_a<=0;qhi_a<=0;qv_a<=0;qbt_a<=0;end
  else begin as_a<=all_seen_l;dup_a<=dup_l;qctx_a<=qctx;qhi_a<=|qhi_bad;qv_a<=q_read_valid;qbt_a<=q_read_beat;end
 reg full_q;   // the flat block's full_q (seats of the read beat all seen, not on a begin edge), one edge later
 always @(posedge ck)full_q<=!beg_a&&(&sr_a);
 reg[511:0]qrow_r;
 always @(posedge ck)qrow_r<=qrow_a;
 assign qb_row=(QB_MUT==1)?qrow_a:qrow_r;
 reg qv_b;reg[4:0]qbt_b;
 always @(posedge ck or negedge rst_top)
  if(!rst_top)begin qv_b<=0;qbt_b<=0;qb_v<=0;qb_beat<=0;qb_full<=0;qb_committed<=0;qb_bad<=0;end
  else begin
   qv_b<=qv_a;qbt_b<=qbt_a;qb_v<=qv_b;qb_beat<=qbt_b;qb_full<=full_q;
   qb_committed<=qctx_a&&(&as_a);
   qb_bad<=qhi_a||(|dup_a);
  end
 initial if(MUT!=0&&MUT!=1&&MUT!=7)$fatal(1,"qfd_native59_qbank: MUT %0d (bank mutants 1 Q lane packing, 7 owner)",MUT);
endmodule
