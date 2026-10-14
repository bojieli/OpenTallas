`timescale 1ns/1ps
// HIER station (el1011-hbm-no3 2026-10-11, owner textbook audit class 1/6): the rb station's 2,328-bit payload cut
// (37 W6 words, DIST=1, STAGE=0, RED=1) is split into hardened word-group SLICE tiles and a bank CONTROL core that
// stays in the station top. The logic is the flat station's, regrouped (0 cycles, same Boolean on every edge):
//   slice  : for 8 aligned words (= one RED reduction group) the input pin capture (id_p bits), the encoded seat
//            (grc kept copies of gr, Ew), every word register of ot_hbm_w2_protected_bank_veto_on (code, snapshot,
//            syndrome, checked, verdict, q_d1, the RED r_q stage, q_d2, the u_cp kept enable copies), the S1
//            per-word verdict bits, the RED group reduction register (r_*) and the NO kept output launch copies
//            (u_outq bits). Each slice has its own clock tree when hardened.
//   control: phase word, failed dual rail, S1 phase/ctl bits, the RED phase register, S2 and the cut wrapper.
// Seam signals are registers or decodes of the protected phase register (go_*, ph4) into registers on the far
// side, and the registered group verdicts back: no new combinational depth across the seam, no added edge.
module ot_hbm_w2_stn_slice #(parameter integer NW=8, NB=512, BASE=0, NO=2, QOUT=0)(
 input wire clk,rst_p,rst_e,gr,
 input wire go_commit,go_repair,go_check,go_sel,
 input wire [3:0] ph4,
 input wire [NB-1:0] din,
 output wire [NO*NB-1:0] dout,
 output wire [(QOUT?NW*64:1)-1:0] q,
 output wire v_same,v_bad,v_cbad,v_ce,v_ue,v_clean,
 output wire [NW-1:0] grc_o);   // kept seat copies: the copy check (vs gr_d) stays in the control core
function automatic [71:0] encode64(input [63:0] data);
  begin encode64={^{data[63],data[62],data[61],data[60],data[59],data[58],data[57],^{data[57],data[58],data[59],data[60],data[61],data[62],data[63]},data[56],data[55],data[54],data[53],data[52],data[51],data[50],data[49],data[48],data[47],data[46],data[45],data[44],data[43],data[42],data[41],data[40],data[39],data[38],data[37],data[36],data[35],data[34],data[33],data[32],data[31],data[30],data[29],data[28],data[27],data[26],^{data[26],data[27],data[28],data[29],data[30],data[31],data[32],data[33],data[34],data[35],data[36],data[37],data[38],data[39],data[40],data[41],data[42],data[43],data[44],data[45],data[46],data[47],data[48],data[49],data[50],data[51],data[52],data[53],data[54],data[55],data[56]},data[25],data[24],data[23],data[22],data[21],data[20],data[19],data[18],data[17],data[16],data[15],data[14],data[13],data[12],data[11],^{data[11],data[12],data[13],data[14],data[15],data[16],data[17],data[18],data[19],data[20],data[21],data[22],data[23],data[24],data[25],data[41],data[42],data[43],data[44],data[45],data[46],data[47],data[48],data[49],data[50],data[51],data[52],data[53],data[54],data[55],data[56]},data[10],data[9],data[8],data[7],data[6],data[5],data[4],^{data[4],data[5],data[6],data[7],data[8],data[9],data[10],data[18],data[19],data[20],data[21],data[22],data[23],data[24],data[25],data[33],data[34],data[35],data[36],data[37],data[38],data[39],data[40],data[49],data[50],data[51],data[52],data[53],data[54],data[55],data[56]},data[3],data[2],data[1],^{data[1],data[2],data[3],data[7],data[8],data[9],data[10],data[14],data[15],data[16],data[17],data[22],data[23],data[24],data[25],data[29],data[30],data[31],data[32],data[37],data[38],data[39],data[40],data[45],data[46],data[47],data[48],data[53],data[54],data[55],data[56],data[60],data[61],data[62],data[63]},data[0],^{data[0],data[2],data[3],data[5],data[6],data[9],data[10],data[12],data[13],data[16],data[17],data[20],data[21],data[24],data[25],data[27],data[28],data[31],data[32],data[35],data[36],data[39],data[40],data[43],data[44],data[47],data[48],data[51],data[52],data[55],data[56],data[58],data[59],data[62],data[63]},^{data[0],data[1],data[3],data[4],data[6],data[8],data[10],data[11],data[13],data[15],data[17],data[19],data[21],data[23],data[25],data[26],data[28],data[30],data[32],data[34],data[36],data[38],data[40],data[42],data[44],data[46],data[48],data[50],data[52],data[54],data[56],data[57],data[59],data[61],data[63]}},data[63],data[62],data[61],data[60],data[59],data[58],data[57],^{data[57],data[58],data[59],data[60],data[61],data[62],data[63]},data[56],data[55],data[54],data[53],data[52],data[51],data[50],data[49],data[48],data[47],data[46],data[45],data[44],data[43],data[42],data[41],data[40],data[39],data[38],data[37],data[36],data[35],data[34],data[33],data[32],data[31],data[30],data[29],data[28],data[27],data[26],^{data[26],data[27],data[28],data[29],data[30],data[31],data[32],data[33],data[34],data[35],data[36],data[37],data[38],data[39],data[40],data[41],data[42],data[43],data[44],data[45],data[46],data[47],data[48],data[49],data[50],data[51],data[52],data[53],data[54],data[55],data[56]},data[25],data[24],data[23],data[22],data[21],data[20],data[19],data[18],data[17],data[16],data[15],data[14],data[13],data[12],data[11],^{data[11],data[12],data[13],data[14],data[15],data[16],data[17],data[18],data[19],data[20],data[21],data[22],data[23],data[24],data[25],data[41],data[42],data[43],data[44],data[45],data[46],data[47],data[48],data[49],data[50],data[51],data[52],data[53],data[54],data[55],data[56]},data[10],data[9],data[8],data[7],data[6],data[5],data[4],^{data[4],data[5],data[6],data[7],data[8],data[9],data[10],data[18],data[19],data[20],data[21],data[22],data[23],data[24],data[25],data[33],data[34],data[35],data[36],data[37],data[38],data[39],data[40],data[49],data[50],data[51],data[52],data[53],data[54],data[55],data[56]},data[3],data[2],data[1],^{data[1],data[2],data[3],data[7],data[8],data[9],data[10],data[14],data[15],data[16],data[17],data[22],data[23],data[24],data[25],data[29],data[30],data[31],data[32],data[37],data[38],data[39],data[40],data[45],data[46],data[47],data[48],data[53],data[54],data[55],data[56],data[60],data[61],data[62],data[63]},data[0],^{data[0],data[2],data[3],data[5],data[6],data[9],data[10],data[12],data[13],data[16],data[17],data[20],data[21],data[24],data[25],data[27],data[28],data[31],data[32],data[35],data[36],data[39],data[40],data[43],data[44],data[47],data[48],data[51],data[52],data[55],data[56],data[58],data[59],data[62],data[63]},^{data[0],data[1],data[3],data[4],data[6],data[8],data[10],data[11],data[13],data[15],data[17],data[19],data[21],data[23],data[25],data[26],data[28],data[30],data[32],data[34],data[36],data[38],data[40],data[42],data[44],data[46],data[48],data[50],data[52],data[54],data[56],data[57],data[59],data[61],data[63]}};end
 endfunction
function automatic [63:0] raw64(input [71:0] c);
  begin raw64={c[70],c[69],c[68],c[67],c[66],c[65],c[64],c[62],c[61],c[60],c[59],c[58],c[57],c[56],c[55],c[54],c[53],c[52],c[51],c[50],c[49],c[48],c[47],c[46],c[45],c[44],c[43],c[42],c[41],c[40],c[39],c[38],c[37],c[36],c[35],c[34],c[33],c[32],c[30],c[29],c[28],c[27],c[26],c[25],c[24],c[23],c[22],c[21],c[20],c[19],c[18],c[17],c[16],c[14],c[13],c[12],c[11],c[10],c[9],c[8],c[6],c[5],c[4],c[2]};end
 endfunction
function automatic [7:0] check72(input [71:0] c);
  begin check72={^c,^{c[63],c[64],c[65],c[66],c[67],c[68],c[69],c[70]},^{c[31],c[32],c[33],c[34],c[35],c[36],c[37],c[38],c[39],c[40],c[41],c[42],c[43],c[44],c[45],c[46],c[47],c[48],c[49],c[50],c[51],c[52],c[53],c[54],c[55],c[56],c[57],c[58],c[59],c[60],c[61],c[62]},^{c[15],c[16],c[17],c[18],c[19],c[20],c[21],c[22],c[23],c[24],c[25],c[26],c[27],c[28],c[29],c[30],c[47],c[48],c[49],c[50],c[51],c[52],c[53],c[54],c[55],c[56],c[57],c[58],c[59],c[60],c[61],c[62]},^{c[7],c[8],c[9],c[10],c[11],c[12],c[13],c[14],c[23],c[24],c[25],c[26],c[27],c[28],c[29],c[30],c[39],c[40],c[41],c[42],c[43],c[44],c[45],c[46],c[55],c[56],c[57],c[58],c[59],c[60],c[61],c[62]},^{c[3],c[4],c[5],c[6],c[11],c[12],c[13],c[14],c[19],c[20],c[21],c[22],c[27],c[28],c[29],c[30],c[35],c[36],c[37],c[38],c[43],c[44],c[45],c[46],c[51],c[52],c[53],c[54],c[59],c[60],c[61],c[62],c[67],c[68],c[69],c[70]},^{c[1],c[2],c[5],c[6],c[9],c[10],c[13],c[14],c[17],c[18],c[21],c[22],c[25],c[26],c[29],c[30],c[33],c[34],c[37],c[38],c[41],c[42],c[45],c[46],c[49],c[50],c[53],c[54],c[57],c[58],c[61],c[62],c[65],c[66],c[69],c[70]},^{c[0],c[2],c[4],c[6],c[8],c[10],c[12],c[14],c[16],c[18],c[20],c[22],c[24],c[26],c[28],c[30],c[32],c[34],c[36],c[38],c[40],c[42],c[44],c[46],c[48],c[50],c[52],c[54],c[56],c[58],c[60],c[62],c[64],c[66],c[68],c[70]}};end
 endfunction
 localparam integer PW=2328;
 localparam [2:0] P_CHECK=0,P_VERIFY=1,P_EVAL=2,P_REPAIR=3,P_COMMIT=4;
 // ---- input pin capture (no logic before the flop) and the raw seat words (bit PW is the cut's valid 1)
 reg [NB-1:0] id_p;
 always @(posedge clk)id_p<=din;
 wire [NW*64-1:0] raw_in;
 for(genvar b=0;b<NW*64;b=b+1)begin:rawb
  if(b<NB)begin:pin assign raw_in[b]=id_p[b]; end
  else begin:cst assign raw_in[b]=(BASE*64+b==PW)?1'b1:1'b0; end
 end
 // ---- encoded seat (GRANT_SEAT=1 form): kept grc copy per word, written on every granted edge
 wire [NW-1:0] grc;
 reg [71:0] Ew[0:NW-1];
 for(genvar w=0;w<NW;w=w+1)begin:seat
  ot_hbm_w2_keep_reg #(.W(1)) u_c(.clk(clk),.rst_n(rst_e),.d(gr),.q(grc[w]));
  always @(posedge clk)if(grc[w])Ew[w]<=encode64(raw_in[w*64+:64]);
 end
 assign grc_o=grc;
 // ---- payload bank words (ot_hbm_w2_protected_bank_veto_on, STAGE=0 DIST=1 RED=1 LOCAL_PHASE=0 HOLD_SEAT=0)
 reg [71:0] code[0:NW-1];
 reg [71:0] snapshot_lo[0:NW-1],snapshot_hi[0:NW-1];
 reg [71:0] syndrome[0:NW-1];
 reg [71:0] checked_lo[0:NW-1],checked_hi[0:NW-1],checked_syn[0:NW-1];
 reg [71:0] verdict[0:NW-1];
 reg [63:0] q_d1[0:NW-1],q_d2[0:NW-1],r_q[0:NW-1];
 wire [NW-1:0] com_q,rep_q,chk_q,ver_q,sel_q;
 reg [NW-1:0] s_same,s_bad,s_cbad,s_ce,s_ue,s_clean;
 reg r_same,r_bad,r_cbad,r_ce,r_ue,r_clean;
 wire [NW-1:0] same,bad,cbad,ce,ue,clean,input_bad;
 wire [71:0] snap[0:NW-1];
 wire [7:0] syn[0:NW-1];
 wire [2:0] wp=ph4[2:0]; wire ws=ph4[3];
 wire [NW*64-1:0] qv;
 for(genvar g=0;g<NW;g=g+1)begin:word
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
  assign cbad[g]=(com_q[g]!=(wp==P_COMMIT)) || (rep_q[g]!=(wp==P_REPAIR)) ||
                 (chk_q[g]!=(wp==P_CHECK)) || (ver_q[g]!=(wp==P_VERIFY)) ||
                 (sel_q[g]!=(wp==P_COMMIT && ws));
  assign ce[g]=v[1];assign ue[g]=v[2];assign clean[g]=v[0];
  assign qv[g*64+:64]=q_d2[g];
  ot_hbm_w2_keep_reg #(.W(5),.RV(5'b10000)) u_cp(.clk(clk),.rst_n(rst_p),
   .d({go_commit,go_repair,go_check|com_q[g]|rep_q[g],chk_q[g],go_sel}),
   .q({com_q[g],rep_q[g],chk_q[g],ver_q[g],sel_q[g]}));
 end
 always @(posedge clk or negedge rst_p)
  if(!rst_p)begin
   s_same<=0;s_bad<=0;s_cbad<=0;s_ce<=0;s_ue<=0;s_clean<=0;
   r_same<=0;r_bad<=0;r_cbad<=0;r_ce<=0;r_ue<=0;r_clean<=0;
  end else begin
   s_same<=same;s_bad<=bad;s_cbad<=cbad;s_ce<=ce;s_ue<=ue;s_clean<=clean;
   r_same<=&s_same;r_bad<=|s_bad;r_cbad<=|s_cbad;r_ce<=|s_ce;r_ue<=|s_ue;r_clean<=&s_clean;
  end
 assign v_same=r_same;assign v_bad=r_bad;assign v_cbad=r_cbad;assign v_ce=r_ce;assign v_ue=r_ue;assign v_clean=r_clean;
 integer i;
 always @(posedge clk)begin
  for(i=0;i<NW;i=i+1)begin
   q_d1[i]<=raw64(code[i]);r_q[i]<=q_d1[i];q_d2[i]<=r_q[i];
   if(com_q[i])code[i]<=sel_q[i]?Ew[i]:72'b0;
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
 if(QOUT)begin:qo assign q=qv; end else begin:nq assign q=1'b0; end
 // ---- kept output launch copies (one per branch, never merged): P_d bits of this slice
 for(genvar t=0;t<NO;t=t+1)begin:branch
  ot_hbm_w2_keep_dreg #(.W(NB)) u_outq(.clk(clk),.d(qv[NB-1:0]),.q(dout[t*NB+:NB]));
 end
endmodule

// Payload bank CONTROL + cut wrapper (W=2328, NG groups): the non-word part of ot_hbm_w2_protected_bank_veto_on
// (WORDS=37, STAGE=0, DIST=1, RED=1, fatal=0) and of ot_hbm_w2_protected_cut_veto_on (PREENC=0).
module ot_hbm_w2_stn_payload_ctl #(parameter integer NG=5)(
 input wire clk,por_n,in_v,out_r,valid,
 input wire [NG-1:0] g_same,g_bad,g_cbad,g_ce,g_ue,g_clean,
 output wire in_r,out_v,empty,fault,
 output wire go_commit,go_repair,go_check,go_sel,
 output wire [3:0] ph4);
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
 reg [71:0] phase_code;
 (* keep=1, dont_touch=1 *) reg failed,failed_n;
 reg [2:0] s_ph;reg s_ctlbad;reg [2:0] r_ph;reg r_ctlbad;
 reg [2:0] ph2;reg f2,n2,same2,ce2;
 wire [63:0] phase_raw=raw64(phase_code);
 wire [2:0] phase=phase_raw[2:0];
 wire sel_bit=phase_raw[3];
 wire control_bad=check72(phase_code)!=0 || phase_raw[63:4]!=0 ||
                  (sel_bit && phase!=P_COMMIT && phase!=P_PCOMMIT);
 wire fatal=1'b0;
 wire freeze=failed || failed==failed_n || f2 || fatal;
 reg [2:0] phase_next;reg sel_next;
 wire [NG-1:0] m_same=g_same,m_bad=g_bad,m_cbad=g_cbad,m_ce=g_ce,m_ue=g_ue,m_clean=g_clean;
 wire [2:0] m_ph=r_ph;wire m_ctlbad=r_ctlbad;
 assign fault=failed || failed==failed_n || f2;
 wire normal=n2 && phase==P_EVAL && !failed && failed_n && !fatal;
 // cut wrapper
 assign in_r=normal&&(!valid||out_r);
 assign out_v=normal&&valid;
 assign empty=normal&&!valid;
 wire load=in_r&&(in_v||valid);wire load_sel=in_v;
 wire settled=phase==P_EVAL && ph2==P_EVAL && !freeze;
 wire d_check=settled && !same2;
 wire d_repair=settled && same2 && ce2;
 wire d_commit=settled && same2 && !ce2 && normal && load;
 always @*begin
  phase_next=phase;sel_next=(phase==P_COMMIT||phase==P_PCOMMIT)&&sel_bit;
  if(!freeze)case(phase)
   P_CHECK:phase_next=P_VERIFY;
   P_VERIFY:phase_next=P_EVAL;
   P_EVAL:if(d_check)phase_next=P_PCHECK;
          else if(d_repair)phase_next=P_PREPAIR;
          else if(d_commit)begin phase_next=P_PCOMMIT;sel_next=load_sel;end
   P_REPAIR,P_COMMIT:begin phase_next=P_CHECK;sel_next=0;end
   P_PCHECK:phase_next=P_CHECK;
   P_PCOMMIT:phase_next=P_COMMIT;
   P_PREPAIR:phase_next=P_REPAIR;
   default:phase_next=phase;
  endcase
 end
 assign go_commit=(phase==P_PCOMMIT);
 assign go_repair=(phase==P_PREPAIR);
 assign go_check=(phase==P_PCHECK);
 assign go_sel=(phase==P_PCOMMIT && sel_bit);
 assign ph4={sel_bit,phase};
 always @(posedge clk or negedge por_n)begin
  if(!por_n)begin
   failed<=0;failed_n<=1;
   phase_code<=encode64({61'b0,P_COMMIT});
   s_ph<=P_COMMIT;s_ctlbad<=0;r_ph<=P_COMMIT;r_ctlbad<=0;
   ph2<=P_COMMIT;f2<=0;n2<=0;same2<=0;ce2<=0;
  end else begin
   s_ph<=phase;s_ctlbad<=control_bad;
   r_ph<=s_ph;r_ctlbad<=s_ctlbad;
   ph2<=m_ph;same2<=&m_same;ce2<=|m_ce;
   f2<=m_ctlbad || (|m_cbad) || ((m_ph==P_EVAL||m_ph==P_REPAIR) && (|m_bad)) ||
       (m_ph==P_EVAL && (&m_same) && (|m_ue)) || (m_ph==P_REPAIR && !(&m_same));
   n2<=!(m_ctlbad || (|m_cbad) || (m_ph==P_EVAL && (|m_bad)) || (m_ph==P_EVAL && (&m_same) && (|m_ue))) &&
       m_ph==P_EVAL && (&m_same) && (&m_clean);
   if(freeze)begin failed<=1;failed_n<=0;end
   else phase_code<=encode64({60'b0,sel_next,phase_next});
  end
 end
endmodule

// Hardened slice masters (fixed geometry, one name per view): slice8 = any of words 0..31 (8 aligned words, all data
// bits real: BASE only selects constant bits >= NB, none here), slice5 = words 32..36 (280 data bits, the cut valid
// bit 2328 constant inside, q exported for owner0/frame0/valid).
module ot_hbm_w2_stn_slice8 #(parameter integer NO=2)(
 input wire clk,rst_p,rst_e,gr,go_commit,go_repair,go_check,go_sel,input wire [3:0] ph4,
 input wire [511:0] din,output wire [NO*512-1:0] dout,
 output wire v_same,v_bad,v_cbad,v_ce,v_ue,v_clean,output wire [7:0] grc_o);
 ot_hbm_w2_stn_slice #(.NW(8),.NB(512),.BASE(0),.NO(NO),.QOUT(0)) u(.clk(clk),.rst_p(rst_p),.rst_e(rst_e),.gr(gr),
  .go_commit(go_commit),.go_repair(go_repair),.go_check(go_check),.go_sel(go_sel),.ph4(ph4),.din(din),.dout(dout),.q(),
  .v_same(v_same),.v_bad(v_bad),.v_cbad(v_cbad),.v_ce(v_ce),.v_ue(v_ue),.v_clean(v_clean),.grc_o(grc_o));
endmodule
module ot_hbm_w2_stn_slice5 #(parameter integer NO=2)(
 input wire clk,rst_p,rst_e,gr,go_commit,go_repair,go_check,go_sel,input wire [3:0] ph4,
 input wire [279:0] din,output wire [NO*280-1:0] dout,output wire [319:0] q,
 output wire v_same,v_bad,v_cbad,v_ce,v_ue,v_clean,output wire [4:0] grc_o);
 ot_hbm_w2_stn_slice #(.NW(5),.NB(280),.BASE(32),.NO(NO),.QOUT(1)) u(.clk(clk),.rst_p(rst_p),.rst_e(rst_e),.gr(gr),
  .go_commit(go_commit),.go_repair(go_repair),.go_check(go_check),.go_sel(go_sel),.ph4(ph4),.din(din),.dout(dout),.q(q),
  .v_same(v_same),.v_bad(v_bad),.v_cbad(v_cbad),.v_ce(v_ce),.v_ue(v_ue),.v_clean(v_clean),.grc_o(grc_o));
endmodule
