`default_nettype none
// Fixed compiler-issued 5/5/6-bit radix schedule, Q4xW16 production shape. No ready,
// replay, queue, credit or variable-length scan. Owns 12 real 256x256 SRAMs.
// Opcodes: 0idle,1clear frame,2ingest,3hist clear,4hist scan,5choose bin,
// 6compact scan,7flush partial,8emit line. Bins scanned 31..0,31..0,63..0 for passes 0..2. Ingest fuses pass0 histogram.
//
// PIPELINED SUCCESSOR (H-NETLIST/IDXP-SEL 2026-10-16; gate hidx_sel_pr REFUSE: 55-level SRAM->compare->serial
// compaction->buf_q path, 13,468-load reset). Same arithmetic and selection, every stage <= ~20 levels:
//   q domain (clk_q[q]):  S0 op edge t: SRAM read issued.  S1 (t+1): SRAM rd_out registered (rawr).
//     S2 (t+2): orderkey compare vs threshold (gt/eq per lane) + parallel prefix rank of tie lanes.
//     S3 (t+3): tie-budget recurrence -> choose mask -> selected_line/selected_v register (stream to the link).
//     S4 (t+4): parallel prefix of the choose mask -> constant-index (one-hot AND-OR) dense packing; count.
//     S5 (t+5): dense line rotated by fill (4-level barrel) OR-merged into buf_q; full line -> write register.
//     S6 (t+6): registered SRAM write (pack line or op7 flush line).
//   histogram (q): H1 lane bin/match register (from in_line on op2, from rawr on op4), H2 per-bin 16-lane popcount
//     register, H3 hist += count (clear op3 registered one edge, applied in H3).
//   choose (ctl, clk_ctl): A hist[q][addr] read register (q domain), B 4-way sum + prefix sums, C rank recurrence /
//     threshold / found, D tie split (pass 2).  op3's found-clear rides the same A/B pipe.
// Constant latency changes the IDX compiler schedules (tools/hbm_idx_static_calendar.py SEL_CORE table):
//   +2 edges on the selected stream (selected_v/selected_line) -> link;  +2 drain edges after every op4 scan before
//   the first op5 (4 instead of 2);  op7 >= last op6 + 6 (was +2), op8 >= op7 + 2 (unchanged);  out_v +1 edge.
//   op2 ingest -> op5 drain unchanged (2); op5 -> next op3/op4/op6 spacing unchanged (1 idle).
// Reset: rst_n drives only ot_rst_relay (2 sync + 5 region flops on clk_ctl); regions 0..3 = quadrant control,
// 4 = ctl. Datapath registers (lines, histogram, pipeline payload) have no reset: op1/op3 clear what is used.
// SAFE FANOUT SUCCESSOR (LEAD2-HBM/L2H-IDXSEL 2026-10-19; route hidx_sel_g4p-g4p-90b8aed47 EARLY_FAIL_SETUP TT -570 ps,
// 8,529 endpoints: ONE pin flop per op/pass/addr/k bit fanned out to four quadrants and 12 SRAMs, op_r[0] -> qfault[3]
// 396 ps wire + 896 ps logic). Same arithmetic and selection; structure per the safe-design checklist:
//   P1 (core input +1): nine kept relay copies of the control word {addr,pass,op} (two per quadrant + ctl) and k; the
//       in_line slice of each quadrant passes a relay register (in_p1).  Pin -> P1 -> P2 keeps every hop < 405 um.
//   P2 (core input +2): per-consumer KEPT registered one-hot copies (ot_hidx_sel_rep, non-parameterised, kept by
//       SYNTH_KEEP_MODULES so opt_merge cannot fold them back): per lane (16/quadrant) the op2 write/hist selects, the
//       op1|op7 / op7 line clears, and the lane's own copies of the internal emit (s1) and pack (s4) valids; per SRAM
//       re/ing/addr; per 8 histogram bins the clear/add enables; per 2 histogram read bits an addr copy; per 4 lanes a
//       threshold copy.  No register drives more than ~40 loads; in_line passes a second relay (in_p2).
//   S2/S3/S4 prefix ranks are 4-lane local counts + group bases (log depth), not 16-step serial chains.
//   qfault: hazard terms, the 16 per-lane source-order compares and the count checks are registered one edge
//       before the sticky OR (fault +1 edge; diagnostic only).  out_line's valid bit uses a registered 16-lane mask.
// Latency: every core input +2 edges (uniform, so every internal relation is unchanged); the shell adds one more
// output relay stage.  The IDX calendar compiler takes sel_in 1 -> 3 and sel_out 1 -> 2 (PIN table, frame +3 edges).
module ot_hidx_sel_rep(input wire clk,input wire [15:0] d,output reg [15:0] q);
 always @(posedge clk)q<=d;
endmodule
module ot_hbm_idx_selector_static_core #(parameter integer MUT=0)(
 input wire clk_ctl,input wire [3:0] clk_q,input wire [11:0] clk_mem,
 input wire rst_n,input wire [3:0] op,input wire [1:0] pass,
 input wire [7:0] addr,input wire [9:0] k,
 input wire [2367:0] in_line,
 output reg [3:0] out_v,output reg [2367:0] out_line,
 output wire [15:0] threshold_observe,
 output reg [3:0] selected_v,output reg [2367:0] selected_line,
 output wire [55:0] selected_observe,
 output reg fault
);
 localparam integer EW=37,W=16,LW=592;
 function automatic [15:0] orderkey(input [15:0] x);
  orderkey=x[15]?~x:(x^16'h8000);
 endfunction
 function automatic [15:0] pmask(input [1:0] p);
  pmask=(p==0)?16'd0:((p==1)?16'hf800:16'hffc0);
 endfunction
 function automatic [3:0] pshift(input [1:0] p);
  pshift=(p==0)?4'd11:((p==1)?4'd6:4'd0);
 endfunction
 function automatic [15:0] pbins(input [1:0] p);
  pbins=(p==2)?16'd63:16'd31;
 endfunction
 wire [4:0] rr_n;
 ot_rst_relay #(.REGIONS(5),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rr(.clk(clk_ctl),.rst_n_in(rst_n),.rst_n(rr_n));
 wire rc_n=rr_n[4];
 // ---------------- P1: kept relay copies of the control word ----------------
 wire [15:0] cw={2'b0,addr,pass,op};
 wire [15:0] p1[0:8];
 wire [15:0] p1k;
 for(genvar i=0;i<8;i=i+1)begin:gp1
  ot_hidx_sel_rep u(.clk(clk_q[i/2]),.d(cw),.q(p1[i]));
 end
 ot_hidx_sel_rep u_p1c(.clk(clk_ctl),.d(cw),.q(p1[8]));
 ot_hidx_sel_rep u_p1k(.clk(clk_ctl),.d({6'd0,k}),.q(p1k));
 // ---------------- ctl P2 ----------------
 wire [15:0] p2c,p2k;
 ot_hidx_sel_rep u_p2c(.clk(clk_ctl),.d(p1[8]),.q(p2c));
 ot_hidx_sel_rep u_p2k(.clk(clk_ctl),.d(p1k),.q(p2k));
 wire [3:0] c_op=p2c[3:0];wire [1:0] c_pass=p2c[5:4];wire [7:0] c_addr=p2c[13:6];wire [9:0] c_k=p2k[9:0];
 reg [15:0] threshold;
 reg [13:0] rank_left;
 reg found;
 reg [13:0] ties[0:3];
 reg [13:0] selected[0:3];
 reg [3:0] qfault;
 wire [13:0] hrd[0:3];
 assign threshold_observe=threshold;
 // ---------------- ctl: choose-bin pipeline (A: hist read in q domain, B: sums, C: recurrence, D: ties) -------------
 reg a_v,a_clr;reg [1:0] a_pass;reg [5:0] a_addr;
 reg b_v,b_clr;reg [1:0] b_pass;reg [5:0] b_addr;reg [15:0] b_all;reg [15:0] b_s[0:3];reg [13:0] b_h[0:3];
 reg d_go;reg [13:0] d_r;reg [15:0] d_s[0:3];reg [13:0] d_h[0:3];
 // next threshold (the per-quadrant kept copies load the same value on the same edge)
 reg [15:0] thr_n;
 always @*begin
  thr_n=threshold;
  if(c_op==1)thr_n=16'd0;
  if(b_v&&!found&&!({2'b0,rank_left}>b_all))thr_n=(threshold&pmask(b_pass))|(16'(b_addr)<<pshift(b_pass));
  if(!rc_n)thr_n=16'd0;
 end
 always @(posedge clk_ctl or negedge rc_n)begin
  if(!rc_n)begin
   threshold<=0;rank_left<=0;found<=0;fault<=0;a_v<=0;a_clr<=0;b_v<=0;b_clr<=0;d_go<=0;
   for(integer q=0;q<4;q=q+1)ties[q]<=0;
  end else begin
   if(|qfault)fault<=1;
   a_v<=c_op==5;a_clr<=c_op==3;
   b_v<=a_v;b_clr<=a_clr;
   d_go<=0;
   threshold<=thr_n;
   if(c_op==1)begin rank_left<={4'b0,c_k};found<=0;if(c_k>512||c_k==0)fault<=1;end
   if(b_clr)found<=0;
   if(b_v&&!found)begin
    if({2'b0,rank_left}>b_all)rank_left<=rank_left-b_all[13:0];
    else begin
     found<=1;
     if(b_pass==2)d_go<=1;
    end
   end
   if(d_go)for(integer q=0;q<4;q=q+1)begin
    if({2'b0,d_r}<=d_s[q])ties[q]<=0;
    else if({2'b0,d_r}-d_s[q]>={2'b0,d_h[q]})ties[q]<=d_h[q];
    else ties[q]<=14'({2'b0,d_r}-d_s[q]);
   end
   if((c_op==1&&(a_v||b_v))||(c_op==5&&(a_clr||b_clr)))fault<=1;
  end
 end
 always @(posedge clk_ctl)begin
  a_pass<=c_pass;a_addr<=c_addr[5:0];
  b_pass<=a_pass;b_addr<=a_addr;
  for(integer q=0;q<4;q=q+1)b_h[q]<=hrd[q];
  b_s[0]<=16'd0;b_s[1]<=16'(hrd[0]);b_s[2]<=16'(hrd[0])+16'(hrd[1]);
  b_s[3]<=(16'(hrd[0])+16'(hrd[1]))+16'(hrd[2]);
  b_all<=(16'(hrd[0])+16'(hrd[1]))+(16'(hrd[2])+16'(hrd[3]));
  d_r<=rank_left;
  for(integer q=0;q<4;q=q+1)begin d_s[q]<=b_s[q];d_h[q]<=b_h[q];end
 end
 // ---------------- quadrants ----------------
 for(genvar q=0;q<4;q=q+1)begin:gq
  wire rq_n=rr_n[q];
  wire [15:0] pa=p1[2*q],pb=p1[2*q+1];       // P1 copies: a = SRAMs, quadrant control, lanes 0..7; b = lanes 8..15, hist
  // ---- P1 in_line relay and P2 relay (no reset) ----
  reg [LW-1:0] in_p1,in_p2;
  always @(posedge clk_q[q])begin in_p1<=in_line[q*LW+:LW];in_p2<=in_p1;end
  // ---- P2 quadrant control copy ----
  wire [15:0] qc;
  ot_hidx_sel_rep u_qc(.clk(clk_q[q]),.d(pa),.q(qc));
  wire [3:0] qop=qc[3:0];wire [1:0] qpass=qc[5:4];wire [7:0] qaddr=qc[13:6];
  // ---- P2 per-lane copies: 0 ing_w 1 ing_h 2 bclr(op1|op7) 3 fl(op7) 4..6 emit chain 7..13 pack chain ----
  // (mutants: MUT3 lane 5 SRAM write-data select copy one edge late; MUT4 lane 3 emit copy one edge early)
  wire [15:0] lq[0:15];
  for(genvar l=0;l<16;l=l+1)begin:gl
   wire [15:0] src=(l<8)?pa:pb;
   wire [3:0] o=src[3:0];
   wire [15:0] ld;
   assign ld[0]=o==2;assign ld[1]=o==2;assign ld[2]=o==1||o==7;assign ld[3]=o==7;
   assign ld[4]=o==8;assign ld[5]=lq[l][4];
   assign ld[6]=(MUT==4&&l==3)?lq[l][4]:lq[l][5];
   assign ld[7]=o==6;assign ld[8]=lq[l][7];assign ld[9]=lq[l][8];assign ld[10]=lq[l][9];assign ld[11]=lq[l][10];
   assign ld[12]=lq[l][11];assign ld[13]=lq[l][11];
   assign ld[14]=lq[l][0];assign ld[15]=1'b0;           // 14: mutant-only (MUT3 lane-5 write-data select one edge late)
   ot_hidx_sel_rep u_lc(.clk(clk_q[q]),.d(ld),.q(lq[l]));
  end
  // ---- P2 per-SRAM copies: 0 re 1 ing 2..9 addr ----
  wire [15:0] sq[0:2];
  for(genvar m=0;m<3;m=m+1)begin:gs
   ot_hidx_sel_rep u_sc(.clk(clk_q[q]),.d({6'd0,pa[13:6],pa[3:0]==2,pa[3:0]==4||pa[3:0]==6||pa[3:0]==8}),.q(sq[m]));
  end
  // ---- P2 histogram groups (8 bins each): 0 hc0 1 hclr_a 2 hclr_b 3 ing 4..6 scan chain 7 h1v 8 h2v_a 9 h2v_b ----
  wire [15:0] hq[0:7];
  for(genvar g=0;g<8;g=g+1)begin:gh
   wire [15:0] hd;
   assign hd[0]=pb[3:0]==3;assign hd[1]=hq[g][0];assign hd[2]=hq[g][0];assign hd[3]=pb[3:0]==2;
   assign hd[4]=pb[3:0]==4;assign hd[5]=hq[g][4];assign hd[6]=hq[g][5];assign hd[7]=hq[g][3]||hq[g][6];
   assign hd[8]=hq[g][7];assign hd[9]=hq[g][7];assign hd[15:10]=6'd0;
   ot_hidx_sel_rep u_hc(.clk(clk_q[q]),.d(hd),.q(hq[g]));
  end
  // ---- P2 histogram read address: two 6-bit copies per rep (one per 64:1 read-mux output bit) ----
  wire [15:0] haq[0:6];
  for(genvar j=0;j<7;j=j+1)begin:gha
   ot_hidx_sel_rep u_ha(.clk(clk_q[q]),.d({4'd0,pb[11:6],pb[11:6]}),.q(haq[j]));
  end
  // ---- threshold copies: 0..3 compare (4 lanes each), 4 histogram ----
  wire [15:0] thq[0:4];
  for(genvar j=0;j<5;j=j+1)begin:gt
   ot_hidx_sel_rep u_th(.clk(clk_ctl),.d(thr_n),.q(thq[j]));
  end
  wire [767:0] raw;
  reg rv;reg [3:0] rop;reg [1:0] rpass;reg [7:0] raddr;
  reg s1_v;reg [3:0] s1_op;reg [1:0] s1_pass;reg [7:0] s1_addr;reg [LW-1:0] rawr;
  reg s2_v;reg [7:0] s2_addr;reg [LW-1:0] s2_line;reg [15:0] s2_gt,s2_eq;reg [1:0] s2_loc[0:15];reg [2:0] s2_gtot[0:3];
  reg [4:0] s2_ecnt;
  reg s3_v;reg [7:0] s3_addr;
  reg s4_v;reg [7:0] s4_addr;reg [LW-1:0] dense;reg [4:0] dcnt;
  reg [LW-1:0] buf_q;reg [3:0] fill;reg [5:0] wp;
  reg wreq;reg [5:0] wa_r;reg [LW-1:0] wreg;
  reg [13:0] tie_rem;reg comp_started;reg [19:0] last_id;
  reg [7:0] hz;reg [15:0] idbad;reg [15:0] vmask;
  reg [15:0] h1_m;reg [5:0] h1_bin[0:15];
  reg [4:0] h2_cnt[0:63];
  reg [13:0] hist[0:63];
  reg [13:0] hrd_q;
  assign hrd[q]=hrd_q;
  assign selected_observe[q*14+:14]=selected[q];
  // fill copies for the barrel rotate (two reps x four 4-bit copies)
  reg [3:0] fill_n;
  wire [15:0] fq0,fq1;
  ot_hidx_sel_rep u_f0(.clk(clk_q[q]),.d({4{fill_n}}),.q(fq0));
  ot_hidx_sel_rep u_f1(.clk(clk_q[q]),.d({4{fill_n}}),.q(fq1));
  wire [31:0] fq={fq1,fq0};
  // ---- SRAMs: per-SRAM kept control copies; write data selected per lane ----
  wire [LW-1:0] wd;
  for(genvar l=0;l<16;l=l+1)begin:gwd
   assign wd[l*EW+:EW]=((MUT==3&&l==5)?lq[l][14]:lq[l][0])?in_p2[l*EW+:EW]:wreg[l*EW+:EW];
  end
  wire [767:0] wide_wd={176'd0,wd};
  for(genvar m=0;m<3;m=m+1)begin:gm
   ot_sram_1r1w_256x256_m2_r2c2 mem(.clk(clk_mem[q*3+m]),.r_ce_in(sq[m][0]),.r_addr_in(sq[m][9:2]),.rd_out(raw[m*256+:256]),
    .w_ce_in(sq[m][1]||wreq),.w_addr_in(sq[m][1]?sq[m][9:2]:{2'd0,wa_r}),.wd_in(wide_wd[m*256+:256]),.w_mask_in({256{1'b1}}),
    .rr_en(2'd0),.rr_addr(14'd0),.cr_en(2'd0),.cr_sel(16'd0));
  end
  // ---- S2 combinational: compare (threshold copy per 4 lanes) + 4-lane local tie ranks + group totals ----
  reg [15:0] c_gt,c_eq;reg [15:0] c_ky;reg [1:0] c_loc[0:15];reg [2:0] c_gtot[0:3];reg [4:0] c_ecnt;
  always @*begin
   for(integer l=0;l<W;l=l+1)begin
    c_ky=orderkey(rawr[l*EW+1+:16]);
    c_gt[l]=rawr[l*EW]&&(c_ky>thq[l/4]);
    c_eq[l]=rawr[l*EW]&&(c_ky==thq[l/4]);
    if(MUT==1)begin c_gt[l]=rawr[l*EW]&&(c_ky>=thq[l/4]);c_eq[l]=0;end
   end
   for(integer g=0;g<4;g=g+1)begin
    c_loc[4*g]=2'd0;
    c_loc[4*g+1]=2'(c_eq[4*g]);
    c_loc[4*g+2]=2'(c_eq[4*g])+2'(c_eq[4*g+1]);
    c_loc[4*g+3]=(2'(c_eq[4*g])+2'(c_eq[4*g+1]))+2'(c_eq[4*g+2]);
    c_gtot[g]=(3'(c_eq[4*g])+3'(c_eq[4*g+1]))+(3'(c_eq[4*g+2])+3'(c_eq[4*g+3]));
   end
   c_ecnt=(5'(c_gtot[0])+5'(c_gtot[1]))+(5'(c_gtot[2])+5'(c_gtot[3]));
  end
  // ---- S3 combinational: group bases + local rank -> tie budget -> choose mask ----
  wire [13:0] tavail=comp_started?tie_rem:ties[q];
  reg [15:0] c_choose;reg [3:0] c_gb[0:3];reg [4:0] c_er;
  always @*begin
   c_gb[0]=4'd0;c_gb[1]=4'(s2_gtot[0]);c_gb[2]=4'(s2_gtot[0])+4'(s2_gtot[1]);
   c_gb[3]=(4'(s2_gtot[0])+4'(s2_gtot[1]))+4'(s2_gtot[2]);
   for(integer l=0;l<W;l=l+1)begin
    c_er=5'(c_gb[l/4])+5'(s2_loc[l]);
    c_choose[l]=s2_gt[l]||(s2_eq[l]&&({9'd0,c_er}<tavail));
   end
  end
  wire [13:0] tuse=({9'd0,s2_ecnt}<tavail)?{9'd0,s2_ecnt}:tavail;
  // ---- S4 combinational: log-depth prefix positions + one-hot dense pack ----
  reg [15:0] ch;reg [4:0] c_pos[0:15];reg [4:0] c_cnt;reg [LW-1:0] c_dense;reg [1:0] p_loc[0:15];reg [2:0] p_gt[0:3];
  reg [3:0] p_gb[0:3];
  always @*begin
   for(integer l=0;l<W;l=l+1)ch[l]=selected_line[q*LW+l*EW];
   for(integer g=0;g<4;g=g+1)begin
    p_loc[4*g]=2'd0;p_loc[4*g+1]=2'(ch[4*g]);p_loc[4*g+2]=2'(ch[4*g])+2'(ch[4*g+1]);
    p_loc[4*g+3]=(2'(ch[4*g])+2'(ch[4*g+1]))+2'(ch[4*g+2]);
    p_gt[g]=(3'(ch[4*g])+3'(ch[4*g+1]))+(3'(ch[4*g+2])+3'(ch[4*g+3]));
   end
   p_gb[0]=4'd0;p_gb[1]=4'(p_gt[0]);p_gb[2]=4'(p_gt[0])+4'(p_gt[1]);p_gb[3]=(4'(p_gt[0])+4'(p_gt[1]))+4'(p_gt[2]);
   for(integer l=0;l<W;l=l+1)c_pos[l]=5'(p_gb[l/4])+5'(p_loc[l]);
   c_cnt=(5'(p_gt[0])+5'(p_gt[1]))+(5'(p_gt[2])+5'(p_gt[3]));
   c_dense=0;
   for(integer i=0;i<W;i=i+1)for(integer l=i;l<W;l=l+1)
    if(ch[l]&&c_pos[l]==5'(i))c_dense[i*EW+:EW]=c_dense[i*EW+:EW]|selected_line[q*LW+l*EW+:EW];
  end
  // ---- S5 combinational: rotate dense by fill (8 kept fill copies), merge ----
  reg [2*LW-1:0] c_merged;reg [2*LW-1:0] c_sh;
  always @*begin
   for(integer g=0;g<8;g=g+1)begin
    c_sh={{LW{1'b0}},dense}<<(fq[g*4+:4]*EW);
    c_merged[g*(2*LW/8)+:(2*LW/8)]=c_sh[g*(2*LW/8)+:(2*LW/8)];
   end
   c_merged=c_merged|{{LW{1'b0}},buf_q};
  end
  wire [4:0] nf={1'b0,fill}+dcnt;
  always @*begin
   fill_n=fill;
   if(qop==1)fill_n=4'd0;
   if(s4_v)fill_n=(nf>=16)?4'(nf-16):nf[3:0];
   if(qop==7&&fill!=0)fill_n=4'd0;
   if(!rq_n)fill_n=4'd0;
  end
  // ---- histogram H1 combinational (lane copies of the ingest select) ----
  wire h_scan=s1_v&&s1_op==4;
  reg [15:0] c_hm;reg [5:0] c_hb[0:15];reg [15:0] c_hk;reg [1:0] c_hp;reg [EW-1:0] c_hs;
  always @*for(integer l=0;l<W;l=l+1)begin
   c_hs=lq[l][1]?in_p2[l*EW+:EW]:rawr[l*EW+:EW];
   c_hp=lq[l][1]?2'd0:s1_pass;
   c_hk=orderkey(c_hs[1+:16]);
   c_hm[l]=(lq[l][1]||h_scan)&&c_hs[0]&&((c_hk&pmask(c_hp))==(thq[4]&pmask(c_hp)));
   c_hb[l]=6'((c_hk>>pshift(c_hp))&pbins(c_hp));
  end
  reg [4:0] c_hc[0:63];
  always @*for(integer b=0;b<64;b=b+1)begin
   c_hc[b]=0;for(integer l=0;l<W;l=l+1)c_hc[b]=c_hc[b]+5'(h1_m[l]&&h1_bin[l]==6'(b));
  end
  // ---- control registers (reset, region q) ----
  always @(posedge clk_q[q] or negedge rq_n)begin
   if(!rq_n)begin
    rv<=0;s1_v<=0;s2_v<=0;s3_v<=0;s4_v<=0;wreq<=0;fill<=0;wp<=0;tie_rem<=0;comp_started<=0;selected[q]<=0;
    qfault[q]<=0;out_v[q]<=0;selected_v[q]<=0;last_id<=0;h1_m<=0;hz<=0;idbad<=0;
   end else begin
    rv<=qop==4||qop==6||qop==8;s1_v<=rv;
    s2_v<=s1_v&&s1_op==6;
    s3_v<=s2_v;selected_v[q]<=s2_v;
    s4_v<=s3_v;
    out_v[q]<=s1_v&&s1_op==8;
    h1_m<=c_hm;
    wreq<=0;
    fill<=fill_n;
    if(qop==1)begin wp<=0;tie_rem<=0;comp_started<=0;selected[q]<=0;last_id<=0;end
    // S2: source id order (compaction scan); compares registered, OR-ed into qfault next edge
    for(integer l=0;l<W;l=l+1)idbad[l]<=s1_v&&s1_op==6&&rawr[l*EW]&&(s1_addr!=0||l!=0)&&rawr[l*EW+17+:20]<=last_id;
    if(s1_v&&s1_op==6)for(integer l=0;l<W;l=l+1)if(rawr[l*EW])last_id<=rawr[l*EW+17+:20];
    // S3: tie recurrence
    if(s2_v)begin comp_started<=1;tie_rem<=tavail-tuse;end
    // S4: count
    if(s3_v)selected[q]<=selected[q]+14'(c_cnt);
    // S5: pack write request
    if(s4_v&&nf>=16)begin wreq<=1;wa_r<=wp;wp<=wp+1;end
    // op7 flush (live edge): queue the partial line through the same write register
    if(qop==7&&fill!=0)begin wreq<=1;wa_r<=wp;wp<=wp+1;end
    // schedule hazards the compiler must never issue (registered terms, sticky OR one edge later)
    hz[0]<=qop==2&&(rv&&rop==6||s1_v&&s1_op==6||s2_v||s3_v||s4_v||wreq);
    hz[1]<=qop==7&&(rv&&rop==6||s1_v&&s1_op==6||s2_v||s3_v||s4_v);
    hz[2]<=qop==3&&(rv&&rop==4||s1_v&&s1_op==4||hq[0][7]||hq[0][8]);
    hz[3]<=s3_v&&(int'(selected[q])+int'(c_cnt)>512);
    hz[4]<=s4_v&&nf>=16&&({2'd0,wp}>s4_addr);   // never overwrite an unread source line
    hz[7:5]<=3'd0;
    if((|hz)||(|idbad))qfault[q]<=1;
   end
  end
  // ---- datapath registers (no reset); line-wide enables come from the lane copies ----
  always @(posedge clk_q[q])begin
   rop<=qop;rpass<=qpass;raddr<=qaddr;
   s1_op<=rop;s1_pass<=rpass;s1_addr<=raddr;rawr<=raw[LW-1:0];
   for(integer l=0;l<W;l=l+1)vmask[l]<=((int'(raddr)*16+l)<int'(selected[q]));
   s2_addr<=s1_addr;s2_line<=rawr;s2_gt<=c_gt;s2_eq<=c_eq;s2_ecnt<=c_ecnt;
   for(integer l=0;l<W;l=l+1)s2_loc[l]<=c_loc[l];
   for(integer g=0;g<4;g=g+1)s2_gtot[g]<=c_gtot[g];
   s3_addr<=s2_addr;
   for(integer l=0;l<W;l=l+1)begin
    selected_line[q*LW+l*EW+:EW]<=s2_line[l*EW+:EW];selected_line[q*LW+l*EW]<=s2_v&&c_choose[l];
   end
   s4_addr<=s3_addr;dense<=c_dense;dcnt<=s3_v?c_cnt:5'd0;
   for(integer l=0;l<W;l=l+1)begin
    if(lq[l][2])buf_q[l*EW+:EW]<=0;
    else if(lq[l][12])buf_q[l*EW+:EW]<=(nf>=16)?c_merged[LW+l*EW+:EW]:c_merged[l*EW+:EW];
    if(lq[l][3])wreg[l*EW+:EW]<=buf_q[l*EW+:EW];
    else if(lq[l][13])wreg[l*EW+:EW]<=c_merged[l*EW+:EW];
    // emit (S2 from the registered read)
    if(lq[l][6])begin
     out_line[q*LW+l*EW+:EW]<=rawr[l*EW+:EW];
     out_line[q*LW+l*EW]<=vmask[l];
     if(MUT==2&&l==0&&s1_addr==0)out_line[q*LW+l*EW+17+:20]<=rawr[l*EW+17+:20]^20'd1;
    end
   end
   // histogram
   for(integer l=0;l<W;l=l+1)h1_bin[l]<=c_hb[l];
   for(integer b=0;b<64;b=b+1)h2_cnt[b]<=c_hc[b];
   for(integer b=0;b<64;b=b+1)
    hist[b]<=(((b%8)<4)?hq[b/8][1]:hq[b/8][2])?14'd0:hist[b]+((((b%8)<4)?hq[b/8][8]:hq[b/8][9])?14'(h2_cnt[b]):14'd0);
   for(integer j=0;j<14;j=j+1)hrd_q[j]<=hist[(j%2)?haq[j/2][11:6]:haq[j/2][5:0]][j];
  end
 end
endmodule
`default_nettype wire
`default_nettype none
// ---------------------------------------------------------------------------
// PIN-REGISTERED TILE (OWNER RULE 19:50 PT 10-15, H-NETLIST/idxreg 2026-10-16): the die master ot_hbm_idx_selector_static is
// this shell. Every data input passes ONE kept flop at the pin (P0); every output passes the core's register, a relay
// register (o1) and the pin flop (L2H-IDXSEL 10-19: q0/q1 selected_line / out_line travel up to ~500 um to the E / S face,
// so the output path gets one registered hop more).  Clocks pass through; rst_n enters the core's ot_rst_relay.
// Latency (tools/hbm_idx_static_calendar.py PIN table): sel_in = 3 (pin + core P1 + core P2), sel_out = 2.
// REGIONAL ROOTS (L2H-IDXSEL s2, 10-19 23:40): the s1 gates (one clk_ctl root over all 42,772 sinks, std-reg insertion
// 695..998 ps) stalled in CTS hold repair (18-23k endpoints, GATE_STALL at 14,400 s). s2 drives the core's existing clock
// domains from their own ports: quadrant q (its lanes, histogram, pack/emit pipeline and its 3 SRAMs) on clk_q[q], the
// choose pipeline, reset relay and every pin flop on clk_ctl. Crossings: ctl pin flop -> quadrant P1 relay / in_p1 (reg->reg),
// quadrant output -> o1 relay (quadrant domain) -> ctl pin flop (reg->reg), selected[q] -> o1_obs (reg->reg); the ctl
// threshold / tie copies feed quadrant compares and the quadrant histogram read feeds the ctl sums (same PLL, phase 0).
// clk_mem stays a port (parents unchanged) and is unloaded: SRAM (q, m) is clocked by clk_q[q]. Cycles unchanged.
module ot_hbm_idx_selector_static #(parameter integer MUT=0)(
 input wire clk_ctl,input wire [3:0] clk_q,input wire [11:0] clk_mem,
 input wire rst_n,input wire [3:0] op,input wire [1:0] pass,
 input wire [7:0] addr,input wire [9:0] k,
 input wire [2367:0] in_line,
 output reg [3:0] out_v,output reg [2367:0] out_line,
 output reg [15:0] threshold_observe,
 output reg [3:0] selected_v,output reg [2367:0] selected_line,
 output reg [55:0] selected_observe,
 output reg fault
);
 wire rst_core_n=rst_n;
 (* keep *) reg [3:0] op_r;(* keep *) reg [1:0] pass_r;(* keep *) reg [7:0] addr_r;(* keep *) reg [9:0] k_r;
 (* keep *) reg [2367:0] in_r;
 wire [3:0] c_out_v,c_sel_v;wire [2367:0] c_out_line,c_sel_line;wire [15:0] c_thr;wire [55:0] c_obs;wire c_fault;
 reg [3:0] o1_out_v,o1_sel_v;reg [2367:0] o1_out_line,o1_sel_line;reg [15:0] o1_thr;reg [55:0] o1_obs;reg o1_fault;
 // o1 output relay of each quadrant's lines / valids in that quadrant's domain; observes and fault in ctl
 for(genvar q=0;q<4;q=q+1)begin:go1
  always @(posedge clk_q[q])begin
   o1_out_v[q]<=c_out_v[q];o1_sel_v[q]<=c_sel_v[q];
   o1_out_line[q*592+:592]<=c_out_line[q*592+:592];o1_sel_line[q*592+:592]<=c_sel_line[q*592+:592];
  end
 end
 always @(posedge clk_ctl)begin
  op_r<=op;pass_r<=pass;addr_r<=addr;k_r<=k;in_r<=in_line;
  o1_thr<=c_thr;o1_obs<=c_obs;o1_fault<=c_fault;
  out_v<=o1_out_v;out_line<=o1_out_line;threshold_observe<=o1_thr;
  selected_v<=o1_sel_v;selected_line<=o1_sel_line;selected_observe<=o1_obs;fault<=o1_fault;
 end
 ot_hbm_idx_selector_static_core #(.MUT(MUT)) core(.clk_ctl(clk_ctl),.clk_q(clk_q),.clk_mem({{3{clk_q[3]}},{3{clk_q[2]}},{3{clk_q[1]}},{3{clk_q[0]}}}),.rst_n(rst_core_n),
  .op(op_r),.pass(pass_r),.addr(addr_r),.k(k_r),.in_line(in_r),.out_v(c_out_v),.out_line(c_out_line),
  .threshold_observe(c_thr),.selected_v(c_sel_v),.selected_line(c_sel_line),.selected_observe(c_obs),.fault(c_fault));
endmodule
`default_nettype wire
