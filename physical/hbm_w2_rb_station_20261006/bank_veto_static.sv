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
module ot_hbm_w2_protected_bank_veto_on #(parameter integer WORDS=1, STAGE=1, DIST=0)(
 input wire clk,por_n,load,load_sel,fatal,
 input wire [WORDS*72-1:0] encoded_d,
 output wire [WORDS*64-1:0] q,
 output wire normal,fault,repairing);
function automatic [71:0] encode64(input [63:0] data);
  begin encode64={^{data[63],data[62],data[61],data[60],data[59],data[58],data[57],^{data[57],data[58],data[59],data[60],data[61],data[62],data[63]},data[56],data[55],data[54],data[53],data[52],data[51],data[50],data[49],data[48],data[47],data[46],data[45],data[44],data[43],data[42],data[41],data[40],data[39],data[38],data[37],data[36],data[35],data[34],data[33],data[32],data[31],data[30],data[29],data[28],data[27],data[26],^{data[26],data[27],data[28],data[29],data[30],data[31],data[32],data[33],data[34],data[35],data[36],data[37],data[38],data[39],data[40],data[41],data[42],data[43],data[44],data[45],data[46],data[47],data[48],data[49],data[50],data[51],data[52],data[53],data[54],data[55],data[56]},data[25],data[24],data[23],data[22],data[21],data[20],data[19],data[18],data[17],data[16],data[15],data[14],data[13],data[12],data[11],^{data[11],data[12],data[13],data[14],data[15],data[16],data[17],data[18],data[19],data[20],data[21],data[22],data[23],data[24],data[25],data[41],data[42],data[43],data[44],data[45],data[46],data[47],data[48],data[49],data[50],data[51],data[52],data[53],data[54],data[55],data[56]},data[10],data[9],data[8],data[7],data[6],data[5],data[4],^{data[4],data[5],data[6],data[7],data[8],data[9],data[10],data[18],data[19],data[20],data[21],data[22],data[23],data[24],data[25],data[33],data[34],data[35],data[36],data[37],data[38],data[39],data[40],data[49],data[50],data[51],data[52],data[53],data[54],data[55],data[56]},data[3],data[2],data[1],^{data[1],data[2],data[3],data[7],data[8],data[9],data[10],data[14],data[15],data[16],data[17],data[22],data[23],data[24],data[25],data[29],data[30],data[31],data[32],data[37],data[38],data[39],data[40],data[45],data[46],data[47],data[48],data[53],data[54],data[55],data[56],data[60],data[61],data[62],data[63]},data[0],^{data[0],data[2],data[3],data[5],data[6],data[9],data[10],data[12],data[13],data[16],data[17],data[20],data[21],data[24],data[25],data[27],data[28],data[31],data[32],data[35],data[36],data[39],data[40],data[43],data[44],data[47],data[48],data[51],data[52],data[55],data[56],data[58],data[59],data[62],data[63]},^{data[0],data[1],data[3],data[4],data[6],data[8],data[10],data[11],data[13],data[15],data[17],data[19],data[21],data[23],data[25],data[26],data[28],data[30],data[32],data[34],data[36],data[38],data[40],data[42],data[44],data[46],data[48],data[50],data[52],data[54],data[56],data[57],data[59],data[61],data[63]}},data[63],data[62],data[61],data[60],data[59],data[58],data[57],^{data[57],data[58],data[59],data[60],data[61],data[62],data[63]},data[56],data[55],data[54],data[53],data[52],data[51],data[50],data[49],data[48],data[47],data[46],data[45],data[44],data[43],data[42],data[41],data[40],data[39],data[38],data[37],data[36],data[35],data[34],data[33],data[32],data[31],data[30],data[29],data[28],data[27],data[26],^{data[26],data[27],data[28],data[29],data[30],data[31],data[32],data[33],data[34],data[35],data[36],data[37],data[38],data[39],data[40],data[41],data[42],data[43],data[44],data[45],data[46],data[47],data[48],data[49],data[50],data[51],data[52],data[53],data[54],data[55],data[56]},data[25],data[24],data[23],data[22],data[21],data[20],data[19],data[18],data[17],data[16],data[15],data[14],data[13],data[12],data[11],^{data[11],data[12],data[13],data[14],data[15],data[16],data[17],data[18],data[19],data[20],data[21],data[22],data[23],data[24],data[25],data[41],data[42],data[43],data[44],data[45],data[46],data[47],data[48],data[49],data[50],data[51],data[52],data[53],data[54],data[55],data[56]},data[10],data[9],data[8],data[7],data[6],data[5],data[4],^{data[4],data[5],data[6],data[7],data[8],data[9],data[10],data[18],data[19],data[20],data[21],data[22],data[23],data[24],data[25],data[33],data[34],data[35],data[36],data[37],data[38],data[39],data[40],data[49],data[50],data[51],data[52],data[53],data[54],data[55],data[56]},data[3],data[2],data[1],^{data[1],data[2],data[3],data[7],data[8],data[9],data[10],data[14],data[15],data[16],data[17],data[22],data[23],data[24],data[25],data[29],data[30],data[31],data[32],data[37],data[38],data[39],data[40],data[45],data[46],data[47],data[48],data[53],data[54],data[55],data[56],data[60],data[61],data[62],data[63]},data[0],^{data[0],data[2],data[3],data[5],data[6],data[9],data[10],data[12],data[13],data[16],data[17],data[20],data[21],data[24],data[25],data[27],data[28],data[31],data[32],data[35],data[36],data[39],data[40],data[43],data[44],data[47],data[48],data[51],data[52],data[55],data[56],data[58],data[59],data[62],data[63]},^{data[0],data[1],data[3],data[4],data[6],data[8],data[10],data[11],data[13],data[15],data[17],data[19],data[21],data[23],data[25],data[26],data[28],data[30],data[32],data[34],data[36],data[38],data[40],data[42],data[44],data[46],data[48],data[50],data[52],data[54],data[56],data[57],data[59],data[61],data[63]}};end
 endfunction
function automatic [63:0] raw64(input [71:0] c);
  begin raw64={c[70],c[69],c[68],c[67],c[66],c[65],c[64],c[62],c[61],c[60],c[59],c[58],c[57],c[56],c[55],c[54],c[53],c[52],c[51],c[50],c[49],c[48],c[47],c[46],c[45],c[44],c[43],c[42],c[41],c[40],c[39],c[38],c[37],c[36],c[35],c[34],c[33],c[32],c[30],c[29],c[28],c[27],c[26],c[25],c[24],c[23],c[22],c[21],c[20],c[19],c[18],c[17],c[16],c[14],c[13],c[12],c[11],c[10],c[9],c[8],c[6],c[5],c[4],c[2]};end
 endfunction
function automatic [7:0] check72(input [71:0] c);
  begin check72={^c,^{c[63],c[64],c[65],c[66],c[67],c[68],c[69],c[70]},^{c[31],c[32],c[33],c[34],c[35],c[36],c[37],c[38],c[39],c[40],c[41],c[42],c[43],c[44],c[45],c[46],c[47],c[48],c[49],c[50],c[51],c[52],c[53],c[54],c[55],c[56],c[57],c[58],c[59],c[60],c[61],c[62]},^{c[15],c[16],c[17],c[18],c[19],c[20],c[21],c[22],c[23],c[24],c[25],c[26],c[27],c[28],c[29],c[30],c[47],c[48],c[49],c[50],c[51],c[52],c[53],c[54],c[55],c[56],c[57],c[58],c[59],c[60],c[61],c[62]},^{c[7],c[8],c[9],c[10],c[11],c[12],c[13],c[14],c[23],c[24],c[25],c[26],c[27],c[28],c[29],c[30],c[39],c[40],c[41],c[42],c[43],c[44],c[45],c[46],c[55],c[56],c[57],c[58],c[59],c[60],c[61],c[62]},^{c[3],c[4],c[5],c[6],c[11],c[12],c[13],c[14],c[19],c[20],c[21],c[22],c[27],c[28],c[29],c[30],c[35],c[36],c[37],c[38],c[43],c[44],c[45],c[46],c[51],c[52],c[53],c[54],c[59],c[60],c[61],c[62],c[67],c[68],c[69],c[70]},^{c[1],c[2],c[5],c[6],c[9],c[10],c[13],c[14],c[17],c[18],c[21],c[22],c[25],c[26],c[29],c[30],c[33],c[34],c[37],c[38],c[41],c[42],c[45],c[46],c[49],c[50],c[53],c[54],c[57],c[58],c[61],c[62],c[65],c[66],c[69],c[70]},^{c[0],c[2],c[4],c[6],c[8],c[10],c[12],c[14],c[16],c[18],c[20],c[22],c[24],c[26],c[28],c[30],c[32],c[34],c[36],c[38],c[40],c[42],c[44],c[46],c[48],c[50],c[52],c[54],c[56],c[58],c[60],c[62],c[64],c[66],c[68],c[70]}};end
 endfunction
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
  // Kept enable copies must equal the protected phase they act for.
  assign cbad[g]=(com_q[g]!=(phase==P_COMMIT)) || (rep_q[g]!=(phase==P_REPAIR)) ||
                 (chk_q[g]!=(phase==P_CHECK)) || (ver_q[g]!=(phase==P_VERIFY)) ||
                 (sel_q[g]!=(phase==P_COMMIT && sel_bit));
  assign ce[g]=v[1];assign ue[g]=v[2];assign clean[g]=v[0];
  assign q[g*64+:64]=q_d2[g];
  ot_hbm_w2_keep_reg #(.W(5),.RV(5'b10000)) u_cp(.clk(clk),.rst_n(por_n),
   .d({go_commit,go_repair,go_check|com_q[g]|rep_q[g],chk_q[g],go_sel}),
   .q({com_q[g],rep_q[g],chk_q[g],ver_q[g],sel_q[g]}));
 end
 wire freeze=failed || failed==failed_n || f2 || fatal;
 assign fault=failed || failed==failed_n || f2;
 assign normal=n2 && phase==P_EVAL && !failed && failed_n && !fatal;
 assign repairing=!fault && !normal;
 // EVAL decisions only on a verdict sampled in EVAL (two edges ago). EVAL
 // performs no writes while it stays, so that verdict covers today's state.
 wire settled=phase==P_EVAL && ph2==P_EVAL && !freeze;
 wire d_check=settled && !same2;
 wire d_repair=settled && same2 && ce2;
 assign d_commit=settled && same2 && !ce2 && normal && load;
 reg [2:0] phase_next;reg sel_next;
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
   ph2<=s_ph;same2<=&s_same;ce2<=|s_ce;
   f2<=s_ctlbad || (|s_cbad) || ((s_ph==P_EVAL||s_ph==P_REPAIR) && (|s_bad)) ||
       (s_ph==P_EVAL && (&s_same) && (|s_ue)) || (s_ph==P_REPAIR && !(&s_same));
   n2<=!(s_ctlbad || (|s_cbad) || (s_ph==P_EVAL && (|s_bad)) || (s_ph==P_EVAL && (&s_same) && (|s_ue))) &&
       s_ph==P_EVAL && (&s_same) && (&s_clean);
   if(freeze)begin failed<=1;failed_n<=0;end
   else phase_code<=encode64({60'b0,sel_next,phase_next});
  end
 end
 // Word state: no reset (POR commits the zero codeword). Enables are the
 // kept per-word copies only, so no bank-wide enable crosses the block.
 always @(posedge clk)begin
  for(i=0;i<WORDS;i=i+1)begin
   q_d1[i]<=raw64(code[i]);q_d2[i]<=q_d1[i];
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
module ot_hbm_w2_protected_cut_veto_on #(parameter integer W=337, PREENC=1, DIST=0)(
 input wire clk,por_n,in_v,output wire in_r,
 input wire [W-1:0] in_d,input wire [((W+1+63)/64)*72-1:0] in_codes,
 output wire out_v,input wire out_r,
 output wire [W-1:0] out_d,output wire empty,fault);
function automatic [71:0] encode64(input [63:0] data);
  begin encode64={^{data[63],data[62],data[61],data[60],data[59],data[58],data[57],^{data[57],data[58],data[59],data[60],data[61],data[62],data[63]},data[56],data[55],data[54],data[53],data[52],data[51],data[50],data[49],data[48],data[47],data[46],data[45],data[44],data[43],data[42],data[41],data[40],data[39],data[38],data[37],data[36],data[35],data[34],data[33],data[32],data[31],data[30],data[29],data[28],data[27],data[26],^{data[26],data[27],data[28],data[29],data[30],data[31],data[32],data[33],data[34],data[35],data[36],data[37],data[38],data[39],data[40],data[41],data[42],data[43],data[44],data[45],data[46],data[47],data[48],data[49],data[50],data[51],data[52],data[53],data[54],data[55],data[56]},data[25],data[24],data[23],data[22],data[21],data[20],data[19],data[18],data[17],data[16],data[15],data[14],data[13],data[12],data[11],^{data[11],data[12],data[13],data[14],data[15],data[16],data[17],data[18],data[19],data[20],data[21],data[22],data[23],data[24],data[25],data[41],data[42],data[43],data[44],data[45],data[46],data[47],data[48],data[49],data[50],data[51],data[52],data[53],data[54],data[55],data[56]},data[10],data[9],data[8],data[7],data[6],data[5],data[4],^{data[4],data[5],data[6],data[7],data[8],data[9],data[10],data[18],data[19],data[20],data[21],data[22],data[23],data[24],data[25],data[33],data[34],data[35],data[36],data[37],data[38],data[39],data[40],data[49],data[50],data[51],data[52],data[53],data[54],data[55],data[56]},data[3],data[2],data[1],^{data[1],data[2],data[3],data[7],data[8],data[9],data[10],data[14],data[15],data[16],data[17],data[22],data[23],data[24],data[25],data[29],data[30],data[31],data[32],data[37],data[38],data[39],data[40],data[45],data[46],data[47],data[48],data[53],data[54],data[55],data[56],data[60],data[61],data[62],data[63]},data[0],^{data[0],data[2],data[3],data[5],data[6],data[9],data[10],data[12],data[13],data[16],data[17],data[20],data[21],data[24],data[25],data[27],data[28],data[31],data[32],data[35],data[36],data[39],data[40],data[43],data[44],data[47],data[48],data[51],data[52],data[55],data[56],data[58],data[59],data[62],data[63]},^{data[0],data[1],data[3],data[4],data[6],data[8],data[10],data[11],data[13],data[15],data[17],data[19],data[21],data[23],data[25],data[26],data[28],data[30],data[32],data[34],data[36],data[38],data[40],data[42],data[44],data[46],data[48],data[50],data[52],data[54],data[56],data[57],data[59],data[61],data[63]}},data[63],data[62],data[61],data[60],data[59],data[58],data[57],^{data[57],data[58],data[59],data[60],data[61],data[62],data[63]},data[56],data[55],data[54],data[53],data[52],data[51],data[50],data[49],data[48],data[47],data[46],data[45],data[44],data[43],data[42],data[41],data[40],data[39],data[38],data[37],data[36],data[35],data[34],data[33],data[32],data[31],data[30],data[29],data[28],data[27],data[26],^{data[26],data[27],data[28],data[29],data[30],data[31],data[32],data[33],data[34],data[35],data[36],data[37],data[38],data[39],data[40],data[41],data[42],data[43],data[44],data[45],data[46],data[47],data[48],data[49],data[50],data[51],data[52],data[53],data[54],data[55],data[56]},data[25],data[24],data[23],data[22],data[21],data[20],data[19],data[18],data[17],data[16],data[15],data[14],data[13],data[12],data[11],^{data[11],data[12],data[13],data[14],data[15],data[16],data[17],data[18],data[19],data[20],data[21],data[22],data[23],data[24],data[25],data[41],data[42],data[43],data[44],data[45],data[46],data[47],data[48],data[49],data[50],data[51],data[52],data[53],data[54],data[55],data[56]},data[10],data[9],data[8],data[7],data[6],data[5],data[4],^{data[4],data[5],data[6],data[7],data[8],data[9],data[10],data[18],data[19],data[20],data[21],data[22],data[23],data[24],data[25],data[33],data[34],data[35],data[36],data[37],data[38],data[39],data[40],data[49],data[50],data[51],data[52],data[53],data[54],data[55],data[56]},data[3],data[2],data[1],^{data[1],data[2],data[3],data[7],data[8],data[9],data[10],data[14],data[15],data[16],data[17],data[22],data[23],data[24],data[25],data[29],data[30],data[31],data[32],data[37],data[38],data[39],data[40],data[45],data[46],data[47],data[48],data[53],data[54],data[55],data[56],data[60],data[61],data[62],data[63]},data[0],^{data[0],data[2],data[3],data[5],data[6],data[9],data[10],data[12],data[13],data[16],data[17],data[20],data[21],data[24],data[25],data[27],data[28],data[31],data[32],data[35],data[36],data[39],data[40],data[43],data[44],data[47],data[48],data[51],data[52],data[55],data[56],data[58],data[59],data[62],data[63]},^{data[0],data[1],data[3],data[4],data[6],data[8],data[10],data[11],data[13],data[15],data[17],data[19],data[21],data[23],data[25],data[26],data[28],data[30],data[32],data[34],data[36],data[38],data[40],data[42],data[44],data[46],data[48],data[50],data[52],data[54],data[56],data[57],data[59],data[61],data[63]}};end
 endfunction
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
 ot_hbm_w2_protected_bank_veto_on #(.WORDS(N),.STAGE(PREENC),.DIST(DIST)) u_state(
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
