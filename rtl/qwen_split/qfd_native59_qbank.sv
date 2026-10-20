`timescale 1ns/1ps
// QW-N59-4 (10-19) HARDENED SPLIT of qfd_native59_dv_service_r1 (SAFE 2, ROOTS 1, RST_FOREST 1; NU / MCTX / EMB_RELAY as
// the r1 block).  Why: the one-root safe4 / safe4b gates (ot-agidock128, 10-19 20:59) built CTS but measured pin-flop
// TT 633..777 / FF 516..643 (spread 145 / 127 > 80), SS setup -635 ps after repair at u_qseat.select_q (owner_n -> beat
// mux -> select) and a 10,330 s hold repair (17.6k buffers): 24k flops on one root spread at 10 % std-cell density over
// the 518.4 x 648 macro-bound slot (average sink wire 585 um).  The split puts the Q-seat SRAM bank and the service in
// two HARD children, each with its own centre-fed root, and the parent is a landed parent (tools/landed_parent/lp.py).
//
//   qfd_native59_qbank  the 8 Q-seat SRAMs (qfd_native59_qseat_sram function, kept-copy read face) + scatter replicas +
//                       qseen / qctx / dup / range checks.  Faces: dd_i, layer_context_v, command_stage, q_slot,
//                       q_slot_beat (pin registers).  Every output is a flop: qb_* = the flat block's combinational Q value
//                       of the previous edge; dd_o / lcv_o / stage_o = one-edge relays of the raw dd_i / context pins.
//   qfd_native59_svc    everything else (command context, formatter, x3, static services, codecs, dr landing, embedding,
//                       dr_o), the same RTL text as qfd_native59_dv_service with the Q bank replaced by the qb_* inputs.
//   qfd_native59_split_flat  wires-only parent (lp.py input): u_qb + u_svc.
// EDGE CONTRACT of the flat split vs qfd_native59_dv_service_r1 (lockstep bench tb_qfd_native59_split_lockstep):
//   bank ports (dd_i, layer_context_v, command_stage, q_slot, q_slot_beat) at the r1 edge (offset 0);
//   every other input port presented ONE edge later than at r1, every output ONE edge later (the service runs one edge
//   behind the bank: the bank's registered outputs carry the r1 combinational value of the previous edge).
//   => compiler: native59 is r1 with q_slot / q_slot_beat / dd_i / context ONE edge EARLIER relative to the rest of the
//   face (equivalently: every non-bank port +1 edge).  Q write -> Q read (Q-ready age) relation unchanged (both bank).
//   The landed parent (lp.py) adds E + 1 = 3 more edges on every service port (record: results/arch/landed_parent_1018/
//   qfd_native59_split_flat).  Reset: both children release on the same edge (the service's view: one edge earlier);
//   the static calendar has no event within 8 edges of reset release, so the offset is unobservable (bench idle window).
// Static schedule only: no ready / credit; every fault stays a sticky fault.

// ----------------------------------------------------------------------------------------------------------------------
// Kept-copy read face of qfd_native59_qseat_sram (REPLICATE 1, REGIONAL 0): same state, same writes, same select and
// bypass function, but the read beat arrives as ONE-HOT kept copies (one per 4 lanes) so no register drives the 512-seat
// owner mux (safe4: select_q worst setup path), and the read enables / addresses are per-macro kept copies.
module qfd_native59_qseat_sram_k #(parameter integer MUT=0)(
 input wire ck,clear,
 input wire[7:0]write_v,input wire[71:0]write_element,input wire[255:0]write_data,
 input wire[1151:0]element_copies,input wire[127:0]valid_copies,
 input wire[15:0]read_v_c,input wire[127:0]read_oh_c,        // read_v per lane l; one-hot beat per lane group l/4
 input wire[7:0]read_v_m,input wire[39:0]read_beat_m,          // per macro w
 input wire[39:0]bypass_beat_c,                                // binary beat per writer k (bypass compare)
 output wire[511:0]read_data
);
 reg[2:0]owner[0:511];
 wire[2:0]owner_n[0:511];
 genvar e,w,l,b;
 generate for(e=0;e<512;e=e+1)begin:g_owner
  wire[7:0]hit;
  for(w=0;w<8;w=w+1)begin:g_hit
   assign hit[w]=valid_copies[8*(e/32)+w]&&(element_copies[72*(e/32)+9*w+:9]==9'(e));
  end
  assign owner_n[e]=hit[7]?3'd7:hit[6]?3'd6:hit[5]?3'd5:hit[4]?3'd4:
                     hit[3]?3'd3:hit[2]?3'd2:hit[1]?3'd1:hit[0]?3'd0:owner[e];
  always @(posedge ck)owner[e]<=owner_n[e];
 end endgenerate
 wire[511:0]bank_data[0:7];
 (* keep = "true" *) reg[127:0]select_q;
 reg[7:0]bypass_v;reg[31:0]bypass_lane;reg[255:0]bypass_data;
 always @(posedge ck)begin
  bypass_data<=write_data;
  for(integer k=0;k<8;k=k+1)begin
   bypass_v[k]<=write_v[k]&&!clear&&(write_element[9*k+4+:5]==bypass_beat_c[5*k+:5]);
   bypass_lane[4*k+:4]<=write_element[9*k+:4];
  end
 end
 generate for(l=0;l<16;l=l+1)begin:g_lane
  // owner_n[16 * beat + l] as a one-hot AND-OR (decoded constant-index slices)
  wire[2:0]ot[0:32];assign ot[0]=3'd0;
  for(b=0;b<32;b=b+1)begin:g_b
   assign ot[b+1]=ot[b]|({3{read_oh_c[32*(l/4)+b]}}&owner_n[16*b+l]);
  end
  for(w=0;w<8;w=w+1)begin:g_sel
   always @(posedge ck)if(read_v_c[l])select_q[8*l+w]<=ot[32]==3'((MUT==7)?((w+1)%8):w);
  end
 end endgenerate
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
// Q-seat bank child.  Body = the SAFE 2 Q-seat section of qfd_native59_dv_service (scatter replicas, qseen, full, dup /
// range checks, the 8-writer SRAM store) on its own pin registers; outputs registered (see the file header).
// QB_MUT (split-only mutants, lockstep must FAIL): 1 qb_row leaves unregistered (one edge early), 2 dd_o relay skipped.
module qfd_native59_qbank #(parameter integer MUT=0,QB_MUT=0)(
 input wire ck,rst_n,
 input wire[547:0]dd_i,input wire layer_context_v,input wire[5:0]command_stage,
 input wire q_slot,input wire[4:0]q_slot_beat,
 output reg[547:0]dd_o,output reg lcv_o,output reg[5:0]stage_o,
 output reg qb_v,output reg[4:0]qb_beat,output wire[511:0]qb_row,output reg qb_full,output reg qb_committed,output reg qb_bad
);
 // reset copy forest (kept; ot_rst_copies <= 32 loads each): pin registers 459+7+6, qseen 512 + qctx, controls
 (* keep = "true" *) reg[23:0]rst_cp_bp;(* keep = "true" *) reg[19:0]rst_cp_bs;
 always @(posedge ck or negedge rst_n)
  if(!rst_n)begin rst_cp_bp<='0;rst_cp_bs<='0;end
  else begin rst_cp_bp<='1;rst_cp_bs<='1;end
 wire rst_pin=rst_cp_bp[0],rst_top=rst_cp_bs[0];
 // pin registers (the bank uses dd_i[547:89]; [88:0] only travel in the relay)
 reg[547:89]p_dd;reg p_lcv;reg[5:0]p_stage;reg p_qs;reg[4:0]p_qb;
 always @(posedge ck or negedge rst_pin)
  if(!rst_pin)begin p_dd<=0;p_lcv<=0;p_stage<=0;p_qs<=0;p_qb<=0;end
  else begin p_dd<=dd_i[547:89];p_lcv<=layer_context_v;p_stage<=command_stage;p_qs<=q_slot;p_qb<=q_slot_beat;end
 // kept read-face copies, captured on the SAME edge as p_qs / p_qb (identical registers)
 (* keep = "true" *) reg[15:0]rv_c;(* keep = "true" *) reg[127:0]roh_c;
 (* keep = "true" *) reg[7:0]rv_m;(* keep = "true" *) reg[39:0]rb_m;(* keep = "true" *) reg[39:0]bb_c;
 (* keep = "true" *) reg[31:0]foh;    // one-hot beat for the full check
 integer ci;
 always @(posedge ck or negedge rst_pin)
  if(!rst_pin)begin rv_c<=0;roh_c<=0;rv_m<=0;rb_m<=0;bb_c<=0;foh<=0;end
  else begin
   rv_c<={16{q_slot}};rv_m<={8{q_slot}};rb_m<={8{q_slot_beat}};bb_c<={8{q_slot_beat}};
   for(ci=0;ci<4;ci=ci+1)roh_c[32*ci+:32]<=32'd1<<q_slot_beat;
   foh<=32'd1<<q_slot_beat;
  end
 // relays to the service (one edge; raw pins, kept: not merged with the pin registers)
 generate if(QB_MUT!=2)begin:g_relay
  always @(posedge ck)dd_o<=dd_i;
 end else begin:g_m2
  always @*dd_o=dd_i;
 end endgenerate
 always @(posedge ck or negedge rst_pin)
  if(!rst_pin)begin lcv_o<=0;stage_o<=0;end
  else begin lcv_o<=layer_context_v;stage_o<=command_stage;end
 // ---------------------------------------------------------------- the flat block's Q-seat section (SAFE 2)
 wire dd_v=p_dd[547];wire[1:0]dd_kind=p_dd[546:545];wire[7:0]dd_mask=p_dd[544:537];
 wire dd_q=dd_v&&dd_kind==2'd0;
 wire begin_slot=p_lcv&&p_stage>=1&&p_stage<=36;
 reg[511:0]qseen;reg qctx;
 wire[511:0]qseen_n,qdup;
 wire[71:0]qe_all;wire[7:0]qhit_any,qhi_bad;
 (* keep = "true" *) reg[71:0]qe_rep[0:15];
 wire[7:0]qh_rep[0:15];wire[15:0]qb_rep;
 (* keep = "true" *) reg[7:0]qm_rep[0:15];
 (* keep = "true" *) reg[2:0]qd_rep[0:15];
 (* keep = "true" *) reg[6:0]qc_rep[0:15];
 genvar gr,gl,ge;
 generate for(gr=0;gr<16;gr=gr+1)begin:g_seg
  always @(posedge ck)begin
   qc_rep[gr]<={layer_context_v,command_stage};
   qd_rep[gr]<=dd_i[547:545];qm_rep[gr]<=dd_i[544:537];
   for(integer lane=0;lane<8;lane=lane+1)
    qe_rep[gr][9*lane+:9]<=dd_i[345+24*lane+:9]^9'(MUT==1);
  end
  assign qb_rep[gr]=qc_rep[gr][6]&&qc_rep[gr][5:0]>=1&&qc_rep[gr][5:0]<=36;
  assign qh_rep[gr]={8{qd_rep[gr]==3'b100&&!qb_rep[gr]}}&qm_rep[gr];
  always @(posedge ck or negedge rst_top)
   if(!rst_top)qseen[32*gr+:32]<=0;
   else if(qb_rep[gr])qseen[32*gr+:32]<=0;
   else qseen[32*gr+:32]<=qseen_n[32*gr+:32];
 end endgenerate
 wire[1151:0]qe_copies;wire[127:0]qh_copies;
 generate for(gr=0;gr<16;gr=gr+1)begin:g_scatter_bus
  assign qe_copies[72*gr+:72]=qe_rep[gr];assign qh_copies[8*gr+:8]=qh_rep[gr];
 end endgenerate
 generate
  for(gl=0;gl<8;gl=gl+1)begin:g_qlane
   assign qe_all[9*gl+:9]=p_dd[345+24*gl+:9]^((MUT==1)?9'd1:9'd0);
   assign qhit_any[gl]=dd_q&&dd_mask[gl];
   assign qhi_bad[gl]=qhit_any[gl]&&(|p_dd[345+24*gl+9+:15]);
  end
  for(ge=0;ge<512;ge=ge+1)begin:g_qseat
   wire[7:0]hit;
   for(gl=0;gl<8;gl=gl+1)begin:g_h
    assign hit[gl]=qh_rep[ge/32][gl]&&(qe_rep[ge/32][9*gl+:9]==9'(ge));
   end
   assign qseen_n[ge]=qseen[ge]|(|hit);
   assign qdup[ge]=(qseen[ge]&&(|hit))||(|(hit&(hit-8'd1)));
  end
 endgenerate
 always @(posedge ck or negedge rst_top)
  if(!rst_top)qctx<=0;
  else if(begin_slot)qctx<=1;
 wire[511:0]qrow;
 qfd_native59_qseat_sram_k #(.MUT(MUT)) u_qseat(
  .ck(ck),.clear(begin_slot),.write_v(qhit_any),.write_element(qe_all),.write_data(p_dd[344:89]),
  .element_copies(qe_copies),.valid_copies(qh_copies),
  .read_v_c(rv_c),.read_oh_c(roh_c),.read_v_m(rv_m),.read_beat_m(rb_m),.bypass_beat_c(bb_c),.read_data(qrow));
 // full: the 16 seats of the read beat, one-hot (the flat block's full_q, registered on the read edge)
 wire[31:0]bfull;
 genvar gb;
 generate for(gb=0;gb<32;gb=gb+1)begin:g_full
  assign bfull[gb]=foh[gb]&&(&qseen_n[16*gb+:16]);
 end endgenerate
 reg full_q;
 always @(posedge ck)full_q<=!begin_slot&&(|bfull);
 reg q_read_valid;reg[4:0]q_read_beat;
 always @(posedge ck or negedge rst_pin)
  if(!rst_pin)begin q_read_valid<=0;q_read_beat<=0;end
  else begin q_read_valid<=p_qs;q_read_beat<=p_qb;end
 // ---------------------------------------------------------------- registered outputs
 reg[511:0]qrow_r;
 always @(posedge ck)qrow_r<=qrow;
 assign qb_row=(QB_MUT==1)?qrow:qrow_r;
 always @(posedge ck or negedge rst_top)
  if(!rst_top)begin qb_v<=0;qb_beat<=0;qb_full<=0;qb_committed<=0;qb_bad<=0;end
  else begin
   qb_v<=q_read_valid;qb_beat<=q_read_beat;qb_full<=full_q;
   qb_committed<=qctx&&(&qseen);
   qb_bad<=(|qhi_bad)||(|qdup);
  end
 initial if(MUT!=0&&MUT!=1&&MUT!=7)$fatal(1,"qfd_native59_qbank: MUT %0d (bank mutants 1 Q lane packing, 7 owner)",MUT);
endmodule

