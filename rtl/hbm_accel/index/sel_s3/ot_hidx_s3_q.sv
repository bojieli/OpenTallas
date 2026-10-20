`default_nettype none
// L2H-IDXSEL s3 (LEAD3-HBM route B, 10-19/20): ONE hardened QUADRANT tile of the HBM IDX selector, used x4 inside the
// landed cluster ot_hbm_idx_selector_s3 (tools/landed_parent/lp.py, spec tools/landed_parent/specs/hidx_sel_s3.json).
// Same arithmetic and selection as the quadrant block gq[q] of ot_hbm_idx_selector_static_core (safe-fanout core,
// L2H-IDXSEL 10-19): 16 lanes, 3 real 256x256 SRAMs, the 64-bin histogram, S0..S6 compare / tie / pack pipeline.
// What changed (s1/s2 gates GATE_STALL: one 42,772-sink root, then ~7k inter-root reg->reg crossings):
//   * the quadrant is its own clock region (clk); every crossing to the ctl tile is a LANDED net in the parent
//     (ot_pl_land_w/_r, 4-slot ring, +3 edges, fixed latency, no backpressure);
//   * every pin is registered here: cw -> two kept P1 copies (pa, pb) ARE the pin flops; thr -> five kept threshold
//     copies (pin flops); ties -> ties_r; in_line -> in_p1 (pin flop) -> in_p2; outputs selected_v_o / selected_line_o,
//     ret (histogram read + its op tags) and qfault_o are output pin flops;
//   * the choose loop returns its op tags WITH the histogram read (ret = {op1, op3, op5, pass, addr[5:0], hrd}), so
//     the ctl's choose pipeline consumes a self-aligned stream (no ctl delay line); the threshold / ties come back
//     through landings: the IDX compiler idles sel_choose_rt = 8 edges after every op5 run (calendar SEL_CORE table);
//   * the die's selected-only face (as ot_hbm_idx_selector_static_sel, LH-UNREAD F-S 10-19): no emit (op 8) readback,
//     no observation ports; op 8 is a ctl fault, the quadrant ignores it.
// Latency (die-port view, tools/hbm_idx_static_calendar.py PIN table 'registered_s3'): op word ctl pin + ctl out flop +
//   landing 3 + pa/pb + P2 = 7 edges (sel_in); in_line in_p1 + in_p2 = 2 (sel_in_line); selected core reg -> pin flop 1.
// DMUT (bench only, 0 in every kit): 1 tie compare >= (old MUT1); 3 lane-5 SRAM write-data select copy one edge late
//   (old MUT3); 5 histogram read returned one edge later than its op tags.
module ot_hidx_s3_rep(input wire clk,input wire [15:0] d,output reg [15:0] q);
 always @(posedge clk)q<=d;
endmodule
module ot_hidx_s3_q #(parameter integer DMUT=0)(
 input wire clk,
 input wire rst_n,
 input wire [13:0] cw,                 // {addr[7:0], pass[1:0], op[3:0]} from the ctl tile (landed)
 input wire [15:0] thr,                // ctl threshold register (landed)
 input wire [13:0] ties,               // ctl tie budget of this quadrant (landed)
 input wire [591:0] in_line,           // this quadrant's 16 lanes x 37 b (die port slice)
 output reg [24:0] ret,                // {op1, op3, op5, pass[1:0], addr[5:0], hrd[13:0]} -> ctl (landed)
 output reg qfault_o,                  // sticky schedule-hazard flag -> ctl fault (landed)
 output reg selected_v_o,
 output reg [591:0] selected_line_o
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
 // ---------------- reset: 2 registered stages at the face + one region stage ----------------
 wire [0:0] rr_n;
 ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rr(.clk(clk),.rst_n_in(rst_n),.rst_n(rr_n));
 wire rq_n=rr_n[0];
 // ---------------- pin flops: P1 control copies, threshold copies, ties, in_line ----------------
 wire [15:0] pa,pb;                    // a = SRAMs, quadrant control, lanes 0..7; b = lanes 8..15, histogram
 ot_hidx_s3_rep u_pa(.clk(clk),.d({2'b0,cw}),.q(pa));
 ot_hidx_s3_rep u_pb(.clk(clk),.d({2'b0,cw}),.q(pb));
 wire [15:0] thq[0:4];                 // 0..3 compare (4 lanes each), 4 histogram
 for(genvar j=0;j<5;j=j+1)begin:gt
  ot_hidx_s3_rep u_th(.clk(clk),.d(thr),.q(thq[j]));
 end
 reg [13:0] ties_r;
 always @(posedge clk)ties_r<=ties;
 reg [LW-1:0] in_p1,in_p2;
 always @(posedge clk)begin in_p1<=in_line;in_p2<=in_p1;end
 // ---------------- P2 quadrant control copy ----------------
 wire [15:0] qc;
 ot_hidx_s3_rep u_qc(.clk(clk),.d(pa),.q(qc));
 wire [3:0] qop=qc[3:0];wire [1:0] qpass=qc[5:4];wire [7:0] qaddr=qc[13:6];
 // ---- P2 per-lane copies: 0 ing_w 1 ing_h 2 bclr(op1|op7) 3 fl(op7) 7..13 pack chain 14 mutant-only ----
 wire [15:0] lq[0:15];
 for(genvar l=0;l<16;l=l+1)begin:gl
  wire [15:0] src=(l<8)?pa:pb;
  wire [3:0] o=src[3:0];
  wire [15:0] ld;
  assign ld[0]=o==2;assign ld[1]=o==2;assign ld[2]=o==1||o==7;assign ld[3]=o==7;
  assign ld[6:4]=3'd0;
  assign ld[7]=o==6;assign ld[8]=lq[l][7];assign ld[9]=lq[l][8];assign ld[10]=lq[l][9];assign ld[11]=lq[l][10];
  assign ld[12]=lq[l][11];assign ld[13]=lq[l][11];
  assign ld[14]=lq[l][0];assign ld[15]=1'b0;
  ot_hidx_s3_rep u_lc(.clk(clk),.d(ld),.q(lq[l]));
 end
 // ---- P2 per-SRAM copies: 0 re 1 ing 2..9 addr ----
 wire [15:0] sq[0:2];
 for(genvar m=0;m<3;m=m+1)begin:gs
  ot_hidx_s3_rep u_sc(.clk(clk),.d({6'd0,pa[13:6],pa[3:0]==2,pa[3:0]==4||pa[3:0]==6}),.q(sq[m]));
 end
 // ---- P2 histogram groups (8 bins each): 0 hc0 1 hclr_a 2 hclr_b 3 ing 4..6 scan chain 7 h1v 8 h2v_a 9 h2v_b ----
 wire [15:0] hq[0:7];
 for(genvar g=0;g<8;g=g+1)begin:gh
  wire [15:0] hd;
  assign hd[0]=pb[3:0]==3;assign hd[1]=hq[g][0];assign hd[2]=hq[g][0];assign hd[3]=pb[3:0]==2;
  assign hd[4]=pb[3:0]==4;assign hd[5]=hq[g][4];assign hd[6]=hq[g][5];assign hd[7]=hq[g][3]||hq[g][6];
  assign hd[8]=hq[g][7];assign hd[9]=hq[g][7];assign hd[15:10]=6'd0;
  ot_hidx_s3_rep u_hc(.clk(clk),.d(hd),.q(hq[g]));
 end
 // ---- P2 histogram read address: two 6-bit copies per rep (one per 64:1 read-mux output bit) ----
 wire [15:0] haq[0:6];
 for(genvar j=0;j<7;j=j+1)begin:gha
  ot_hidx_s3_rep u_ha(.clk(clk),.d({4'd0,pb[11:6],pb[11:6]}),.q(haq[j]));
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
 reg [7:0] hz;reg [15:0] idbad;reg qfault;
 reg [13:0] selected;
 reg sel_v;reg [LW-1:0] sel_line;
 reg [15:0] h1_m;reg [5:0] h1_bin[0:15];
 reg [4:0] h2_cnt[0:63];
 reg [13:0] hist[0:63];
 reg [13:0] hrd_q,hrd_d;
 reg [10:0] rtag;                      // {op1, op3, op5, pass, addr[5:0]} of the edge that issued the read
 // fill copies for the barrel rotate (two reps x four 4-bit copies)
 reg [3:0] fill_n;
 wire [15:0] fq0,fq1;
 ot_hidx_s3_rep u_f0(.clk(clk),.d({4{fill_n}}),.q(fq0));
 ot_hidx_s3_rep u_f1(.clk(clk),.d({4{fill_n}}),.q(fq1));
 wire [31:0] fq={fq1,fq0};
 // ---- SRAMs: per-SRAM kept control copies; write data selected per lane ----
 wire [LW-1:0] wd;
 for(genvar l=0;l<16;l=l+1)begin:gwd
  assign wd[l*EW+:EW]=((DMUT==3&&l==5)?lq[l][14]:lq[l][0])?in_p2[l*EW+:EW]:wreg[l*EW+:EW];
 end
 wire [767:0] wide_wd={176'd0,wd};
 for(genvar m=0;m<3;m=m+1)begin:gm
  ot_sram_1r1w_256x256_m2_r2c2 mem(.clk(clk),.r_ce_in(sq[m][0]),.r_addr_in(sq[m][9:2]),.rd_out(raw[m*256+:256]),
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
   if(DMUT==1)begin c_gt[l]=rawr[l*EW]&&(c_ky>=thq[l/4]);c_eq[l]=0;end
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
 wire [13:0] tavail=comp_started?tie_rem:ties_r;
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
  for(integer l=0;l<W;l=l+1)ch[l]=sel_line[l*EW];
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
   if(ch[l]&&c_pos[l]==5'(i))c_dense[i*EW+:EW]=c_dense[i*EW+:EW]|sel_line[l*EW+:EW];
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
 // ---- control registers (reset) ----
 always @(posedge clk or negedge rq_n)begin
  if(!rq_n)begin
   rv<=0;s1_v<=0;s2_v<=0;s3_v<=0;s4_v<=0;wreq<=0;fill<=0;wp<=0;tie_rem<=0;comp_started<=0;selected<=0;
   qfault<=0;sel_v<=0;last_id<=0;h1_m<=0;hz<=0;idbad<=0;rtag<=0;
  end else begin
   rv<=qop==4||qop==6;s1_v<=rv;
   s2_v<=s1_v&&s1_op==6;
   s3_v<=s2_v;sel_v<=s2_v;
   s4_v<=s3_v;
   h1_m<=c_hm;
   wreq<=0;
   fill<=fill_n;
   rtag<={qop==1,qop==3,qop==5,qpass,qaddr[5:0]};
   if(qop==1)begin wp<=0;tie_rem<=0;comp_started<=0;selected<=0;last_id<=0;end
   // S2: source id order (compaction scan); compares registered, OR-ed into qfault next edge
   for(integer l=0;l<W;l=l+1)idbad[l]<=s1_v&&s1_op==6&&rawr[l*EW]&&(s1_addr!=0||l!=0)&&rawr[l*EW+17+:20]<=last_id;
   if(s1_v&&s1_op==6)for(integer l=0;l<W;l=l+1)if(rawr[l*EW])last_id<=rawr[l*EW+17+:20];
   // S3: tie recurrence
   if(s2_v)begin comp_started<=1;tie_rem<=tavail-tuse;end
   // S4: count
   if(s3_v)selected<=selected+14'(c_cnt);
   // S5: pack write request
   if(s4_v&&nf>=16)begin wreq<=1;wa_r<=wp;wp<=wp+1;end
   // op7 flush (live edge): queue the partial line through the same write register
   if(qop==7&&fill!=0)begin wreq<=1;wa_r<=wp;wp<=wp+1;end
   // schedule hazards the compiler must never issue (registered terms, sticky OR one edge later)
   hz[0]<=qop==2&&(rv&&rop==6||s1_v&&s1_op==6||s2_v||s3_v||s4_v||wreq);
   hz[1]<=qop==7&&(rv&&rop==6||s1_v&&s1_op==6||s2_v||s3_v||s4_v);
   hz[2]<=qop==3&&(rv&&rop==4||s1_v&&s1_op==4||hq[0][7]||hq[0][8]);
   hz[3]<=s3_v&&(int'(selected)+int'(c_cnt)>512);
   hz[4]<=s4_v&&nf>=16&&({2'd0,wp}>s4_addr);   // never overwrite an unread source line
   hz[7:5]<=3'd0;
   if((|hz)||(|idbad))qfault<=1;
  end
 end
 // ---- datapath registers (no reset); line-wide enables come from the lane copies ----
 always @(posedge clk)begin
  rop<=qop;rpass<=qpass;raddr<=qaddr;
  s1_op<=rop;s1_pass<=rpass;s1_addr<=raddr;rawr<=raw[LW-1:0];
  s2_addr<=s1_addr;s2_line<=rawr;s2_gt<=c_gt;s2_eq<=c_eq;s2_ecnt<=c_ecnt;
  for(integer l=0;l<W;l=l+1)s2_loc[l]<=c_loc[l];
  for(integer g=0;g<4;g=g+1)s2_gtot[g]<=c_gtot[g];
  s3_addr<=s2_addr;
  for(integer l=0;l<W;l=l+1)begin
   sel_line[l*EW+:EW]<=s2_line[l*EW+:EW];sel_line[l*EW]<=s2_v&&c_choose[l];
  end
  s4_addr<=s3_addr;dense<=c_dense;dcnt<=s3_v?c_cnt:5'd0;
  for(integer l=0;l<W;l=l+1)begin
   if(lq[l][2])buf_q[l*EW+:EW]<=0;
   else if(lq[l][12])buf_q[l*EW+:EW]<=(nf>=16)?c_merged[LW+l*EW+:EW]:c_merged[l*EW+:EW];
   if(lq[l][3])wreg[l*EW+:EW]<=buf_q[l*EW+:EW];
   else if(lq[l][13])wreg[l*EW+:EW]<=c_merged[l*EW+:EW];
  end
  // histogram
  for(integer l=0;l<W;l=l+1)h1_bin[l]<=c_hb[l];
  for(integer b=0;b<64;b=b+1)h2_cnt[b]<=c_hc[b];
  for(integer b=0;b<64;b=b+1)
   hist[b]<=(((b%8)<4)?hq[b/8][1]:hq[b/8][2])?14'd0:hist[b]+((((b%8)<4)?hq[b/8][8]:hq[b/8][9])?14'(h2_cnt[b]):14'd0);
  for(integer j=0;j<14;j=j+1)hrd_q[j]<=hist[(j%2)?haq[j/2][11:6]:haq[j/2][5:0]][j];
  hrd_d<=hrd_q;
  // ---- output pin flops ----
  ret<={rtag,(DMUT==5)?hrd_d:hrd_q};
  selected_v_o<=sel_v;selected_line_o<=sel_line;
  qfault_o<=qfault;
 end
endmodule
`default_nettype wire
