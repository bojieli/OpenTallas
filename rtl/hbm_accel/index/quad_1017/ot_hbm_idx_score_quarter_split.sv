`default_nettype none
// HBM d4g IDX QUARTER SCORER, WIRES-ONLY form (lane OWN-IDXSCORE, 2026-10-18). Structural successor of
// ot_hbm_idx_score_quarter_static (same ports, same arithmetic) for the landed-regions standard (owner 10-18): the
// quarter is 1.12 x 2.25 mm of leaves, so it is NOT hardened as one block with one tree; the die binds its children
// directly (wires-only parent, die-level regional clocks and landings):
//   * u_w  = ot_hbm_idx_score_qw_static (W glue tile, clk_ctl): input pin flops, the reset relay (rst_c), the W glue
//            (key line split, valid/keep lanes, meta input, W fault cause) and a REGISTERED output stage, so every
//            tile pin launches from a flop (native audit: no logic behind an output pin). Zero sum-bus word for the row
//            heads (driven by the tile, not tied at the die).
//   * 8 leaves ot_hbm_idx_score_leaf (closed-leaf kit hidx_score_leaf_1017), 2 rows x 4, W->E register chain.
//   * u_e  = ot_hbm_idx_score_qe_static (E glue tile): both rows' E glue verbatim (keep delay, settle/online fault,
//            ot_hbm_idx_tail_native, d123 meta delay), own reset relay (same release edge as rst_c), registered score
//            and fault, as the flat quarter. ONE clock port (the die's E-region clock): the flat quarter's clk_engine /
//            clk_meta / clk_tail / clk_ctl are the same PLL phase; the wires-only parent leaves those ports unused.
// LATENCY vs ot_hbm_idx_score_quarter_static: +1 edge on every leaf input (query, key beats and aux alike: the leaves'
// relative timeline is unchanged), so score and fault leave +1 edge later (compiler: --score-chain +1). Reset release
// unchanged. Bench rtl/test/hbm_idx_static/run_quarter_split_lockstep.sh (old vs new, every edge, +1).
// STATIC: no ready / credit; checks are fault-only, as the flat quarter.
module ot_hbm_idx_score_qw_static #(parameter integer TP=96,RANK_W=(TP<=1?1:$clog2(TP)))(
 input wire clk_ctl,input wire rst_n,input wire half,
 input wire[RANK_W-1:0]rank,input wire[10:0]first_ord,input wire[11:0]nkeys,
 input wire keep_en,input wire[170:0]keep_bitmap,
 input wire ql_v,input wire[7:0]ql_head,input wire[511:0]ql_codes,input wire[31:0]ql_sc,input wire[15:0]ql_w,
 input wire beat_v,input wire[7:0]beat_index,
 // key lines split per leaf row (chunks 0,1 -> row 0, chunks 2,3 -> row 1): each half gets its own W-face section beside
 // its row's E-face key pins, so no key bit crosses the 1.12 mm tile height (TW4-IDXSCORE 10-19: r2 trial GRT overflow
 // 147,829 on M3 at the row boundary came from one 4,396-bit W port centred on the face feeding both rows' E sections).
 input wire[2197:0]key_lines0,input wire[2197:0]key_lines1,
 // E face = two row sections (row 0 bottom, row 1 top), each in the leaf's W pin order qv,q,kv,kkv,key,aux,bus, so every
 // row's pins face its own leaf (0,e) W pins: the query / valid / zero-bus words are REPLICATED per row (one flop set
 // per row, beside its pins) instead of one pin driving both rows across the 1.12 mm tile height (TW3-IDXSCORE 10-19).
 output wire rst_c0,output wire rst_c1,
 output reg o_qv0,output reg[567:0]o_q0,output reg o_kv0,
 output reg[3:0]o_kkv0,output reg[2175:0]o_key0,output reg[29:0]o_aux0,
 output wire[551:0]o_bus0,
 output reg o_qv1,output reg[567:0]o_q1,output reg o_kv1,
 output reg[3:0]o_kkv1,output reg[2175:0]o_key1,output reg[29:0]o_aux1,
 output wire[551:0]o_bus1
);
 // one relay region per leaf row (same release edge for both rows)
 wire[1:0]rst_r;
 ot_rst_relay #(.REGIONS(2),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rst(.clk(clk_ctl),.rst_n_in(rst_n),.rst_n(rst_r));
 assign rst_c0=rst_r[0];assign rst_c1=rst_r[1];
 (* keep *) reg h_r;(* keep *) reg[RANK_W-1:0]rk_r;(* keep *) reg[10:0]fo_r;(* keep *) reg[11:0]nk_r;
 (* keep *) reg ke_r;(* keep *) reg[170:0]kb_r;
 (* keep *) reg qv_r;(* keep *) reg[7:0]qh_r;(* keep *) reg[511:0]qc_r;(* keep *) reg[31:0]qs_r;(* keep *) reg[15:0]qw_r;
 (* keep *) reg bv_r;(* keep *) reg[7:0]bi_r;(* keep *) reg[4395:0]kl_r;
 always @(posedge clk_ctl)begin
  h_r<=half;rk_r<=rank;fo_r<=first_ord;nk_r<=nkeys;ke_r<=keep_en;kb_r<=keep_bitmap;
  qv_r<=ql_v;qh_r<=ql_head;qc_r<=ql_codes;qs_r<=ql_sc;qw_r<=ql_w;
  bv_r<=beat_v;bi_r<=beat_index;kl_r<={key_lines1,key_lines0};
 end
 wire[19:0]g0=20'(8*TP)*20'(fo_r)+20'(8)*20'(rk_r)+20'(16*TP)*20'(bi_r);
 reg wf;
 always @* begin
  wf=0;
  if(bv_r)begin
   if(nk_r>2736||bi_r>170)wf=1;
   for(integer j=0;j<4;j=j+1)if(!kl_r[j*1099]||kl_r[j*1099+1+:10]!==10'((4*int'(h_r)+j)*128+int'(bi_r)))wf=1;
  end
 end
 wire[2175:0]keys[0:1];wire[3:0]vk[0:1],kk[0:1];wire[29:0]aux[0:1];
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
   assign kk[e][l]=!ke_r||kb_r[bi_r];
  end
  wire[19:0]first=g0+(h_r?20'(8*TP):20'd0)+20'(e*4);
  wire[24:0]meta_d={(({4'd0,bi_r}+12'd1)*12'd16>=nk_r),first,4'd0};
  assign aux[e]={wf,meta_d,kk[e]};
 end
 // registered output stage: every W-tile output pin launches from a flop (+1 edge on all leaf inputs)
 always @(posedge clk_ctl)begin
  o_qv0<=qv_r;o_q0<={qh_r,qc_r,qs_r,qw_r};o_kv0<=bv_r;
  o_qv1<=qv_r;o_q1<={qh_r,qc_r,qs_r,qw_r};o_kv1<=bv_r;
  o_kkv0<=vk[0];o_key0<=keys[0];
  o_kkv1<=vk[1];o_key1<=keys[1];o_aux1<=aux[1];
 end
`ifdef OT_IDXQS_MUT_AUXEARLY
 always @* o_aux0=aux[0];                                                     // mutant: row 0 aux one edge early
`else
 always @(posedge clk_ctl) o_aux0<=aux[0];
`endif
 assign o_bus0='0;assign o_bus1='0;
endmodule

module ot_hbm_idx_score_qe_static(
 input wire clk,input wire rst_n,
 input wire r0_qv,input wire r0_kv,input wire[29:0]r0_aux,input wire[551:0]r0_bus,
 input wire r1_qv,input wire r1_kv,input wire[29:0]r1_aux,input wire[551:0]r1_bus,
 output reg[305:0]score,output reg fault
);
 localparam integer SW = 1 + 1 + 4 + 128 + 4, AUXW = 30, NK = 4, NCH = 4;
 wire rst_c;
 ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rst(.clk(clk),.rst_n_in(rst_n),.rst_n(rst_c));
 wire[1:0]ev,efault,wf_d;wire[7:0]kv,fl;wire[127:0]val;wire[159:0]idx;wire[1:0]last;
 wire rq[0:1],rk[0:1];wire[AUXW-1:0]ra[0:1];wire[4*SW-1:0]rb[0:1];
 assign rq[0]=r0_qv;assign rk[0]=r0_kv;assign ra[0]=r0_aux;
 assign rq[1]=r1_qv;assign rk[1]=r1_kv;assign ra[1]=r1_aux;
`ifdef OT_IDXQS_MUT_ROWSWAP
 assign rb[0]=r1_bus;assign rb[1]=r0_bus;                                     // mutant: the two rows' sum buses swapped
`else
 assign rb[0]=r0_bus;assign rb[1]=r1_bus;
`endif
 genvar e,c,l;
 for(e=0;e<2;e=e+1)begin:ge
  wire eclk=clk;
  wire qv_e=rq[e], kv_e=rk[e]; wire [AUXW-1:0] aux_e=ra[e]; wire [4*SW-1:0] bus_e=rb[e];
  wire [3:0] keep_d;
  ot_hdc_delay #(.W(4),.D(106)) keep_pipe(.clk(eclk),.rst_n(rst_c),.d(aux_e[3:0]),.q(keep_d));
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
  ot_hbm_idx_tail_native u_t (.clk(clk), .rst_n(rst_c), .i_v(sv[0]), .i_kv(skv[0]),
   .i_keep(keep_d), .i_sum(tsum), .i_fault(tfl), .o_v(tv), .o_kv(tkv), .o_score(ts), .o_fault(tf));
  reg ov; reg [3:0] ok, ofl; reg [63:0] os;
  always @(posedge eclk or negedge rst_c) if(!rst_c) ov<=0; else ov<=tv;
  always @(posedge eclk) begin ok<=tkv; os<=ts; ofl<=tf; end
  assign ev[e]=ov; assign kv[e*4+:4]=ok; assign val[e*64+:64]=os;
  wire[24:0]meta;
  hidx_meta_w25_d123_r0 md(.clk(clk),.rst_n(rst_c),.d(aux_e[28:4]),.q(meta));
  for(l=0;l<4;l=l+1)begin:go
   assign idx[(e*4+l)*20+:20]=meta[23:4]+20'(l);
  end
  assign last[e]=meta[24];
  assign fl[e*4+:4]=ofl|meta[3:0];
  assign wf_d[e]=aux_e[29];
 end
 always @(posedge clk or negedge rst_c)
  if(!rst_c)score[0]<=1'b0; else score[0]<=ev[0];
 always @(posedge clk)score[305:1]<={idx,val,kv,fl,last[0]};
 always @(posedge clk or negedge rst_c)begin
  if(!rst_c)fault<=0;
  else if((|efault)||(ev[1]!=ev[0])||wf_d[0])fault<=1;
 end
endmodule

// wires-only parent: ports identical to ot_hbm_idx_score_quarter_static
module ot_hbm_idx_score_quarter_wo #(parameter integer TP=96,RANK_W=(TP<=1?1:$clog2(TP)))(
 input wire clk_ctl,input wire[1:0]clk_engine,clk_meta,clk_tail,
 input wire[7:0]clk_chunk,input wire[255:0]clk_hslice,input wire rst_n,
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
 ot_hbm_idx_score_qw_static #(.TP(TP)) u_w(.clk_ctl(clk_ctl),.rst_n(rst_n),.half(half),.rank(rank),.first_ord(first_ord),
  .nkeys(nkeys),.keep_en(keep_en),.keep_bitmap(keep_bitmap),.ql_v(ql_v),.ql_head(ql_head),.ql_codes(ql_codes),.ql_sc(ql_sc),
  .ql_w(ql_w),.beat_v(beat_v),.beat_index(beat_index),.key_lines0(key_lines[2197:0]),
  .key_lines1(key_lines[4395:2198]),.rst_c0(rst_c0),.rst_c1(rst_c1),
  .o_qv0(w_qv0),.o_q0(w_q0),.o_kv0(w_kv0),.o_kkv0(w_kkv0),.o_key0(w_key0),.o_aux0(w_aux0),.o_bus0(w_bus0),
  .o_qv1(w_qv1),.o_q1(w_q1),.o_kv1(w_kv1),.o_kkv1(w_kkv1),.o_key1(w_key1),.o_aux1(w_aux1),.o_bus1(w_bus1));
 wire r_qv[0:1],r_kv[0:1];wire[AUXW-1:0]r_aux[0:1];wire[4*SW-1:0]r_bus[0:1];
 genvar e,c,l;
 for(e=0;e<2;e=e+1)begin:ge
  wire qv_c [0:NCH]; wire [QW-1:0] q_c [0:NCH]; wire kv_c [0:NCH]; wire [3:0] kkv_c [0:NCH]; wire [KW4-1:0] key_c [0:NCH];
  wire [AUXW-1:0] aux_c [0:NCH]; wire [4*SW-1:0] bus_c [0:NCH];
  assign qv_c[0]=(e==0)?w_qv0:w_qv1; assign q_c[0]=(e==0)?w_q0:w_q1; assign kv_c[0]=(e==0)?w_kv0:w_kv1;
  assign bus_c[0]=(e==0)?w_bus0:w_bus1;
  assign kkv_c[0]=(e==0)?w_kkv0:w_kkv1; assign key_c[0]=(e==0)?w_key0:w_key1; assign aux_c[0]=(e==0)?w_aux0:w_aux1;
  for(c=0;c<NCH;c=c+1)begin:gc
   wire [15:0] cp;
   for(l=0;l<16;l=l+1)begin:gp
    assign cp[l]=clk_hslice[e*128 + c*32 + 2*l];
   end
   ot_hbm_idx_score_leaf #(.AUXW(AUXW)) leaf(.clk(clk_chunk[e*4+c]), .clk_pair(cp), .rst_n((e==0)?rst_c0:rst_c1), .hb(8'(8*c)),
    .w_qv(qv_c[c]), .w_q(q_c[c]), .w_kv(kv_c[c]), .w_kkv(kkv_c[c]), .w_key(key_c[c]), .w_aux(aux_c[c]), .w_bus(bus_c[c]),
    .e_qv(qv_c[c+1]), .e_q(q_c[c+1]), .e_kv(kv_c[c+1]), .e_kkv(kkv_c[c+1]), .e_key(key_c[c+1]), .e_aux(aux_c[c+1]),
    .e_bus(bus_c[c+1]));
  end
  assign r_qv[e]=qv_c[NCH]; assign r_kv[e]=kv_c[NCH]; assign r_aux[e]=aux_c[NCH]; assign r_bus[e]=bus_c[NCH];
 end
 ot_hbm_idx_score_qe_static u_e(.clk(clk_ctl),.rst_n(rst_n),
  .r0_qv(r_qv[0]),.r0_kv(r_kv[0]),.r0_aux(r_aux[0]),.r0_bus(r_bus[0]),
  .r1_qv(r_qv[1]),.r1_kv(r_kv[1]),.r1_aux(r_aux[1]),.r1_bus(r_bus[1]),.score(score),.fault(fault));
endmodule
`default_nettype wire
