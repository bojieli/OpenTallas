`timescale 1ns/1ps
// REGISTERED_BOUNDARY successor of the W2 protected bank (additive; every
// earlier bank, cut and gate is unchanged and remains the default).
//
// Registered veto. The protected representation is the balanced CHECK one
// (per word: W6 code, W6 snapshot lo/hi, W6 syndrome, exact W6 mirror of the
// checked inputs, W6 verdict; bank: W6 phase word and a failed dual rail).
// What changes is WHEN the EVAL verdict is known:
//   S1 (one edge): every word's equality/bound/verdict check is registered
//      locally (5 bits per word) together with the sampled phase.
//   S2 (one edge): the bank-wide reduction and the fault/normal formula.
// The data the consumer sees is delayed by the same two edges (q = code two
// edges ago). Therefore every permission the bank grants (normal) is a verdict
// about EXACTLY the bits it presents: a corruption that lands after the sampled
// edge can never be presented as normal, because the presented copy predates
// it and the next verdict refuses it. That is the equivalence argument for the
// registered veto (same-edge inhibition of the presented data), benched by
// tb_w2_bank_veto.sv (normal => q === protected value, every edge).
// Faults are latched (sticky) two edges after the corrupted state is sampled;
// no output, load or repair can be authorised by a verdict that saw it.
//
// Phase (W6 phase word raw bits[2:0]): 0 CHECK 1 VERIFY 2 EVAL 3 REPAIR
// 4 COMMIT, and with DIST=1 the distribution phases 5 PREP_CHECK 6 PREP_COMMIT
// 7 PREP_REPAIR, which give a wide bank one edge to carry the decision to
// per-word kept enable copies (com/rep/chk/ver). The copies are checked
// against the protected phase every edge; a mismatch is a fault.
// Data words carry no reset: POR enters COMMIT with select=0, which writes
// the all-zero W6 codeword, then CHECK/VERIFY/EVAL as for any load.
// STAGE=1 samples encoded_d at the deciding edge (combinational sources);
// STAGE=0 commits encoded_d itself and requires it stable until COMMIT ends.
// RED=1 (margin; the default for WORDS>8) splits the bank-wide S2 reduction:
// an extra registered edge SM reduces each group of 8 words and S2 combines
// the groups. The presented data takes the same extra edge (q = code three
// edges ago), so every verdict is still about exactly the presented bits; the
// reduced Boolean is unchanged (AND/OR are associative).
module ot_hbm_w2_protected_bank_veto_on #(parameter integer WORDS=1, STAGE=1, DIST=0, RED=(WORDS>8),LOCAL_PHASE=0,HOLD_SEAT=0)(
 input wire clk,por_n,load,load_sel,fatal,
 input wire [WORDS*72-1:0] encoded_d,
 output wire [WORDS*64-1:0] q,
 output wire normal,fault,repairing);
 import ot_gpu_w6_secded_pkg::*;
 import ot_hbm_w2_boundary_pkg::*;
 localparam [2:0] P_CHECK=0,P_VERIFY=1,P_EVAL=2,P_REPAIR=3,P_COMMIT=4,
                  P_PCHECK=5,P_PCOMMIT=6,P_PREPAIR=7;
 reg [71:0] code[0:WORDS-1];
 reg [71:0] snapshot_lo[0:WORDS-1],snapshot_hi[0:WORDS-1];
 reg [71:0] syndrome[0:WORDS-1];
 reg [71:0] checked_lo[0:WORDS-1],checked_hi[0:WORDS-1],checked_syn[0:WORDS-1];
 reg [71:0] verdict[0:WORDS-1];
 reg [71:0] staged[0:WORDS-1];
 reg [63:0] q_d1[0:WORDS-1],q_d2[0:WORDS-1];
 reg [71:0] phase_code;
 (* keep=1, dont_touch=1 *) reg failed,failed_n;
 // Per-word kept enable copies (separate kept hierarchy: never merged).
 wire [WORDS-1:0] com_q,rep_q,chk_q,ver_q,sel_q;
 // S1 (per word) and S2 (bank) registered verdict pipeline.
 reg [WORDS-1:0] s_same,s_bad,s_cbad,s_ce,s_ue,s_clean;
 reg [2:0] s_ph;reg s_ctlbad;
 reg [2:0] ph2;reg f2,n2,same2,ce2;
 // SM level: group reductions (RED=1) or the S1 registers themselves (RED=0).
 localparam integer NG=RED?(WORDS+7)/8:WORDS;
 wire [NG-1:0] m_same,m_bad,m_cbad,m_ce,m_ue,m_clean;wire [2:0] m_ph;wire m_ctlbad;
 wire [63:0] q_m[0:WORDS-1];
 wire [63:0] raw_seat[0:WORDS-1],d1_seat[0:WORDS-1],qm_seat[0:WORDS-1];
 for(genvar hs=0;hs<WORDS;hs=hs+1)begin:hseat
  if(HOLD_SEAT)begin:real_delay
   ot_hbm_w2_hold_seat #(.W(64)) u_raw(.a(raw64(code[hs])),.y(raw_seat[hs]));
   ot_hbm_w2_hold_seat #(.W(64)) u_d1(.a(q_d1[hs]),.y(d1_seat[hs]));
   if(RED)begin:extra
    ot_hbm_w2_hold_seat #(.W(64)) u_qm(.a(q_m[hs]),.y(qm_seat[hs]));
   end else assign qm_seat[hs]=q_m[hs];
  end else begin:bypass
   assign raw_seat[hs]=raw64(code[hs]);assign d1_seat[hs]=q_d1[hs];assign qm_seat[hs]=q_m[hs];
  end
 end
 wire [63:0] phase_raw=raw64(phase_code);
 wire [2:0] phase=phase_raw[2:0];
 // raw[3] is the protected commit select (data vs zero codeword).
 wire sel_bit=phase_raw[3];
 wire control_bad=check72(phase_code)!=0 || phase_raw[63:4]!=0 || (!DIST && phase>=P_PCHECK) ||
                  (sel_bit && phase!=P_COMMIT && phase!=P_PCOMMIT);
 wire go_commit,go_repair,go_check,go_sel,d_commit;
 wire [WORDS-1:0] same,bad,cbad,ce,ue,clean,input_bad;
 wire [71:0] snap[0:WORDS-1];
 wire [7:0] syn[0:WORDS-1];
 // Declare shared drivers before the generate scope: otherwise implicit
 // one-bit local nets can shadow the next-state signals in Verilog.
 wire freeze=failed || failed==failed_n || f2 || fatal;
 reg [2:0] phase_next;reg sel_next;
 for(genvar g=0;g<WORDS;g=g+1)begin:word
  wire [63:0] hi=raw64(snapshot_hi[g]);
  wire [63:0] status=raw64(syndrome[g]);
  assign snap[g]={hi[7:0],raw64(snapshot_lo[g])};
  assign syn[g]=status[7:0];
  assign same[g]=(code[g]===snap[g]);
  assign input_bad[g]=check72(snapshot_lo[g])!=0 || check72(snapshot_hi[g])!=0 ||
                check72(syndrome[g])!=0 || hi[63:8]!=0 || status[63:8]!=0;
  wire [63:0] v=raw64(verdict[g]);
  wire bound=(checked_lo[g]===snapshot_lo[g])&&(checked_hi[g]===snapshot_hi[g])&&(checked_syn[g]===syndrome[g]);
  assign bad[g]=!bound || check72(verdict[g])!=0 || v[63:4]!=0 || v[3];
  // Kept per-word phase replicas reduce fanout for timing (binding V16).
  // Capture the same next-state value as phase_code; no new copy-check.
  wire [3:0] local_phase;
  if(LOCAL_PHASE)begin:lph
   ot_hbm_w2_keep_reg #(.W(4),.RV(4'b0100)) u_phase(
    .clk(clk),.rst_n(por_n),.d(freeze?{sel_bit,phase}:{sel_next,phase_next}),.q(local_phase));
  end else begin:gph assign local_phase={sel_bit,phase}; end
  wire [2:0] wp=local_phase[2:0]; wire ws=local_phase[3];
  assign cbad[g]=(com_q[g]!=(wp==P_COMMIT)) || (rep_q[g]!=(wp==P_REPAIR)) ||
                 (chk_q[g]!=(wp==P_CHECK)) || (ver_q[g]!=(wp==P_VERIFY)) ||
                 (sel_q[g]!=(wp==P_COMMIT && ws));
  assign ce[g]=v[1];assign ue[g]=v[2];assign clean[g]=v[0];
  assign q[g*64+:64]=q_d2[g];
  ot_hbm_w2_keep_reg #(.W(5),.RV(5'b10000)) u_cp(.clk(clk),.rst_n(por_n),
   .d({go_commit,go_repair,go_check|com_q[g]|rep_q[g],chk_q[g],go_sel}),
   .q({com_q[g],rep_q[g],chk_q[g],ver_q[g],sel_q[g]}));
 end
 generate if(RED)begin:sm
  reg [NG-1:0] r_same,r_bad,r_cbad,r_ce,r_ue,r_clean;reg [2:0] r_ph;reg r_ctlbad;
  reg [63:0] r_q[0:WORDS-1];
  wire [NG-1:0] g_same,g_bad,g_cbad,g_ce,g_ue,g_clean;
  for(genvar j=0;j<NG;j=j+1)begin:grp
   localparam integer LO=8*j,N=(WORDS-LO<8)?WORDS-LO:8;
   assign g_same[j]=&s_same[LO+:N];assign g_bad[j]=|s_bad[LO+:N];assign g_cbad[j]=|s_cbad[LO+:N];
   assign g_ce[j]=|s_ce[LO+:N];assign g_ue[j]=|s_ue[LO+:N];assign g_clean[j]=&s_clean[LO+:N];
  end
  always @(posedge clk or negedge por_n)
   if(!por_n)begin r_same<=0;r_bad<=0;r_cbad<=0;r_ce<=0;r_ue<=0;r_clean<=0;r_ph<=P_COMMIT;r_ctlbad<=0;end
   else begin
    r_same<=g_same;r_bad<=g_bad;r_cbad<=g_cbad;r_ce<=g_ce;r_ue<=g_ue;r_clean<=g_clean;
    r_ph<=s_ph;r_ctlbad<=s_ctlbad;
   end
  always @(posedge clk)for(integer w=0;w<WORDS;w=w+1)r_q[w]<=d1_seat[w];
  assign m_same=r_same;assign m_bad=r_bad;assign m_cbad=r_cbad;assign m_ce=r_ce;assign m_ue=r_ue;
  assign m_clean=r_clean;assign m_ph=r_ph;assign m_ctlbad=r_ctlbad;
  for(genvar w=0;w<WORDS;w=w+1)begin:qm assign q_m[w]=r_q[w];end
 end else begin:nosm
  assign m_same=s_same;assign m_bad=s_bad;assign m_cbad=s_cbad;assign m_ce=s_ce;assign m_ue=s_ue;
  assign m_clean=s_clean;assign m_ph=s_ph;assign m_ctlbad=s_ctlbad;
  for(genvar w=0;w<WORDS;w=w+1)begin:qm assign q_m[w]=d1_seat[w];end
 end endgenerate
 assign fault=failed || failed==failed_n || f2;
 assign normal=n2 && phase==P_EVAL && !failed && failed_n && !fatal;
 assign repairing=!fault && !normal;
 // EVAL decisions only on a verdict sampled in EVAL (two edges ago). EVAL
 // performs no writes while it stays, so that verdict covers today's state.
 wire settled=phase==P_EVAL && ph2==P_EVAL && !freeze;
 wire d_check=settled && !same2;
 wire d_repair=settled && same2 && ce2;
 assign d_commit=settled && same2 && !ce2 && normal && load;
 always @*begin
  phase_next=phase;sel_next=(phase==P_COMMIT||phase==P_PCOMMIT)&&sel_bit;
  if(!freeze)case(phase)
   P_CHECK:phase_next=P_VERIFY;
   P_VERIFY:phase_next=P_EVAL;
   P_EVAL:if(d_check)phase_next=DIST?P_PCHECK:P_CHECK;
          else if(d_repair)phase_next=DIST?P_PREPAIR:P_REPAIR;
          else if(d_commit)begin phase_next=DIST?P_PCOMMIT:P_COMMIT;sel_next=load_sel;end
   P_REPAIR,P_COMMIT:begin phase_next=P_CHECK;sel_next=0;end
   P_PCHECK:phase_next=P_CHECK;
   P_PCOMMIT:phase_next=P_COMMIT;
   P_PREPAIR:phase_next=P_REPAIR;
   default:phase_next=phase;
  endcase
 end
 // Copy drivers: DIST copies decode only the protected phase register (one
 // short distribution edge); DIST=0 copies follow the local decision.
 assign go_commit=DIST?(phase==P_PCOMMIT):(phase_next==P_COMMIT && phase!=P_COMMIT);
 assign go_repair=DIST?(phase==P_PREPAIR):(phase_next==P_REPAIR && phase!=P_REPAIR);
 assign go_check=DIST?(phase==P_PCHECK):(phase_next==P_CHECK && phase==P_EVAL);
 assign go_sel=DIST?(phase==P_PCOMMIT && sel_bit):(go_commit && load_sel);
 integer i;
 always @(posedge clk or negedge por_n)begin
  if(!por_n)begin
   failed<=0;failed_n<=1;
   phase_code<=encode64({61'b0,P_COMMIT});
   s_same<=0;s_bad<=0;s_cbad<=0;s_ce<=0;s_ue<=0;s_clean<=0;s_ph<=P_COMMIT;s_ctlbad<=0;
   ph2<=P_COMMIT;f2<=0;n2<=0;same2<=0;ce2<=0;
  end else begin
   s_same<=same;s_bad<=bad;s_cbad<=cbad;s_ce<=ce;s_ue<=ue;s_clean<=clean;
   s_ph<=phase;s_ctlbad<=control_bad;
   ph2<=m_ph;same2<=&m_same;ce2<=|m_ce;
   f2<=m_ctlbad || (|m_cbad) || ((m_ph==P_EVAL||m_ph==P_REPAIR) && (|m_bad)) ||
       (m_ph==P_EVAL && (&m_same) && (|m_ue)) || (m_ph==P_REPAIR && !(&m_same));
   n2<=!(m_ctlbad || (|m_cbad) || (m_ph==P_EVAL && (|m_bad)) || (m_ph==P_EVAL && (&m_same) && (|m_ue))) &&
       m_ph==P_EVAL && (&m_same) && (&m_clean);
   if(freeze)begin failed<=1;failed_n<=0;end
   else phase_code<=encode64({60'b0,sel_next,phase_next});
  end
 end
 // Word state: no reset (POR commits the zero codeword). Enables are the
 // kept per-word copies only, so no bank-wide enable crosses the block.
 always @(posedge clk)begin
  for(i=0;i<WORDS;i=i+1)begin
   q_d1[i]<=raw_seat[i];q_d2[i]<=qm_seat[i];
   if(STAGE && phase==P_EVAL)staged[i]<=encoded_d[i*72+:72];
   if(com_q[i])code[i]<=sel_q[i]?(STAGE?staged[i]:encoded_d[i*72+:72]):72'b0;
   else if(rep_q[i]&&ce[i])code[i]<=snap[i]^(72'b1<<(syn[i][6:0]==0?7'd71:syn[i][6:0]-1'b1));
   if(chk_q[i])begin
    snapshot_lo[i]<=encode64(code[i][63:0]);
    snapshot_hi[i]<=encode64({56'b0,code[i][71:64]});
    syndrome[i]<=encode64({56'b0,check72(code[i])});
   end
   if(ver_q[i])begin
    checked_lo[i]<=snapshot_lo[i];checked_hi[i]<=snapshot_hi[i];checked_syn[i]<=syndrome[i];
    verdict[i]<=encode64({60'b0,input_bad[i],
      (syn[i][6:0]!=0 && (!syn[i][7] || syn[i][6:0]>71)),
      (syn[i][7] && syn[i][6:0]<=71),(syn[i]==0)});
   end
  end
 end
endmodule

// Registered-veto cut: {valid,data} in one veto bank. in_r is the decision of
// THIS edge (the item is taken when in_v&&in_r). PREENC=1 encodes in_d here
// and stages it; PREENC=0 takes caller codes (incl. the valid bit) that stay
// stable until the commit edge (the station's encoded input seat).
module ot_hbm_w2_protected_cut_veto_on #(parameter integer W=337, PREENC=1, DIST=0, LOCAL_PHASE=0,HOLD_SEAT=0)(
 input wire clk,por_n,in_v,output wire in_r,
 input wire [W-1:0] in_d,input wire [((W+1+63)/64)*72-1:0] in_codes,
 output wire out_v,input wire out_r,
 output wire [W-1:0] out_d,output wire empty,fault);
 import ot_gpu_w6_secded_pkg::*;
 localparam integer N=(W+1+63)/64;
 wire [N*64-1:0] q;wire normal,repairing;
 wire valid=q[W];
 wire [N*64-1:0] raw_input={{(N*64-W-1){1'b0}},1'b1,in_d};
 wire [N*72-1:0] preencoded;
 for(genvar e=0;e<N;e=e+1)begin:encode_before_accept
  assign preencoded[e*72+:72]=encode64(raw_input[e*64+:64]);
 end
 assign in_r=normal&&(!valid||out_r);
 assign out_v=normal&&valid;assign out_d=q[W-1:0];
 assign empty=normal&&!valid;
 ot_hbm_w2_protected_bank_veto_on #(.WORDS(N),.STAGE(PREENC),.DIST(DIST),.LOCAL_PHASE(LOCAL_PHASE),.HOLD_SEAT(HOLD_SEAT)) u_state(
  .clk(clk),.por_n(por_n),.load(in_r&&(in_v||valid)),.load_sel(in_v),.fatal(1'b0),
  .encoded_d(PREENC?preencoded:in_codes),
  .q(q),.normal(normal),.fault(fault),.repairing(repairing));
endmodule

// Dual-rail register for station control that is not in a W6 word: any
// disagreement between the rails is reported (fail closed).
(* keep_hierarchy=1 *)
module ot_hbm_w2_dr_reg #(parameter integer W=1)(
 input wire clk,rst_n,input wire [W-1:0] d,output wire [W-1:0] q,output wire bad);
 (* keep=1, dont_touch=1 *) reg [W-1:0] t,f;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin t<=0;f<={W{1'b1}};end else begin t<=d;f<=~d;end
 assign q=t;assign bad=|(t~^f);
endmodule

// Kept register copies: a separate kept hierarchy so synthesis cannot merge
// identical copies (each word's enables drive only that word).
(* keep_hierarchy=1 *)
module ot_hbm_w2_keep_reg #(parameter integer W=1, parameter [W-1:0] RV=0)(
 input wire clk,rst_n,input wire [W-1:0] d,output reg [W-1:0] q);
 always @(posedge clk or negedge rst_n)if(!rst_n)q<=RV;else q<=d;
endmodule
// Kept data register without reset (per-pin output launch copies).
(* keep_hierarchy=1 *)
module ot_hbm_w2_keep_dreg #(parameter integer W=1)(
 input wire clk,input wire [W-1:0] d,output reg [W-1:0] q);
 always @(posedge clk)q<=d;
endmodule

// Eight real cells, logically identity. Hierarchy prevents ABC cancelling the
// chain; positive/negative exact gates and mapped inventory verify the seats.
(* keep_hierarchy=1 *)
module ot_hbm_w2_hold_seat #(parameter integer W=64)(input wire [W-1:0] a,output wire [W-1:0] y);
 wire [W-1:0] stage[0:8];assign stage[0]=a;assign y=stage[8];
 for(genvar bitn=0;bitn<W;bitn=bitn+1)begin:b
  for(genvar n=0;n<8;n=n+1)begin:i
   ot_hbm_w2_hold_inv u_inv(.a(stage[n][bitn]),.y(stage[n+1][bitn]));
  end
 end
endmodule
(* keep_hierarchy=1 *)
module ot_hbm_w2_hold_inv(input wire a,output wire y);assign y=~a;endmodule
