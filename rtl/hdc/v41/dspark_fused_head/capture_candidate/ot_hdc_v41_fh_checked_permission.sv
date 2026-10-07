`timescale 1ns/1ps
// Native held endpoint repair. Local protection decides local capture; the
// full live fault only vetoes scalar publication, never a wide capture mux.
// Parent must accept the request only on request_checked_v, and retain its
// real checked reply until checked publication/consume. No backend fiction.
// MARGIN (default 0; margin-first 1): cold_n reaches every register through kept copies (+1 on
// assertion and release); the request/reply take reaches the banks through kept copies and each
// bank loads a twice-registered copy of its data (banks hold the packet two cycles later, still
// three cycles before the age-0 release). The quarantine stays the same-cycle OR of every bank's
// mismatch (fail closed at the grant); the two data registers carry each lane's payload to banks
// beside the guard, so that OR is local. No release cycle changes.
// FPIPE (default 0; needs MARGIN): registered fault aggregation for 1.2 GHz (head_m2 post-CTS -1987 ps:
// bank pair XNOR -> 129-bank OR -> endpoint fault -> warm ACK -> head index-write state, ~2.5 ns).
// Each bank launches its bad flag from a kept per-bank fault flop; the wide bank OR leaves the
// same-cycle endpoint fault and is carried only by the registered reduce (local 8 -> cluster 4 ->
// final), whose result now also vetoes the endpoint fault; request/reply release ages grow by one
// (6) so the grant still sees the loaded banks' check; the head ACK fields leave registers (+1).
// A bank corrupted after its check is quarantined four cycles later (sticky), never silently.
module ot_hdc_v41_fh_checked_permission #(parameter integer MARGIN=0, FPIPE=0) (
 input wire fast_clk,cold_n_in,
 input wire request_accept,request_warm,checked_reply_capture,published_reply_v,
 input wire [31:0] native_ordinal,input wire [46:0] request_owner,
 input wire [7:0] request_id,input wire [3:0] head_we,
 input wire [95:0] head_addr,input wire [63:0] head_mask,
 input wire [2047:0] head_data,
 input wire [ot_dsrom_vm_pkg::REP_BITS-1:0] checked_reply,
 input wire bounds_in,   // FPIPE>=2: the bounds check registered at the endpoint pin stage (else unused)
 input wire [ot_dsrom_vm_pkg::REQ_BITS-1:0] accepted_in, // FPIPE>=3: the normalized request, registered upstream
 output wire bounds_fault,endpoint_fault,
 output wire [ot_dsrom_vm_pkg::REQ_BITS-1:0] captured_request,captured_request_check,
 output wire [ot_dsrom_vm_pkg::REP_BITS-1:0] captured_reply,captured_reply_check,
 output wire request_checked_v,reply_checked_v,guard_busy,
 output wire head_ack_v,output wire [7:0] head_ack_id,
 output wire [23:0] head_ack_word,output wire [15:0] head_ack_mask
);
 import ot_dsrom_vm_pkg::*;
 localparam integer RB=(REQ_BITS+31)/32, PB=(REP_BITS+31)/32;
 localparam integer NCOLD=16;
 wire [NCOLD-1:0] cold_c;
 // FPIPE>=2: a second kept cold level, one copy per bank / per metadata group (+1 on assertion and release)
 localparam integer NC2=(REQ_BITS+31)/32+(REP_BITS+31)/32+9;
 wire [NC2-1:0] cold_b;
 for(genvar c=0;c<NC2;c=c+1) begin : g_cold2
  if(FPIPE>=2) begin : g_k
   ot_hdc_v41_fh_cold_copy u_cold2(.clk(fast_clk),.d(cold_c[c%NCOLD]),.q(cold_b[c]));
  end else begin : g_n
   assign cold_b[c]=cold_c[c%NCOLD];
  end
 end
 wire cold_n=FPIPE>=2?cold_b[NC2-1]:cold_c[0];
 wire [15:0] take_rc;
 wire [7:0] take_pc;
 for(genvar c=0;c<NCOLD;c=c+1) begin : g_cold
  if(MARGIN) begin : g_k
   ot_hdc_v41_fh_cold_copy u_cold(.clk(fast_clk),.d(cold_n_in),.q(cold_c[c]));
  end else begin : g_n
   assign cold_c[c]=cold_n_in;
  end
 end
 request_t accepted_input,source_packet,source_check;
 reply_t held_reply,held_check;
 reg [74:0] wa;reg [79:0] wm;reg [2559:0] wd;
 wire [3:0] bad_address;
 for(genvar g=0;g<4;g=g+1) begin : g_bounds
  assign bad_address[g]=head_we[g]&&(|head_addr[g*24+15+:9]);
 end
 assign bounds_fault=FPIPE>=2?bounds_in:(|bad_address);
 always @* begin
  wa=0;wm=0;wd=0;
  for(integer g=0;g<4;g=g+1) if(head_we[g]) begin
   wa[(g+1)*15+:15]=head_addr[g*24+:15];
   wm[(g+1)*16+:16]=head_mask[g*16+:16];
   for(integer l=0;l<16;l=l+1) if(head_mask[g*16+l])
    wd[(g+1)*512+l*32+:32]=head_data[g*512+l*32+:32];
  end
  accepted_input=FPIPE>=3?accepted_in:{native_ordinal,request_owner,2'b0,30'b0,{head_we,1'b0},wa,wd,wm};
 end
 (* keep=1,dont_touch=1 *) reg active,active_check,reply_active,reply_active_check;
 (* keep=1,dont_touch=1 *) reg [2:0] req_age,req_age_check,rep_age,rep_age_check;
 (* keep=1,dont_touch=1 *) reg warm,warm_check,sent,sent_check,protocol_fault,protocol_fault_check;
 (* keep=1,dont_touch=1 *) reg [7:0] id,id_check;
 wire [RB-1:0] request_bad;
 wire [PB-1:0] reply_bad;
 wire metadata_bad=active!=~active_check||reply_active!=~reply_active_check||
     req_age!=~req_age_check||rep_age!=~rep_age_check||warm!=~warm_check||
     sent!=~sent_check||protocol_fault!=~protocol_fault_check||id!=~id_check;
 // Capture permission depends on held-slot state and small metadata only.
 // Each kept bank checks its OWN pair before updating. Wide pair mismatch
 // is excluded from this path; it remains an immediate publication veto.
 wire request_take=request_accept&&!active&&!protocol_fault&&!metadata_bad&&!bounds_fault;
 wire reply_take=checked_reply_capture&&active&&!reply_active&&!protocol_fault&&!metadata_bad;
 for(genvar c=0;c<16;c=c+1) begin : g_take_r
  if(MARGIN) begin : g_k
   ot_hdc_v41_fh_take_copy u_take(.clk(fast_clk),.cold_n(cold_c[c]),.d(request_take),.q(take_rc[c]));
  end else begin : g_n
   assign take_rc[c]=request_take;
  end
 end
 for(genvar c=0;c<8;c=c+1) begin : g_take_p
  if(MARGIN) begin : g_k
   ot_hdc_v41_fh_take_copy u_take(.clk(fast_clk),.cold_n(cold_c[c]),.d(reply_take),.q(take_pc[c]));
  end else begin : g_n
   assign take_pc[c]=reply_take;
  end
 end
 for(genvar b=0;b<RB;b=b+1) begin : g_request_bank
  localparam integer N=(REQ_BITS-b*32>=32)?32:REQ_BITS-b*32;
  ot_hdc_v41_fh_checked_bank #(.BITS(N),.MARGIN(MARGIN),.FPIPE(FPIPE)) u_bank (
   .clk(fast_clk),.cold_n(cold_b[b]),.load(take_rc[b%16]),.d(accepted_input[b*32+:N]),
   .q(source_packet[b*32+:N]),.check(source_check[b*32+:N]),.bad(request_bad[b]));
 end
 for(genvar b=0;b<PB;b=b+1) begin : g_reply_bank
  localparam integer N=(REP_BITS-b*32>=32)?32:REP_BITS-b*32;
  ot_hdc_v41_fh_checked_bank #(.BITS(N),.MARGIN(MARGIN),.FPIPE(FPIPE)) u_bank (
   .clk(fast_clk),.cold_n(cold_b[RB+b]),.load(take_pc[b%8]),.d(checked_reply[b*32+:N]),
   .q(held_reply[b*32+:N]),.check(held_check[b*32+:N]),.bad(reply_bad[b]));
 end
 // Full native identity, never the bounded head ID alone. Keep eight local
 // registered comparisons so ABC cannot create a wide permission feedback.
 wire [238:0] expected_identity={source_packet.ordinal,source_packet.owner,
     source_packet.we,source_packet.wa,source_packet.wm};
 wire [238:0] returned_identity={held_reply.ordinal,held_reply.owner,
     held_reply.visible,held_reply.wa,held_reply.wm};
 wire [7:0] match_q,match_check;
 for(genvar b=0;b<8;b=b+1) begin : g_identity_bank
  localparam integer N=(239-b*32>=32)?32:239-b*32;
  ot_hdc_v41_fh_checked_match #(.BITS(N)) u_match (
   .clk(fast_clk),.cold_n(cold_b[RB+PB+b]),.a(expected_identity[b*32+:N]),
   .b(returned_identity[b*32+:N]),.match(match_q[b]),.check(match_check[b]));
 end
 wire identity_bad=match_q!=~match_check;
 wire matching_reply=&match_q;
 wire checked_error;
 ot_hdc_v41_fh_checked_reduce #(.BITS(RB+PB+2)) u_check_reduce (
  .clk(fast_clk),.cold_n(cold_n),
  .bad({metadata_bad,identity_bad,request_bad,reply_bad}),.fault(checked_error));
 wire wide_bad=FPIPE?checked_error:((|request_bad)||(|reply_bad));
 wire ep_fault=protocol_fault||metadata_bad||bounds_fault||
     wide_bad||identity_bad||
     (reply_active&&rep_age==0&&!matching_reply);
 // FPIPE>=2: the endpoint fault leaves a register (+1 to the retirement's arithmetic-fault row); grants use it unregistered
 generate if(FPIPE>=2) begin : g_ep_reg
  (* keep=1,dont_touch=1 *) reg ep_q;
  always @(posedge fast_clk) if(!cold_n) ep_q<=0; else ep_q<=ep_fault;
  assign endpoint_fault=ep_q;
 end else begin : g_ep_direct
  assign endpoint_fault=ep_fault;
 end endgenerate
 assign request_checked_v=active&&req_age==0&&!ep_fault&&!checked_error;
 assign reply_checked_v=active&&reply_active&&rep_age==0&&matching_reply&&!ep_fault&&!checked_error;
 // Early held publication is refused until the matching check completes.
 // A wrong identity quarantines; a held correct publication is consumed once.
 wire consume=published_reply_v&&reply_checked_v&&!sent;
 wire ack_n=consume&&warm&&held_reply.visible[1];
 wire [23:0] ack_word_n={9'b0,held_reply.wa[15+:15]};
 wire [15:0] ack_mask_n=held_reply.wm[16+:16];
 localparam [2:0] AGE=FPIPE?3'd6:3'd5;
 generate if(FPIPE) begin : g_ack_reg
`ifndef SYNTHESIS
  initial if(!MARGIN) $fatal(1,"FPIPE needs MARGIN");
`endif
  // head ACK launched from registers: the debt owner sees the receipt one cycle later
  (* keep=1,dont_touch=1 *) reg ack_v_q;
  reg [7:0] ack_id_q;reg [23:0] ack_word_q;reg [15:0] ack_mask_q;
  always @(posedge fast_clk) begin
   if(!cold_n) ack_v_q<=0; else ack_v_q<=ack_n;
   ack_id_q<=id;ack_word_q<=ack_word_n;ack_mask_q<=ack_mask_n;
  end
  assign head_ack_v=ack_v_q;assign head_ack_id=ack_id_q;
  assign head_ack_word=ack_word_q;assign head_ack_mask=ack_mask_q;
 end else begin : g_ack_direct
  assign head_ack_v=ack_n;assign head_ack_id=id;
  assign head_ack_word=ack_word_n;assign head_ack_mask=ack_mask_n;
 end endgenerate
 assign guard_busy=active;
 assign captured_request=source_packet;assign captured_request_check=source_check;
 assign captured_reply=held_reply;assign captured_reply_check=held_check;
 always @(posedge fast_clk) begin
  if(!cold_n) begin
   active<=0;active_check<=1;reply_active<=0;reply_active_check<=1;
   req_age<=0;req_age_check<=3'b111;rep_age<=0;rep_age_check<=3'b111;
   warm<=0;warm_check<=1;sent<=0;sent_check<=1;
   protocol_fault<=0;protocol_fault_check<=1;id<=0;id_check<=8'hff;
  end else begin
   if(request_take) begin
    active<=1;active_check<=0;reply_active<=0;reply_active_check<=1;
    req_age<=AGE;req_age_check<=~AGE;rep_age<=0;rep_age_check<=3'b111;
    warm<=request_warm;warm_check<=~request_warm;id<=request_id;id_check<=~request_id;
    sent<=0;sent_check<=1;
   end else if(active&&req_age!=0) begin req_age<=req_age-1'b1;req_age_check<=~(req_age-3'd1);end
   if(reply_take) begin reply_active<=1;reply_active_check<=0;rep_age<=AGE;rep_age_check<=~AGE;end
   else if(reply_active&&rep_age!=0) begin rep_age<=rep_age-1'b1;rep_age_check<=~(rep_age-3'd1);end
   if(consume) begin sent<=1;sent_check<=0;end
   // Release storage only after matching real checked visibility. The parent
   // independently consumes the warm ACK on this same edge.
   if(active&&sent&&!published_reply_v) begin active<=0;active_check<=1;end
   if(metadata_bad||bounds_fault||identity_bad||
       (request_accept&&!request_take)||
       (checked_reply_capture&&!reply_take)||
       (published_reply_v&&reply_active&&rep_age==0&&!matching_reply)) begin
    protocol_fault<=1;protocol_fault_check<=0;
   end
  end
 end
endmodule

(* keep_hierarchy *)
module ot_hdc_v41_fh_checked_bank #(parameter integer BITS=32, MARGIN=0, FPIPE=0)(
 input wire clk,cold_n,load,input wire [BITS-1:0] d,
 (* keep=1,dont_touch=1 *) output reg [BITS-1:0] q,check,output wire bad
);
 // MARGIN: data registered twice at the bank, load (already one kept copy late) once more
 wire [BITS-1:0] dl;
 wire ll;
 generate if(MARGIN) begin : g_pipe
  reg [BITS-1:0] d1,d2;
  reg l2;
  always @(posedge clk) begin d1<=d; d2<=d1; l2<=cold_n&&load; end
  assign dl=d2; assign ll=l2;
 end else begin : g_direct
  assign dl=d; assign ll=load;
 end endgenerate
 (* keep=1,dont_touch=1 *) reg fault,fault_check;
 wire mismatch=q!=~check;
 wire bad_n=mismatch||fault||fault!=~fault_check;
 // FPIPE: the bank's bad flag leaves a kept per-bank flop (the local pair check stays inside the bank)
 generate if(FPIPE) begin : g_bad_reg
  (* keep=1,dont_touch=1 *) reg bad_q;
  always @(posedge clk) if(!cold_n) bad_q<=0; else bad_q<=bad_n;
  assign bad=bad_q;
 end else begin : g_bad_direct
  assign bad=bad_n;
 end endgenerate
 always @(posedge clk) begin
  if(!cold_n) begin q<=0;check<={BITS{1'b1}};fault<=0;fault_check<=1;end
  else begin
   if(ll&&!bad_n) begin q<=dl;check<=~dl;end
   if(bad_n) begin fault<=1;fault_check<=0;end
  end
 end
endmodule

// kept copies for the margin-first endpoint broadcast (cold_n, take)
(* keep_hierarchy *)
module ot_hdc_v41_fh_cold_copy(input wire clk,d,output reg q);
 always @(posedge clk) q<=d;
endmodule
(* keep_hierarchy *)
module ot_hdc_v41_fh_take_copy(input wire clk,cold_n,d,output reg q);
 always @(posedge clk) if(!cold_n) q<=0; else q<=d;
endmodule

(* keep_hierarchy *)
module ot_hdc_v41_fh_checked_reduce #(parameter integer BITS=131)(
 input wire clk,cold_n,input wire [BITS-1:0] bad,output wire fault
);
 localparam integer NG=(BITS+7)/8,NC=(NG+3)/4;
 (* keep=1,dont_touch=1 *) reg [NG-1:0] local_bad,local_check;
 (* keep=1,dont_touch=1 *) reg [NC-1:0] cluster_bad,cluster_check;
 (* keep=1,dont_touch=1 *) reg final_bad,final_check;
 for(genvar g=0;g<NG;g=g+1) begin : g_local_check
  localparam integer N=(BITS-g*8>=8)?8:BITS-g*8;
  always @(posedge clk) if(!cold_n)begin local_bad[g]<=0;local_check[g]<=1;end
   else begin local_bad[g]<=|bad[g*8+:N];local_check[g]<=~(|bad[g*8+:N]);end
 end
 for(genvar c=0;c<NC;c=c+1) begin : g_cluster_check
  localparam integer N=(NG-c*4>=4)?4:NG-c*4;
  wire f=(|local_bad[c*4+:N])||local_bad[c*4+:N]!=~local_check[c*4+:N];
  always @(posedge clk) if(!cold_n)begin cluster_bad[c]<=0;cluster_check[c]<=1;end
   else begin cluster_bad[c]<=f;cluster_check[c]<=~f;end
 end
 wire f=(|cluster_bad)||cluster_bad!=~cluster_check;
 always @(posedge clk) if(!cold_n)begin final_bad<=0;final_check<=1;end
  else begin final_bad<=f;final_check<=~f;end
 assign fault=final_bad||final_bad!=~final_check||
     local_bad!=~local_check||cluster_bad!=~cluster_check;
endmodule

(* keep_hierarchy *)
module ot_hdc_v41_fh_checked_match #(parameter integer BITS=32)(
 input wire clk,cold_n,input wire [BITS-1:0] a,b,
 (* keep=1,dont_touch=1 *) output reg match,check
);
 always @(posedge clk) begin
  if(!cold_n) begin match<=0;check<=1;end
  else begin match<=a==b;check<=~(a==b);end
 end
endmodule
