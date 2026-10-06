`timescale 1ns/1ps
// REGISTERED_BOUNDARY frame station (additive successor of
// ot_hbm_native_frame_station MODE1; that module and its gates are unchanged).
// Same function: one held full frame {data2063,frame73,owner192} multicast to
// NO branches, NO protected reverse receipts, release only after every branch
// ACKed with the exact owner and frame, protected release receipt.
//
// Boundary contract (die integration): every input pin is captured by a flop
// with no logic in front of it; every output pin is driven by a flop with no
// logic behind it. Die-level paths are pin-to-pin wire only.
//  * forward link (in_v/in_r, out_v/out_r): valid is HELD until the sender
//    learns (one edge later, from its captured ready) that it was taken;
//    ready is PULSED (never high on two consecutive edges), so the held valid
//    can never be taken twice. A level-ready partner (an SM) needs a one-flop
//    duplicate mask at its side (the chain models it).
//  * reverse receipt (release_v/release_r): release_held=0 (readyless inter-
//    station seat) presents one-edge pulses, retried on alternate edges until
//    learned; release_held=1 (parent backpressure) holds valid like out_v.
//  * ACK_v is readyless as before: one ACK per branch per transaction into a
//    reserved protected seat; an ACK while the seat cannot take it is a fault.
// Registered veto: every bank presents data two edges old together with the
// verdict about exactly that data (ot_hbm_w2_protected_bank_veto_on); output
// flops add one more edge to both. Station control outside W6 words is dual
// rail or kept copies checked against each other; any disagreement is fatal.
module ot_hbm_native_frame_station_rb #(parameter integer ENABLE=0,NO=3)(
 input wire clk_sm,por_n,release_held,
 input wire in_v,output wire in_r,input wire [2062:0] in_data,
 input wire [191:0] in_owner,input wire [72:0] in_frame,
 output wire [NO-1:0] out_v,input wire [NO-1:0] out_r,
 output wire [NO*2063-1:0] out_data,output wire [NO*192-1:0] out_owner,
 output wire [NO*73-1:0] out_frame,
 input wire [NO-1:0] ACK_v,input wire [NO*192-1:0] ACK_owner,
 input wire [NO*73-1:0] ACK_frame,
 output wire release_v,input wire release_r,
 output wire [191:0] release_owner,output wire [72:0] release_frame,
 output wire fclk_o,drained,paused,fault
);
 import ot_gpu_w6_secded_pkg::*;
 generate if(!ENABLE)begin:disabled
  assign in_r=0;assign out_v=0;assign out_data=0;assign out_owner=0;assign out_frame=0;
  assign release_v=0;assign release_owner=0;assign release_frame=0;
  assign fclk_o=0;assign drained=1;assign paused=0;assign fault=0;
 end else begin:held
  initial if(NO!=2&&NO!=3)$fatal(1,"actual quarter station NO2 terminal/NO3 2SM+next only");
  localparam integer PW=2328,PN=37,RW=265;
  localparam [3:0] ALL=(4'b1111>>(4-NO));
  // Forwarded clock: four real kept inversions, as the original station.
  wire c1,c2,c3;
  ot_fwd_clk_inv u_clk0(.a(clk_sm),.y(c1));
  ot_fwd_clk_inv u_clk1(.a(c1),.y(c2));
  ot_fwd_clk_inv u_clk2(.a(c2),.y(c3));
  ot_fwd_clk_inv u_clk3(.a(c3),.y(fclk_o));
  // Cold POR: asynchronous assert, synchronous release (two kept stages).
  wire [1:0] rs;
  ot_hbm_w2_keep_reg #(.W(1)) u_rs0(.clk(clk_sm),.rst_n(por_n),.d(1'b1),.q(rs[0]));
  ot_hbm_w2_keep_reg #(.W(1)) u_rs1(.clk(clk_sm),.rst_n(por_n),.d(rs[0]),.q(rs[1]));
  wire rst_n=rs[1];
  // ---------------- input pin capture (no logic before the flop) ----------
  reg [PW-1:0] id_p;reg [NO-1:0] or_p,ackv_p;reg [NO*192-1:0] acko_p;
  reg [NO*73-1:0] ackf_p;reg rr_p,held_p;
  wire [PN-1:0] ivc;wire iv_p;
  always @(posedge clk_sm)begin
   id_p<={in_owner,in_frame,in_data};or_p<=out_r;ackv_p<=ACK_v;
   acko_p<=ACK_owner;ackf_p<=ACK_frame;rr_p<=release_r;held_p<=release_held;
  end
  ot_hbm_w2_keep_reg #(.W(1)) u_iv(.clk(clk_sm),.rst_n(rst_n),.d(in_v),.q(iv_p));
  // ---------------- protected state ----------------------------------------
  wire fault_any;
  wire [PN*72-1:0] E;wire E_v,E_bad;
  wire P_in_r,P_out_v,P_empty,P_fault,P_in_v,P_out_r;wire [PW-1:0] P_d;
  wire [NO-1:0] A_in_r,A_out_v,A_empty,A_fault,A_in_v;wire [NO*192-1:0] A_d;
  wire C_normal,C_fault,C_rep,C_load;wire [63:0] C_q,C_next;
  wire G_normal,G_fault,G_rep;
  wire R_in_r,R_out_v,R_empty,R_fault,R_in_v,R_out_r;wire [RW-1:0] R_d;
  wire [191:0] owner0=P_d[2136+:192];wire [72:0] frame0=P_d[2063+:73];
  wire active=C_q[0];wire [3:0] sent=C_q[4:1],acked=C_q[8:5];
  // ---------------- forward input: pulsed in_r, encoded seat E -------------
  // gr drives in_r (dual rail); grc are kept copies of the previous gr, one
  // per seat word, so the seat write needs no block-wide enable.
  wire gr,gr_bad,take;wire [PN-1:0] grc;
  wire gr_d;
  assign take=iv_p&&gr_d;
  wire gr_next=!gr&&!take&&!E_v&&!fault_any;
  ot_hbm_w2_dr_reg #(.W(1)) u_gr(.clk(clk_sm),.rst_n(rst_n),.d(gr_next),.q(gr),.bad(gr_bad));
  ot_hbm_w2_keep_reg #(.W(1)) u_grd(.clk(clk_sm),.rst_n(rst_n),.d(gr),.q(gr_d));
  wire [PN*64-1:0] raw_in={{(PN*64-PW-1){1'b0}},1'b1,id_p};
  reg [71:0] Ew[0:PN-1];
  for(genvar w=0;w<PN;w=w+1)begin:seat
   ot_hbm_w2_keep_reg #(.W(2)) u_c(.clk(clk_sm),.rst_n(rst_n),.d({in_v,gr}),.q({ivc[w],grc[w]}));
   always @(posedge clk_sm)if(ivc[w]&&grc[w])Ew[w]<=encode64(raw_in[w*64+:64]);
   assign E[w*72+:72]=Ew[w];
  end
  wire copy_bad=(|(ivc^{PN{iv_p}}))||(|(grc^{PN{gr_d}}));
  // E occupancy (dual rail). P commits E two edges after taking it (PREP,
  // COMMIT); E is released only after that commit edge.
  wire P_take=P_in_r&&P_in_v;
  wire [1:0] cons;wire cons_bad;
  ot_hbm_w2_dr_reg #(.W(2)) u_cons(.clk(clk_sm),.rst_n(rst_n),.d({cons[0],P_take}),.q(cons),.bad(cons_bad));
  ot_hbm_w2_dr_reg #(.W(1)) u_ev(.clk(clk_sm),.rst_n(rst_n),.d((E_v||take)&&!cons[1]),.q(E_v),.bad(E_bad));
  // ---------------- payload cut P (37 words, distributed enables) ----------
  wire receipt_room=R_in_r;
  wire quiesce=!receipt_room||!G_normal||fault_any;
  wire receipt_capacity=&A_in_r;
  assign P_in_v=E_v&&!cons[0]&&!cons[1]&&!quiesce&&!fault_any&&receipt_capacity;
  ot_hbm_w2_protected_cut_veto_on #(.W(PW),.PREENC(0),.DIST(1)) u_payload(
   .clk(clk_sm),.por_n(rst_n),.in_v(P_in_v),.in_r(P_in_r),.in_d({PW{1'b0}}),.in_codes(E),
   .out_v(P_out_v),.out_r(P_out_r),.out_d(P_d),.empty(P_empty),.fault(P_fault));
  wire cv=P_out_v;
  // ---------------- learned transfers -----------------------------------
  wire [NO-1:0] ov,ov_d,pend,learned;wire ov_bad,pend_bad;
  assign learned=ov_d&or_p;
  wire [NO-1:0] sent_eff=sent|pend|learned;
  // ---------------- reverse receipt seats A -------------------------------
  wire [NO-1:0] frame_bad;
  wire ack_consume=C_normal&&cv&&active&&!P_fault;
  for(genvar t=0;t<NO;t=t+1)begin:receipts
   assign frame_bad[t]=ackv_p[t]&&(ackf_p[t*73+:73]!=frame0);
   assign A_in_v[t]=ackv_p[t]&&!fault_any&&!frame_bad[t];
   ot_hbm_w2_protected_cut_veto_on #(.W(192),.PREENC(1),.DIST(0)) u_ack(
    .clk(clk_sm),.por_n(rst_n),.in_v(A_in_v[t]),.in_r(A_in_r[t]),.in_d(acko_p[t*192+:192]),
    .in_codes({4*72{1'b0}}),.out_v(A_out_v[t]),.out_r(ack_consume),.out_d(A_d[t*192+:192]),
    .empty(A_empty[t]),.fault(A_fault[t]));
  end
  // Registered owner equalities (operands are static while they are used).
  reg [NO-1:0] seat_match,arr_bad;reg [NO-1:0] frame_bad_q;
  always @(posedge clk_sm or negedge rst_n)
   if(!rst_n)begin seat_match<=0;arr_bad<=0;frame_bad_q<=0;end
   else for(integer t=0;t<NO;t=t+1)begin
    seat_match[t]<=A_d[t*192+:192]==owner0;
    arr_bad[t]<=ackv_p[t]&&C_normal&&cv&&(acko_p[t*192+:192]!=owner0);
    frame_bad_q[t]<=frame_bad[t];
   end
  reg ack_bad;reg [3:0] ns,na;
  always @*begin
   ack_bad=0;ns=sent;na=acked;
   for(integer t=0;t<NO;t=t+1)begin
    if(learned[t]||pend[t])ns[t]=1;
    if(ackv_p[t]&&!A_in_r[t])ack_bad=1;
    if(C_normal&&cv)begin
     if(ackv_p[t]&&(!active||!sent_eff[t]||acked[t]))ack_bad=1;
     if(A_out_v[t])begin
      if(!active||!sent_eff[t]||acked[t]||!seat_match[t])ack_bad=1;
      else na[t]=1;
     end
    end
   end
  end
  // ---------------- permissions C, frame guard G, receipt R ----------------
  wire source_release_r=receipt_room&&G_normal&&!fault_any;
  wire release_all=C_normal&&cv&&active&&source_release_r&&((acked&ALL)==ALL);
  wire arm=C_normal&&cv&&!active&&!fault_any;
  assign C_next=release_all?64'b0:arm?64'b1:{55'b0,na,ns,active};
  assign C_load=C_normal&&(arm||release_all||ns!=sent||na!=acked);
  assign P_out_r=release_all&&!fault_any;
  wire illegal=ack_bad||(|arr_bad);
  reg illegal_q;
  always @(posedge clk_sm or negedge rst_n)if(!rst_n)illegal_q<=0;else illegal_q<=illegal;
  ot_hbm_w2_protected_bank_veto_on #(.WORDS(1),.STAGE(1),.DIST(0)) u_permissions(
   .clk(clk_sm),.por_n(rst_n),.load(C_load),.load_sel(1'b1),.fatal(illegal_q),
   .encoded_d(encode64(C_next)),.q(C_q),.normal(C_normal),.fault(C_fault),.repairing(C_rep));
  ot_hbm_w2_protected_bank_veto_on #(.WORDS(1),.STAGE(1),.DIST(0)) u_frame_guard(
   .clk(clk_sm),.por_n(rst_n),.load(1'b0),.load_sel(1'b0),.fatal(|frame_bad_q),
   .encoded_d(72'b0),.q(),.normal(G_normal),.fault(G_fault),.repairing(G_rep));
  assign R_in_v=release_all&&!fault_any;
  wire rv,rv_d,rel_pend,rel_learned;wire rv_bad,rp_bad;
  assign rel_learned=rv_d&&rr_p;
  assign R_out_r=rel_learned||rel_pend;
  ot_hbm_w2_protected_cut_veto_on #(.W(RW),.PREENC(1),.DIST(0)) u_receipt(
   .clk(clk_sm),.por_n(rst_n),.in_v(R_in_v),.in_r(R_in_r),.in_d({frame0,owner0}),
   .in_codes({5*72{1'b0}}),.out_v(R_out_v),.out_r(R_out_r),.out_d(R_d),
   .empty(R_empty),.fault(R_fault));
  // A learned release is recorded by R in the same edge when R is normal
  // (R_out_r&&valid loads); otherwise it is held pending (dual rail).
  ot_hbm_w2_dr_reg #(.W(1)) u_rpend(.clk(clk_sm),.rst_n(rst_n),
   .d((rel_pend||rel_learned)&&!(R_in_r&&R_out_v)),.q(rel_pend),.bad(rp_bad));
  ot_hbm_w2_dr_reg #(.W(NO)) u_pend(.clk(clk_sm),.rst_n(rst_n),
   .d((pend|learned)&{NO{!C_load}}),.q(pend),.bad(pend_bad));
  // ---------------- output flops ------------------------------------------
  wire [NO-1:0] ov_next;
  for(genvar t=0;t<NO;t=t+1)begin:offer
   assign ov_next[t]=C_normal&&cv&&active&&!fault_any&&!sent_eff[t];
  end
  ot_hbm_w2_dr_reg #(.W(NO)) u_ov(.clk(clk_sm),.rst_n(rst_n),.d(ov_next),.q(ov),.bad(ov_bad));
  ot_hbm_w2_keep_reg #(.W(NO)) u_ovd(.clk(clk_sm),.rst_n(rst_n),.d(ov),.q(ov_d));
  wire rv_next=R_out_v&&!fault_any&&!rel_learned&&!rel_pend&&(held_p||!rv);
  ot_hbm_w2_dr_reg #(.W(1)) u_rv(.clk(clk_sm),.rst_n(rst_n),.d(rv_next),.q(rv),.bad(rv_bad));
  ot_hbm_w2_keep_reg #(.W(1)) u_rvd(.clk(clk_sm),.rst_n(rst_n),.d(rv),.q(rv_d));
  // One kept launch register per output pin (never merged across branches).
  wire [NO*PW-1:0] out_q;wire [RW-1:0] rel_q;
  ot_hbm_w2_keep_dreg #(.W(RW)) u_relq(.clk(clk_sm),.d(R_d),.q(rel_q));
  for(genvar t=0;t<NO;t=t+1)begin:branch
   ot_hbm_w2_keep_dreg #(.W(PW)) u_outq(.clk(clk_sm),.d(P_d),.q(out_q[t*PW+:PW]));
   assign out_data[t*2063+:2063]=out_q[t*PW+:2063];
   assign out_frame[t*73+:73]=out_q[t*PW+2063+:73];
   assign out_owner[t*192+:192]=out_q[t*PW+2136+:192];
  end
  assign out_v=ov;assign in_r=gr;assign release_v=rv;
  assign release_owner=rel_q[191:0];assign release_frame=rel_q[264:192];
  // ---------------- fault / status ----------------------------------------
  wire dr_bad=gr_bad||copy_bad||cons_bad||E_bad||pend_bad||rp_bad||ov_bad||rv_bad;
  reg dr_bad_q;
  always @(posedge clk_sm or negedge rst_n)if(!rst_n)dr_bad_q<=0;else if(dr_bad)dr_bad_q<=1;
  assign fault_any=P_fault||(|A_fault)||C_fault||G_fault||R_fault||illegal_q||dr_bad_q;
  wire native_empty=P_empty&&!E_v&&(&A_empty)&&C_normal&&!active&&!(|pend);
  wire drained_next=native_empty&&R_empty&&!rel_pend&&G_normal&&!fault_any;
  wire paused_next=C_rep||(!P_fault&&!P_empty&&!cv)||(!(|A_fault)&&(|(~A_empty&~A_out_v)))||
   G_rep||(!R_empty&&!R_out_v&&!R_fault);
  reg fault_q,drained_q,paused_q;
  always @(posedge clk_sm or negedge rst_n)
   if(!rst_n)begin fault_q<=0;drained_q<=0;paused_q<=0;end
   else begin fault_q<=fault_any;drained_q<=drained_next;paused_q<=paused_next;end
  assign fault=fault_q;assign drained=drained_q;assign paused=paused_q;
 end endgenerate
endmodule
