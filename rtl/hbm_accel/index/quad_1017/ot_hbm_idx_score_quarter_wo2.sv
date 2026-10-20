`default_nettype none
// HBM d4g IDX QUARTER SCORER, wires-only form r4 (L2H-IDXSCORE 2026-10-19): structural successor of
// ot_hbm_idx_score_quarter_wo after the r3 / r10 gate FAILs, under the SAFE-DESIGN checklist (owner 10-19):
//   * every reset port lands in 2 synchroniser stages only (ot_rst_relay_l; r3: qw 4 / qe 3 port sinks);
//   * REGIONAL clocks, one root per leaf row beside that row's register mass: W tile clk_w0 / clk_w1 (= the die's
//     clk_engine[0/1] row clocks), E tile clk_e0 / clk_e1 (= clk_tail[0/1]); crossings between the rows are reg -> reg
//     (same PLL, fixed phase) -- r3 qe had ONE root over 1.12 mm (TT/FF pin-flop spread 177.7 / 156.8 ps);
//   * reach (<= 405 um a cycle): the W tile's shared inputs (query, beat control, keep bitmap) enter at row 0's face
//     sections, so row 1's outputs were one ~560 um hop away; r4 adds a mid stage B per row (A pin capture -> B -> C
//     output pin regs): every leaf input is now +2 edges vs the flat quarter (was +1); relative leaf timeline unchanged.
//     Compiler: --score-chain +1 more (handed to the die schedule, priced in the kit README);
//   * W fault cause wf: row 0 aux carries the full cause (row 0 checks | row 1 key-line check registered in row 1 at B);
//     row 1 aux[29] carries its row's partial (the E tile reads only row 0's wf, as the flat quarter: wf_d[0]);
//   * E tile score split per row (score0 = row 0 fields + ev + last, score1 = row 1 fields) so each row's score regs and
//     pins sit in that row; the parent re-assembles the flat quarter's 306-bit score bus bit-for-bit.
//   * leaves = ot_hbm_idx_score_leaf_c1 (one clock root, landed reset, ring-buffer delays).
// STATIC: no ready / credit; checks are fault-only, as the flat quarter.
module ot_hbm_idx_score_qw_r4 #(parameter integer TP=96,RANK_W=(TP<=1?1:$clog2(TP)))(
 input wire clk_w0,input wire clk_w1,input wire rst_n,input wire half,
 input wire[RANK_W-1:0]rank,input wire[10:0]first_ord,input wire[11:0]nkeys,
 input wire keep_en,input wire[170:0]keep_bitmap,
 input wire ql_v,input wire[7:0]ql_head,input wire[511:0]ql_codes,input wire[31:0]ql_sc,input wire[15:0]ql_w,
 input wire beat_v,input wire[7:0]beat_index,
 input wire[2197:0]key_lines0,input wire[2197:0]key_lines1,
 output wire rst_c0,output wire rst_c1,
 output wire o_qv0,output wire[567:0]o_q0,output wire o_kv0,
 output wire[3:0]o_kkv0,output wire[2175:0]o_key0,output wire[29:0]o_aux0,
 output wire[551:0]o_bus0,
 output wire o_qv1,output wire[567:0]o_q1,output wire o_kv1,
 output wire[3:0]o_kkv1,output wire[2175:0]o_key1,output wire[29:0]o_aux1,
 output wire[551:0]o_bus1
);
 wire[1:0]rst_r;
 ot_rst_relay_l #(.REGIONS(2),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rst(.clk(clk_w0),.rst_n_in(rst_n),.rst_n(rst_r));
 assign rst_c0=rst_r[0];assign rst_c1=rst_r[1];
 // ---- stage A: pin capture (row 0 domain: shared inputs + key lines 0; row 1 domain: key lines 1)
 (* keep *) reg h_r;(* keep *) reg[RANK_W-1:0]rk_r;(* keep *) reg[10:0]fo_r;(* keep *) reg[11:0]nk_r;
 (* keep *) reg ke_r;(* keep *) reg[170:0]kb_r;
 (* keep *) reg qv_r;(* keep *) reg[7:0]qh_r;(* keep *) reg[511:0]qc_r;(* keep *) reg[31:0]qs_r;(* keep *) reg[15:0]qw_r;
 (* keep *) reg bv_r;(* keep *) reg[7:0]bi_r;(* keep *) reg[2197:0]kl0_r;(* keep *) reg[2197:0]kl1_r;
 always @(posedge clk_w0)begin
  h_r<=half;rk_r<=rank;fo_r<=first_ord;nk_r<=nkeys;ke_r<=keep_en;kb_r<=keep_bitmap;
  qv_r<=ql_v;qh_r<=ql_head;qc_r<=ql_codes;qs_r<=ql_sc;qw_r<=ql_w;
  bv_r<=beat_v;bi_r<=beat_index;kl0_r<=key_lines0;
 end
 always @(posedge clk_w1) kl1_r<=key_lines1;
 wire[4395:0]kl_r={kl1_r,kl0_r};
 // W fault cause, split by row: row 0 = beat range + key lines 0/1 headers, row 1 = key lines 2/3 headers
 reg wf0,wf1;
 always @* begin
  wf0=0;wf1=0;
  if(bv_r)begin
   if(nk_r>2736||bi_r>170)wf0=1;
   for(integer j=0;j<4;j=j+1)if(!kl_r[j*1099]||kl_r[j*1099+1+:10]!==10'((4*int'(h_r)+j)*128+int'(bi_r)))begin
    if(j<2)wf0=1;else wf1=1;
   end
  end
 end
 wire[2175:0]keys[0:1];wire[3:0]vk[0:1];wire[24:0]md[0:1];
 wire[19:0]g0=20'(8*TP)*20'(fo_r)+20'(8)*20'(rk_r)+20'(16*TP)*20'(bi_r);
 genvar e,l;
 for(e=0;e<2;e=e+1)begin:ge
  for(l=0;l<4;l=l+1)begin:gl
   localparam integer ll=4*e+l;
`ifdef OT_IDXQS_MUT_KEYLINE
   assign keys[e][l*544+:544]=kl_r[(l/2)*1099+11+(l%2)*544+:544];           // mutant: row 1 reads row 0's key lines
`else
   assign keys[e][l*544+:544]=kl_r[(ll/2)*1099+11+(ll%2)*544+:544];
`endif
   assign vk[e][l]=({4'd0,bi_r}*12'd16+12'(ll)+(h_r?12'd8:12'd0))<nk_r;
  end
  wire[19:0]first=g0+(h_r?20'(8*TP):20'd0)+20'(e*4);
  assign md[e]={(({4'd0,bi_r}+12'd1)*12'd16>=nk_r),first,4'd0};
 end
 // ---- stages B + C per row, in the KEPT non-parameterised module ot_hidx_qw_row (SYNTH_KEEP_MODULES). L2H-IDXSCORE
 // 10-19 r4k: in the one-root tile (clk_w0 = clk_w1) Yosys opt_merge folded every row-1 copy with identical D into row 0's
 // (b_q, b_qv, b_kv, b_md, o_q, o_qv, o_kv, most of o_aux: 568 o_q flops left of 1,136), so o_q0 launched from the row-1
 // flop one ~650 um buffered hop from its pin (gate qw4s_562_w432 reg->out -228 ps). A hierarchy boundary per row keeps
 // both copies. Cycles unchanged: B then C, row e on its own row clock.
 // keep-bit select split across B/C (r4m, L2H-IDXSCORE 10-19 23:20): qw4k_648 worst path was kb_r[bi_r] (171:1 select) from the
 // row-0 A regs over the hop into row 1's B (+11.0 ps). Now A -> B carries the 16 candidates kb_r[{bi_r[7:4],x}] (11:1) plus
 // bi_r[3:0]; each row's B -> C finishes the 16:1 select beside its own pins. Same cycle; bits >170 read 0 (as Verilator did).
 wire[255:0]kb_p={85'd0,kb_r};wire[15:0]ks=kb_p[{bi_r[7:4],4'd0}+:16];
 wire b_wf0,b_wf1;wire[28:0]b_ak0,b_ak1;wire[29:0]r0_aux;
 ot_hidx_qw_row u_row0(.clk(clk_w0),.qv(qv_r),.q({qh_r,qc_r,qs_r,qw_r}),.kv(bv_r),.kkv(vk[0]),.ks(ks),.blo(bi_r[3:0]),.ke(ke_r),.key(keys[0]),
  .md(md[0]),.wf(wf0),.wf_c(b_wf0|b_wf1),.b_wf_o(b_wf0),.b_ak_o(b_ak0),.o_qv(o_qv0),.o_q(o_q0),.o_kv(o_kv0),.o_kkv(o_kkv0),
  .o_key(o_key0),.o_aux(r0_aux));
 ot_hidx_qw_row u_row1(.clk(clk_w1),.qv(qv_r),.q({qh_r,qc_r,qs_r,qw_r}),.kv(bv_r),.kkv(vk[1]),.ks(ks),.blo(bi_r[3:0]),.ke(ke_r),.key(keys[1]),
  .md(md[1]),.wf(wf1),.wf_c(b_wf1),.b_wf_o(b_wf1),.b_ak_o(b_ak1),.o_qv(o_qv1),.o_q(o_q1),.o_kv(o_kv1),.o_kkv(o_kkv1),
  .o_key(o_key1),.o_aux(o_aux1));
`ifdef OT_IDXQS_MUT_AUXEARLY
 assign o_aux0={b_wf0|b_wf1,b_ak0};                                           // mutant: row 0 aux one edge early
`else
 assign o_aux0=r0_aux;
`endif
 assign o_bus0='0;assign o_bus1='0;
endmodule

// One W-tile row's B (mid) + C (output pin) stages. Non-parameterised so the kit's SYNTH_KEEP_MODULES name matches (a
// parameterised module is renamed $paramod and the keep misses it). o_aux = {wf_c, md, kk} at C; b_wf_o / b_ak_o = the
// B-stage fault cause and {md, kk} (row 0 ORs both rows' B wf into its aux; the AUXEARLY mutant reads b_ak_o).
module ot_hidx_qw_row(
 input wire clk,
 input wire qv,input wire[567:0]q,input wire kv,input wire[3:0]kkv,input wire[15:0]ks,input wire[3:0]blo,input wire ke,
 input wire[2175:0]key,
 input wire[24:0]md,input wire wf,input wire wf_c,
 output wire b_wf_o,output wire[28:0]b_ak_o,
 output reg o_qv,output reg[567:0]o_q,output reg o_kv,output reg[3:0]o_kkv,output reg[2175:0]o_key,output reg[29:0]o_aux
);
 reg b_qv,b_kv,b_wf,b_ke;reg[567:0]b_q;reg[3:0]b_kkv,b_blo;reg[15:0]b_ks;reg[2175:0]b_key;reg[24:0]b_md;
 wire[3:0]b_kk={4{!b_ke||b_ks[b_blo]}};
 always @(posedge clk)begin
  b_qv<=qv;b_q<=q;b_kv<=kv;b_kkv<=kkv;b_ks<=ks;b_blo<=blo;b_ke<=ke;b_key<=key;b_md<=md;b_wf<=wf;
 end
 always @(posedge clk)begin
  o_qv<=b_qv;o_q<=b_q;o_kv<=b_kv;o_kkv<=b_kkv;o_key<=b_key;o_aux<={wf_c,b_md,b_kk};
 end
 assign b_wf_o=b_wf;assign b_ak_o={b_md,b_kk};
endmodule

module ot_hbm_idx_score_qe_r4(
 input wire clk_e0,input wire clk_e1,input wire rst_n,
 input wire r0_qv,input wire r0_kv,input wire[29:0]r0_aux,input wire[551:0]r0_bus,
 input wire r1_qv,input wire r1_kv,input wire[29:0]r1_aux,input wire[551:0]r1_bus,
 // score0 = {idx row 0 (80), val row 0 (64), kv row 0 (4), fl row 0 (4), last row 0, ev row 0}; score1 = row 1 fields
 output reg[153:0]score0,output reg[151:0]score1,output reg fault
);
 localparam integer SW = 1 + 1 + 4 + 128 + 4, AUXW = 30, NK = 4, NCH = 4;
 wire[1:0]rst_e;
 ot_rst_relay_l #(.REGIONS(2),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rst(.clk(clk_e0),.rst_n_in(rst_n),.rst_n(rst_e));
 wire[1:0]ev,efault,wf_d;wire[7:0]kv,fl;wire[127:0]val;wire[159:0]idx;wire[1:0]last;
 wire rq[0:1],rk[0:1];wire[AUXW-1:0]ra[0:1];wire[4*SW-1:0]rb[0:1];wire eck[0:1];
 assign rq[0]=r0_qv;assign rk[0]=r0_kv;assign ra[0]=r0_aux;assign eck[0]=clk_e0;
 assign rq[1]=r1_qv;assign rk[1]=r1_kv;assign ra[1]=r1_aux;assign eck[1]=clk_e1;
`ifdef OT_IDXQS_MUT_ROWSWAP
 assign rb[0]=r1_bus;assign rb[1]=r0_bus;                                     // mutant: the two rows' sum buses swapped
`else
 assign rb[0]=r0_bus;assign rb[1]=r1_bus;
`endif
 genvar e,c,l;
 for(e=0;e<2;e=e+1)begin:ge
  wire eclk=eck[e]; wire rst_c=rst_e[e];
  wire qv_e=rq[e], kv_e=rk[e]; wire [AUXW-1:0] aux_e=ra[e]; wire [4*SW-1:0] bus_e=rb[e];
  wire [3:0] keep_d;
  ot_hdc_delay_rf #(.W(4),.D(106)) keep_pipe(.clk(eclk),.rst_n(rst_c),.d(aux_e[3:0]),.q(keep_d));
  wire [3:0] son, sv; wire [3:0] skv [0:3]; wire [127:0] ssum [0:3]; wire [3:0] sfl [0:3];
  for(c=0;c<4;c=c+1)begin:gs
   assign {son[c], sv[c], skv[c], ssum[c], sfl[c]} = bus_e[c*SW +: SW];
  end
  reg [3:0] ready1,ready2; reg online_q; reg fault_q; reg [1:0] settle;
  always @(posedge eclk or negedge rst_c)begin
   if(!rst_c)begin ready1<=0;ready2<=0;online_q<=0;fault_q<=0;settle<=0;end
   else begin
    if(qv_e)settle<=3;else if(settle!=0)settle<=settle-1;
    ready1<=son;ready2<=ready1;online_q<=&ready2;
    if(kv_e && (!online_q||qv_e||settle!=0))fault_q<=1;
   end
  end
  assign efault[e]=fault_q;
  wire [NK*NCH*32-1:0] tsum; wire [NK*NCH-1:0] tfl;
  for(l=0;l<NK;l=l+1)begin:g_transpose
   for(c=0;c<NCH;c=c+1)begin:g_chunk
    assign tsum[(l*NCH+c)*32+:32]=ssum[c][32*l+:32];
    assign tfl[l*NCH+c]=sfl[c][l];
   end
  end
  wire tv; wire [NK-1:0] tkv, tf; wire [NK*16-1:0] ts;
  ot_hbm_idx_tail_native u_t (.clk(eclk), .rst_n(rst_c), .i_v(sv[0]), .i_kv(skv[0]),
   .i_keep(keep_d), .i_sum(tsum), .i_fault(tfl), .o_v(tv), .o_kv(tkv), .o_score(ts), .o_fault(tf));
  reg ov; reg [3:0] ok, ofl; reg [63:0] os;
  always @(posedge eclk or negedge rst_c) if(!rst_c) ov<=0; else ov<=tv;
  always @(posedge eclk) begin ok<=tkv; os<=ts; ofl<=tf; end
  assign ev[e]=ov; assign kv[e*4+:4]=ok; assign val[e*64+:64]=os;
  wire[24:0]meta;
  hidx_meta_w25_d123_r0 md(.clk(eclk),.rst_n(rst_c),.d(aux_e[28:4]),.q(meta));
  for(l=0;l<4;l=l+1)begin:go
   assign idx[(e*4+l)*20+:20]=meta[23:4]+20'(l);
  end
  assign last[e]=meta[24];
  assign fl[e*4+:4]=ofl|meta[3:0];
  assign wf_d[e]=aux_e[29];
 end
 // row 0 score register + fault (clk_e0), row 1 score register (clk_e1); fault reads row 1's ev / fault reg -> reg
 always @(posedge clk_e0 or negedge rst_e[0])
  if(!rst_e[0])score0[0]<=1'b0; else score0[0]<=ev[0];
 always @(posedge clk_e0)score0[153:1]<={idx[79:0],val[63:0],kv[3:0],fl[3:0],last[0]};
 always @(posedge clk_e1)score1<={idx[159:80],val[127:64],kv[7:4],fl[7:4]};
 always @(posedge clk_e0 or negedge rst_e[0])begin
  if(!rst_e[0])fault<=0;
  else if((|efault)||(ev[1]!=ev[0])||wf_d[0])fault<=1;
 end
endmodule

// wires-only parent r4: the flat quarter's data ports; clocks = the die's row clocks (no unused clock port)
module ot_hbm_idx_score_quarter_wo2 #(parameter integer TP=96,RANK_W=(TP<=1?1:$clog2(TP)))(
 input wire[1:0]clk_engine,input wire[1:0]clk_tail,input wire[7:0]clk_chunk,input wire rst_n,
 input wire half,
 input wire[RANK_W-1:0]rank,input wire[10:0]first_ord,input wire[11:0]nkeys,
 input wire keep_en,input wire[170:0]keep_bitmap,
 input wire ql_v,input wire[7:0]ql_head,input wire[511:0]ql_codes,input wire[31:0]ql_sc,input wire[15:0]ql_w,
 input wire beat_v,input wire[7:0]beat_index,input wire[4395:0]key_lines,
 output wire[305:0]score,output wire fault
);
 localparam integer QW = 568, KW4 = 2176, SW = 138, AUXW = 30, NCH = 4;
 wire rst_c0,rst_c1,w_qv0,w_qv1,w_kv0,w_kv1;wire[QW-1:0]w_q0,w_q1;wire[3:0]w_kkv0,w_kkv1;wire[KW4-1:0]w_key0,w_key1;
 wire[AUXW-1:0]w_aux0,w_aux1;wire[4*SW-1:0]w_bus0,w_bus1;
 ot_hbm_idx_score_qw_r4 #(.TP(TP)) u_w(.clk_w0(clk_engine[0]),.clk_w1(clk_engine[1]),.rst_n(rst_n),.half(half),.rank(rank),
  .first_ord(first_ord),.nkeys(nkeys),.keep_en(keep_en),.keep_bitmap(keep_bitmap),.ql_v(ql_v),.ql_head(ql_head),
  .ql_codes(ql_codes),.ql_sc(ql_sc),.ql_w(ql_w),.beat_v(beat_v),.beat_index(beat_index),.key_lines0(key_lines[2197:0]),
  .key_lines1(key_lines[4395:2198]),.rst_c0(rst_c0),.rst_c1(rst_c1),
  .o_qv0(w_qv0),.o_q0(w_q0),.o_kv0(w_kv0),.o_kkv0(w_kkv0),.o_key0(w_key0),.o_aux0(w_aux0),.o_bus0(w_bus0),
  .o_qv1(w_qv1),.o_q1(w_q1),.o_kv1(w_kv1),.o_kkv1(w_kkv1),.o_key1(w_key1),.o_aux1(w_aux1),.o_bus1(w_bus1));
 wire r_qv[0:1],r_kv[0:1];wire[AUXW-1:0]r_aux[0:1];wire[4*SW-1:0]r_bus[0:1];
 genvar e,c;
 for(e=0;e<2;e=e+1)begin:ge
  wire qv_c [0:NCH]; wire [QW-1:0] q_c [0:NCH]; wire kv_c [0:NCH]; wire [3:0] kkv_c [0:NCH]; wire [KW4-1:0] key_c [0:NCH];
  wire [AUXW-1:0] aux_c [0:NCH]; wire [4*SW-1:0] bus_c [0:NCH];
  assign qv_c[0]=(e==0)?w_qv0:w_qv1; assign q_c[0]=(e==0)?w_q0:w_q1; assign kv_c[0]=(e==0)?w_kv0:w_kv1;
  assign bus_c[0]=(e==0)?w_bus0:w_bus1;
  assign kkv_c[0]=(e==0)?w_kkv0:w_kkv1; assign key_c[0]=(e==0)?w_key0:w_key1; assign aux_c[0]=(e==0)?w_aux0:w_aux1;
  for(c=0;c<NCH;c=c+1)begin:gc
   ot_hbm_idx_score_leaf_c1 #(.AUXW(AUXW)) leaf(.clk(clk_chunk[e*4+c]), .rst_n((e==0)?rst_c0:rst_c1), .hb(8'(8*c)),
    .w_qv(qv_c[c]), .w_q(q_c[c]), .w_kv(kv_c[c]), .w_kkv(kkv_c[c]), .w_key(key_c[c]), .w_aux(aux_c[c]), .w_bus(bus_c[c]),
    .e_qv(qv_c[c+1]), .e_q(q_c[c+1]), .e_kv(kv_c[c+1]), .e_kkv(kkv_c[c+1]), .e_key(key_c[c+1]), .e_aux(aux_c[c+1]),
    .e_bus(bus_c[c+1]));
  end
  assign r_qv[e]=qv_c[NCH]; assign r_kv[e]=kv_c[NCH]; assign r_aux[e]=aux_c[NCH]; assign r_bus[e]=bus_c[NCH];
 end
 wire[153:0]s0;wire[151:0]s1;
 ot_hbm_idx_score_qe_r4 u_e(.clk_e0(clk_tail[0]),.clk_e1(clk_tail[1]),.rst_n(rst_n),
  .r0_qv(r_qv[0]),.r0_kv(r_kv[0]),.r0_aux(r_aux[0]),.r0_bus(r_bus[0]),
  .r1_qv(r_qv[1]),.r1_kv(r_kv[1]),.r1_aux(r_aux[1]),.r1_bus(r_bus[1]),.score0(s0),.score1(s1),.fault(fault));
 // flat score bus {idx[159:0], val[127:0], kv[7:0], fl[7:0], last0, ev0}
 assign score={s1[151:72],s0[153:74],s1[71:8],s0[73:10],s1[7:4],s0[9:6],s1[3:0],s0[5:2],s0[1],s0[0]};
endmodule
`default_nettype wire
