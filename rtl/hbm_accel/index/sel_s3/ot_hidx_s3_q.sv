`default_nettype none
// L2H-IDXSEL s3 / HBM-IDX6 FAN32 (10-20): ONE hardened QUADRANT tile of the HBM IDX selector, used x4 inside the landed
// cluster ot_hbm_idx_selector_s3 (tools/landed_parent/lp.py, spec tools/landed_parent/specs/hidx_sel_s3.json).
// Same arithmetic, selection and PORT TIMING as the s3 quadrant (fb02fa82f, kept as rtl/test/hbm_idx_static/
// ot_hidx_s3_q_ref.sv for the lockstep equivalence bench): 16 lanes, 3 real 256x256 SRAMs, the 64-bin histogram,
// S0..S6 compare / tie / pack / rotate pipeline.  The calendar (registered_s3: sel_in 7, sel_in_line 2, sel_out 1,
// sel_choose_rt 8) is unchanged: no edge added.
// FAN32 structural redesign (the s3 quadrant failed the mandatory native32 census: 497 drivers > 32, max 1788):
//   every register / combinational net drives <= 32 actual load pins.  The method is REPLICATED STATE, not buffering:
//   * cw lands in 11 kept P1 pin-flop copies, one per consumer family (4 lane groups, SRAMs, quadrant control,
//     histogram chains, 4 histogram-read quarters); thr in 6 kept copies; ties in 4 (one per tie replica);
//   * every line-wide select / enable is a kept flag register per 13/12-bit lane CHUNK (3 per lane): SRAM write-data
//     select, buffer clear, flush, pack-chain loads, and the rotate selects;
//   * the S5 barrel rotate (was: 8 fill copies x a multiply-shift, 1788 loads) is a 16-lane cyclic rotate in two
//     one-hot 4:1 stages (F[1:0], F[3:2]) plus a per-lane "l >= F" split; its per-chunk one-hot selects are LOADED ONE
//     EDGE AHEAD from the next-fill value, so the fill recurrence keeps one cycle: the fill state is replicated
//     (4 lane-group replicas + 1 master for the write pointer / hazards), each with its own copies of op1 / op7 /
//     s3_v / s4_v / dcnt, so no replica net exceeds ~20 loads; nf >= 16 ("hi") is likewise a per-chunk flag;
//   * the S4 dense pack runs on 3 kept copies of the selected-lane valid bits (one prefix network per chunk), so each
//     one-hot match term drives one 13-bit chunk;
//   * the tie budget, last_id and the S2/S3/S4 valid bits are replicated per lane group / consumer;
//   * histogram: per-lane (lane, bin-quarter) match flags + 4-bit bin copies feed the 64 bin counters; clears per 2 bins,
//     adds per 4 bins; the 64:1 read is a registered one-hot bin select (4 kept address copies, 16 decodes each);
//   * the histogram path has its own kept copy of each lane's valid + key (rawh), s1_pass is copied per lane, the
//     pack prefix network is a kept module (ot_hidx_s3_pfx) per chunk copy, the compare path
//     has its own kept valid + key copy (rawc), the last-valid-lane one-hot is a kept module (ot_hidx_s3_pri);
//   * reset: ot_rst_relay with 15 regional leaves (2 sync + region stage = the 2-stage landing), <= 31 loads per leaf.
// DMUT (bench only, 0 in every kit): 1 tie compare >= ; 3 lane-5 SRAM write-data select one edge late; 5 histogram read
//   returned one edge later than its op tags.
// Pack prefix network (kept hierarchy, SYNTH_KEEP_MODULES): positions of the selected lanes in 4-lane groups.  As its
// own module ABC cannot flatten the popcounts into the 16 x 16 one-hot match decode (that put up to 63 loads on the
// low lanes' valid bits).
module ot_hidx_s3_pfx(input wire [15:0] ch,output wire [79:0] pos,output wire [4:0] cnt);
 wire [1:0] p_loc[0:15];wire [2:0] p_gt[0:3];wire [3:0] p_gb[0:3];
 for(genvar g=0;g<4;g=g+1)begin:gg
  assign p_loc[4*g]=2'd0;assign p_loc[4*g+1]=2'(ch[4*g]);assign p_loc[4*g+2]=2'(ch[4*g])+2'(ch[4*g+1]);
  assign p_loc[4*g+3]=(2'(ch[4*g])+2'(ch[4*g+1]))+2'(ch[4*g+2]);
  assign p_gt[g]=(3'(ch[4*g])+3'(ch[4*g+1]))+(3'(ch[4*g+2])+3'(ch[4*g+3]));
 end
 assign p_gb[0]=4'd0;assign p_gb[1]=4'(p_gt[0]);assign p_gb[2]=4'(p_gt[0])+4'(p_gt[1]);
 assign p_gb[3]=(4'(p_gt[0])+4'(p_gt[1]))+4'(p_gt[2]);
 for(genvar l=0;l<16;l=l+1)begin:gp
  assign pos[5*l+:5]=5'(p_gb[l/4])+5'(p_loc[l]);
 end
 assign cnt=(5'(p_gt[0])+5'(p_gt[1]))+(5'(p_gt[2])+5'(p_gt[3]));
endmodule
// Last-valid-lane one-hot (kept hierarchy, SYNTH_KEEP_MODULES): the source-id order check takes the id of the highest
// valid lane; as its own module the priority chain cannot be flattened into the 20-bit id select (up to 46 loads on the
// top lanes' valid bits).
module ot_hidx_s3_pri(input wire [15:0] v,output wire [15:0] oh,output wire any);
 for(genvar l=0;l<16;l=l+1)begin:gl
  if(l==15)begin:gt assign oh[l]=v[l];end
  else begin:gn assign oh[l]=v[l]&&!(|v[15:l+1]);end
 end
 assign any=|v;
endmodule
// Opt-in exact counter recurrence: the high nine bits consume a parallel carry prefix.
// No pipeline edge, reset, schedule, or rounding change. Keep hierarchy prevents ABC
// recombining the prefix with the upstream dense-pack count into one long adder.
(* keep_hierarchy *) module ot_hidx_s3_acc14(input wire [13:0] a,input wire [4:0] b,input wire mut,output wire [13:0] y,output wire low_carry);
 wire [5:0] lo={1'b0,a[4:0]}+{1'b0,b};
 wire carry=lo[5]^mut;
 assign low_carry=carry;
 assign y[4:0]=lo[4:0];
 for(genvar i=5;i<14;i=i+1)begin:g_hi
  if(i==5)assign y[i]=a[i]^carry;
  else assign y[i]=a[i]^(carry&&(&a[i-1:5]));
 end
endmodule
module ot_hidx_s3_q #(parameter integer DMUT=0,FAST_COUNT=0)(
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
 localparam integer EW=37,W=16,LW=592,NP1=11;
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
 // lane chunk c of a 37-bit lane: [0..12] [13..24] [25..36]
 function automatic integer cbase(input integer c);
  cbase=(c==0)?0:((c==1)?13:25);
 endfunction
 function automatic integer cwid(input integer c);
  cwid=(c==0)?13:12;
 endfunction
 // ---------------- reset: 2 registered stages at the face + 15 regional leaves ----------------
 wire [14:0] rr;
 ot_rst_relay #(.REGIONS(15),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rr(.clk(clk),.rst_n_in(rst_n),.rst_n(rr));
 // ---------------- pin flops ----------------
 // P1 copies of cw: 0..3 lane groups, 4 SRAMs, 5 quadrant control, 6 histogram chains, 7..10 histogram read quarters
 wire [13:0] p1[0:NP1-1];
 for(genvar i=0;i<NP1;i=i+1)begin:gp1
  (* keep *) reg [13:0] q;
  always @(posedge clk)q<=cw;
  assign p1[i]=q;
 end
 // threshold copies: 0..3 compare (4 lanes each), 4..5 histogram (8 lanes each)
 wire [15:0] thq[0:5];
 for(genvar j=0;j<6;j=j+1)begin:gt
  (* keep *) reg [15:0] q;
  always @(posedge clk)q<=thr;
  assign thq[j]=q;
 end
 reg [LW-1:0] in_p1,in_p2;
 always @(posedge clk)begin in_p1<=in_line;in_p2<=in_p1;end
 // ---------------- P2: quadrant control + decoded op flag copies (from p1[5]) ----------------
 reg [13:0] qc;
 wire [3:0] qop=qc[3:0];wire [1:0] qpass=qc[5:4];wire [7:0] qaddr=qc[13:6];
 wire p5op1=p1[5][3:0]==1,p5op7=p1[5][3:0]==7;
 (* keep *) reg [3:0] op1t;            // tie replicas
 (* keep *) reg op1s;                  // selected counter
 (* keep *) reg [3:0] op1l;            // last_id replicas
 (* keep *) reg [4:0] op1f,op7f;       // fill replicas (4 = master)
 always @(posedge clk)begin
  qc<=p1[5];
  op1t<={4{p5op1}};op1s<=p5op1;op1l<={4{p5op1}};op1f<={5{p5op1}};op7f<={5{p5op7}};
 end
 // ---------------- P2: per-SRAM control copies (from p1[4]): 0 re 1 ing 2..9 addr ----------------
 wire [9:0] sq[0:2];
 for(genvar m=0;m<3;m=m+1)begin:gs
  (* keep *) reg [9:0] q;
  always @(posedge clk)q<={p1[4][13:6],p1[4][3:0]==2,p1[4][3:0]==4||p1[4][3:0]==6};
  assign sq[m]=q;
 end
 // ---------------- P2: per-lane / per-chunk flags (from p1[l/4]) ----------------
 wire [2:0] f_wsel[0:15],f_bclr[0:15],f_fl[0:15],f_ld12[0:15],f_ld13[0:15];
 wire [1:0] f_ing[0:15];
 for(genvar l=0;l<16;l=l+1)begin:gl
  wire [3:0] o=p1[l/4][3:0];
  (* keep *) reg [2:0] wsel,bclr,fl,ld12,ld13;
  (* keep *) reg [1:0] ing;             // 0: histogram source bits 0..8, 1: bits 9..16 + pass / match
  (* keep *) reg c7,c8,c9,c10,c11;      // op6 pack chain
  always @(posedge clk)begin
   wsel<={3{o==2}};bclr<={3{o==1||o==7}};fl<={3{o==7}};ing<={2{o==2}};
   c7<=o==6;c8<=c7;c9<=c8;c10<=c9;c11<=c10;ld12<={3{c11}};ld13<={3{c11}};
  end
  if(DMUT==3&&l==5)begin:gd3
   (* keep *) reg [2:0] wsel_d;
   always @(posedge clk)wsel_d<=wsel;
   assign f_wsel[l]=wsel_d;
  end else begin:gd0
   assign f_wsel[l]=wsel;
  end
  assign f_bclr[l]=bclr;assign f_fl[l]=fl;assign f_ld12[l]=ld12;assign f_ld13[l]=ld13;assign f_ing[l]=ing;
 end
 // ---------------- P2: histogram chains per 8 bins (from p1[6]) ----------------
 // h0 op3 -> clears (per 2 bins); h3 op2 / h4 op4 -> h5 -> h6; h7 = h3 | h6 -> adds (per 4 bins)
 wire [3:0] f_hcl[0:7];wire [3:0] f_h2v[0:7];wire f_h7[0:7];
 for(genvar g=0;g<8;g=g+1)begin:gh
  (* keep *) reg h0,h3,h4,h5,h6,h7;
  (* keep *) reg [3:0] hcl;
  (* keep *) reg [3:0] h2v;             // adds per 2 bins
  always @(posedge clk)begin
   h0<=p1[6][3:0]==3;h3<=p1[6][3:0]==2;h4<=p1[6][3:0]==4;h5<=h4;h6<=h5;h7<=h3||h6;
   hcl<={4{h0}};h2v<={4{h7}};
  end
  assign f_hcl[g]=hcl;assign f_h2v[g]=h2v;assign f_h7[g]=h7;
 end
 // ---------------- P2: histogram read one-hot bin select (from p1[7..10]) ----------------
 wire [63:0] f_oh;
 for(genvar q=0;q<4;q=q+1)begin:gro
  (* keep *) reg [15:0] oh;
  always @(posedge clk)for(integer i=0;i<16;i=i+1)oh[i]<=p1[7+q][11:6]==6'(16*q+i);
  assign f_oh[16*q+:16]=oh;
 end
 // ---------------- SRAMs ----------------
 wire [767:0] raw;
 reg wreq;reg [5:0] wa_r;reg [LW-1:0] wreg,buf_q;
 wire [LW-1:0] wd;
 for(genvar l=0;l<16;l=l+1)begin:gwd
  for(genvar c=0;c<3;c=c+1)begin:gc
   assign wd[l*EW+cbase(c)+:cwid(c)]=f_wsel[l][c]?in_p2[l*EW+cbase(c)+:cwid(c)]:wreg[l*EW+cbase(c)+:cwid(c)];
  end
 end
 wire [767:0] wide_wd={176'd0,wd};
 for(genvar m=0;m<3;m=m+1)begin:gm
  ot_sram_1r1w_256x256_m2_r2c2 mem(.clk(clk),.r_ce_in(sq[m][0]),.r_addr_in(sq[m][9:2]),.rd_out(raw[m*256+:256]),
   .w_ce_in(sq[m][1]||wreq),.w_addr_in(sq[m][1]?sq[m][9:2]:{2'd0,wa_r}),.wd_in(wide_wd[m*256+:256]),.w_mask_in({256{1'b1}}),
   .rr_en(2'd0),.rr_addr(14'd0),.cr_en(2'd0),.cr_sel(16'd0));
 end
 // ---------------- R / S1 stage ----------------
 reg rv;reg [3:0] rop;reg [1:0] rpass;reg [7:0] raddr;
 (* keep *) reg s16_id,s16_c,s14;      // s1_v && s1_op==6 (idbad / valid copies + hazards), s1_v && s1_op==4 (scan)
 (* keep *) reg [7:0] s16_l;           // last_id half replicas
 wire [1:0] spq[0:15];                 // s1_pass per lane
 for(genvar g=0;g<16;g=g+1)begin:gsp
  (* keep *) reg [1:0] q;
  always @(posedge clk)q<=rpass;
  assign spq[g]=q;
 end
 reg [7:0] s1_addr;
 (* keep *) reg [LW-1:0] rawr;             // kept: else opt_merge folds it into the identical rawh bits
 wire [16:0] rawh[0:15],rawc[0:15];    // kept histogram-path copy (valid + key) / compare-path copy (valid + ORDER key)
 for(genvar l=0;l<16;l=l+1)begin:grh
  (* keep *) reg [16:0] q,c;
  always @(posedge clk)begin q<=raw[l*EW+:17];c<={orderkey(raw[l*EW+1+:16]),raw[l*EW]};end   // c: order key at the macro side
  assign rawh[l]=q;assign rawc[l]=c;
 end
 always @(posedge clk)begin
  rop<=qop;rpass<=qpass;raddr<=qaddr;
  s1_addr<=raddr;rawr<=raw[LW-1:0];
 end
 // ---------------- S2 stage ----------------
 reg [7:0] s2_addr;reg [LW-1:0] s2_line;reg [15:0] s2_gt,s2_eq;reg [1:0] s2_loc[0:15];reg [2:0] s2_gtot[0:3];reg [4:0] s2_ecnt;
 (* keep *) reg [3:0] s2v_l;           // selected-lane valid (per 4 lanes)
 (* keep *) reg [7:0] s2v_t;           // tie replicas (2 per replica)
 (* keep *) reg s2v_m;                 // s3 copies, sel_v, hazards
 reg [15:0] c_gt,c_eq;reg [15:0] c_ky;reg [1:0] c_loc[0:15];reg [2:0] c_gtot[0:3];reg [4:0] c_ecnt;
 always @*begin
  for(integer l=0;l<W;l=l+1)begin
   c_ky=rawc[l][16:1];                  // already the order key
   c_gt[l]=rawc[l][0]&&(c_ky>thq[l/4]);
   c_eq[l]=rawc[l][0]&&(c_ky==thq[l/4]);
   if(DMUT==1)begin c_gt[l]=rawc[l][0]&&(c_ky>=thq[l/4]);c_eq[l]=0;end
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
 always @(posedge clk)begin
  s2_addr<=s1_addr;s2_line<=rawr;s2_gt<=c_gt;s2_eq<=c_eq;s2_ecnt<=c_ecnt;
  for(integer l=0;l<W;l=l+1)s2_loc[l]<=c_loc[l];
  for(integer g=0;g<4;g=g+1)s2_gtot[g]<=c_gtot[g];
 end
 // ---------------- S3: tie budget, one replica per 4-lane group ----------------
 reg [3:0] c_gb[0:3];
 always @*begin
  c_gb[0]=4'd0;c_gb[1]=4'(s2_gtot[0]);c_gb[2]=4'(s2_gtot[0])+4'(s2_gtot[1]);
  c_gb[3]=(4'(s2_gtot[0])+4'(s2_gtot[1]))+4'(s2_gtot[2]);
 end
 wire [15:0] c_choose;
 for(genvar g=0;g<4;g=g+1)begin:gtie
  (* keep *) reg [13:0] tg;             // ties pin flop copy
  (* keep *) reg [13:0] tie_rem;
  (* keep *) reg [1:0] comp;            // comp_started, one copy per tavail half
  always @(posedge clk)tg<=ties;
  wire [13:0] tavail={comp[1]?tie_rem[13:7]:tg[13:7],comp[0]?tie_rem[6:0]:tg[6:0]};
  wire [13:0] tuse=({9'd0,s2_ecnt}<tavail)?{9'd0,s2_ecnt}:tavail;
  wire [13:0] trem=tavail-tuse;
  always @(posedge clk or negedge rr[4+g])begin
   if(!rr[4+g])begin tie_rem<=0;comp<=0;end
   else begin
    if(s2v_t[2*g])begin tie_rem[6:0]<=trem[6:0];comp[0]<=1;end
    else if(op1t[g])begin tie_rem[6:0]<=0;comp[0]<=0;end
    if(s2v_t[2*g+1])begin tie_rem[13:7]<=trem[13:7];comp[1]<=1;end
    else if(op1t[g])begin tie_rem[13:7]<=0;comp[1]<=0;end
   end
  end
  for(genvar j=0;j<4;j=j+1)begin:gl
   wire [4:0] er=5'(c_gb[g])+5'(s2_loc[4*g+j]);
   assign c_choose[4*g+j]=s2_gt[4*g+j]||(s2_eq[4*g+j]&&({9'd0,er}<tavail));
  end
 end
 // selected line: main copy (-> pin flop, pack data) + 3 kept valid-bit copies (one pack prefix network per chunk)
 (* keep *) reg [LW-1:0] sel_line;          // kept: its valid bits equal the chv copies
 wire [15:0] chv[0:2];
 for(genvar l=0;l<16;l=l+1)begin:gsv
  (* keep *) reg [2:0] v;
  always @(posedge clk)v<={3{s2v_l[l/4]&&c_choose[l]}};
  for(genvar k=0;k<3;k=k+1)begin:gk
   assign chv[k][l]=v[k];
  end
 end
 always @(posedge clk)for(integer l=0;l<W;l=l+1)begin
  sel_line[l*EW+:EW]<=s2_line[l*EW+:EW];sel_line[l*EW]<=s2v_l[l/4]&&c_choose[l];
 end
 // ---------------- S4: dense pack, one prefix network per chunk ----------------
 (* keep *) reg [4:0] s3v_f;           // fill replicas (dcnt / s4_v copies)
 (* keep *) reg s3v_b,s3v_h;           // selected counter, hazard 3
 reg sel_v;reg [7:0] s3_addr,s4_addr;
 wire [LW-1:0] c_dense;
 wire [4:0] c_cnt[0:2];
 for(genvar k=0;k<3;k=k+1)begin:gpk
  wire [15:0] ch=chv[k];
  wire [79:0] pos;wire [4:0] c_pos[0:15];
  ot_hidx_s3_pfx u_pfx(.ch(ch),.pos(pos),.cnt(c_cnt[k]));
  for(genvar l=0;l<16;l=l+1)begin:gp
   assign c_pos[l]=pos[5*l+:5];
  end
  for(genvar i=0;i<16;i=i+1)begin:gi
   reg [12:0] acc;
   always @*begin
    acc=13'd0;
    for(integer l=i;l<W;l=l+1)if(ch[l]&&c_pos[l]==5'(i))acc[cwid(k)-1:0]=acc[cwid(k)-1:0]|sel_line[l*EW+cbase(k)+:cwid(k)];
   end
   assign c_dense[i*EW+cbase(k)+:cwid(k)]=acc[cwid(k)-1:0];
  end
 end
 reg [LW-1:0] dense;
 always @(posedge clk)begin dense<=c_dense;s3_addr<=s2_addr;s4_addr<=s3_addr;end
 // ---------------- S5: fill replicas (0..3 = lane groups, 4 = master) and per-chunk rotate selects ----------------
 (* keep *) reg [4:0] s4v_f;
 wire [3:0] fr_q[0:4];wire [4:0] nf_q[0:4];
 wire [3:0] f_ro1[0:15][0:2],f_ro2[0:15][0:2];wire f_ge[0:15][0:2],f_hi[0:15][0:2];
 for(genvar r=0;r<5;r=r+1)begin:gf
  localparam integer KS=(r<2)?0:((r<4)?1:2);   // pack copy whose count feeds this replica
  wire rq=rr[(r<2)?2:3];
  (* keep *) reg [3:0] fr;
  (* keep *) reg [4:0] dc;
  wire [4:0] dn=s3v_f[r]?c_cnt[KS]:5'd0;
  wire [4:0] nf={1'b0,fr}+dc;
  reg [3:0] fn;
  always @*begin
   fn=fr;
   if(op1f[r])fn=4'd0;
   if(s4v_f[r])fn=(nf>=16)?4'(nf-16):nf[3:0];
   if(op7f[r]&&fr!=0)fn=4'd0;
   if(!rq)fn=4'd0;
  end
  always @(posedge clk or negedge rq)begin
   if(!rq)fr<=0;else fr<=fn;
  end
  always @(posedge clk)dc<=dn;
  assign fr_q[r]=fr;assign nf_q[r]=nf;
  if(r<4)begin:gsel
   wire [4:0] nhi={1'b0,fn}+dn;
   for(genvar j=0;j<4;j=j+1)begin:gl
    localparam integer L=4*r+j;
    (* keep *) reg [11:0] ro1,ro2;       // 3 chunks x one-hot 4 (packed: kept per bit, never a memory)
    (* keep *) reg [2:0] ge,hi;
    always @(posedge clk)for(integer c=0;c<3;c=c+1)begin
     for(integer k=0;k<4;k=k+1)begin ro1[4*c+k]<=fn[1:0]==2'(k);ro2[4*c+k]<=fn[3:2]==2'(k);end
     ge[c]<=5'(L)>={1'b0,fn};hi[c]<=nhi>=16;
    end
    for(genvar c=0;c<3;c=c+1)begin:gc
     assign f_ro1[L][c]=ro1[4*c+:4];assign f_ro2[L][c]=ro2[4*c+:4];assign f_ge[L][c]=ge[c];assign f_hi[L][c]=hi[c];
    end
   end
  end
 end
 // rotate: rot[l] = dense[(l - F) mod 16] in two one-hot 4:1 stages; lo = buf | rot (l >= F), hv = rot (l < F)
 wire [LW-1:0] a1,rot;
 for(genvar l=0;l<16;l=l+1)begin:grt
  for(genvar c=0;c<3;c=c+1)begin:gc
   localparam integer B=cbase(c),N=cwid(c);
   wire [N-1:0] d0=dense[((l-0)&15)*EW+B+:N],d1=dense[((l+15)&15)*EW+B+:N],d2=dense[((l+14)&15)*EW+B+:N],
    d3=dense[((l+13)&15)*EW+B+:N];
   assign a1[l*EW+B+:N]=({N{f_ro1[l][c][0]}}&d0)|({N{f_ro1[l][c][1]}}&d1)|({N{f_ro1[l][c][2]}}&d2)|({N{f_ro1[l][c][3]}}&d3);
   wire [N-1:0] e0=a1[((l-0)&15)*EW+B+:N],e1=a1[((l+12)&15)*EW+B+:N],e2=a1[((l+8)&15)*EW+B+:N],
    e3=a1[((l+4)&15)*EW+B+:N];
   assign rot[l*EW+B+:N]=({N{f_ro2[l][c][0]}}&e0)|({N{f_ro2[l][c][1]}}&e1)|({N{f_ro2[l][c][2]}}&e2)|({N{f_ro2[l][c][3]}}&e3);
   wire [N-1:0] lo=buf_q[l*EW+B+:N]|(f_ge[l][c]?rot[l*EW+B+:N]:{N{1'b0}});
   wire [N-1:0] hv=f_ge[l][c]?{N{1'b0}}:rot[l*EW+B+:N];
   always @(posedge clk)begin
    if(f_bclr[l][c])buf_q[l*EW+B+:N]<=0;
    else if(f_ld12[l][c])buf_q[l*EW+B+:N]<=f_hi[l][c]?hv:lo;
    if(f_fl[l][c])wreg[l*EW+B+:N]<=buf_q[l*EW+B+:N];
    else if(f_ld13[l][c])wreg[l*EW+B+:N]<=lo;
   end
  end
 end
 // ---------------- histogram ----------------
 wire h_scan=s14;
 wire [3:0] h1_mq[0:15];wire [3:0] h1_b4[0:15][0:3];
 for(genvar l=0;l<16;l=l+1)begin:gh1
  wire [16:0] hs={(f_ing[l][1]?in_p2[l*EW+9+:8]:rawh[l][16:9]),(f_ing[l][0]?in_p2[l*EW+:9]:rawh[l][8:0])};
  wire [1:0] hp=f_ing[l][1]?2'd0:spq[l];
  wire [15:0] hk=orderkey(hs[16:1]);
  wire hm=(f_ing[l][1]||h_scan)&&hs[0]&&((hk&pmask(hp))==(thq[4+l/8]&pmask(hp)));
  wire [5:0] hb=6'((hk>>pshift(hp))&pbins(hp));
  (* keep *) reg [3:0] mq;
  (* keep *) reg [15:0] b4;             // 4 bin-quarter copies of hb[3:0] (packed)
  always @(posedge clk or negedge rr[12+l/6])begin
   if(!rr[12+l/6])mq<=0;
   else for(integer q=0;q<4;q=q+1)mq[q]<=hm&&hb[5:4]==2'(q);
  end
  always @(posedge clk)b4<={4{hb[3:0]}};
  assign h1_mq[l]=mq;
  for(genvar q=0;q<4;q=q+1)begin:gq
   assign h1_b4[l][q]=b4[4*q+:4];
  end
 end
 wire [13:0] hist[0:63];
 for(genvar b=0;b<64;b=b+1)begin:gb
  reg [4:0] cnt;
  reg [4:0] h2;
  reg [13:0] hv;
  always @*begin
   cnt=0;for(integer l=0;l<W;l=l+1)cnt=cnt+5'(h1_mq[l][b/16]&&h1_b4[l][b/16]==4'(b%16));
  end
  always @(posedge clk)begin
   h2<=cnt;
   hv<=f_hcl[b/8][(b%8)/2]?14'd0:hv+(f_h2v[b/8][(b%8)/2]?14'(h2):14'd0);
  end
  assign hist[b]=hv;
 end
 reg [13:0] hrd_q,hrd_d;
 always @(posedge clk)for(integer j=0;j<14;j=j+1)begin
  reg acc;acc=1'b0;
  for(integer b=0;b<64;b=b+1)acc=acc|(f_oh[b]&hist[b][j]);
  hrd_q[j]<=acc;
 end
 always @(posedge clk)hrd_d<=hrd_q;
 // ---------------- source-id order (last_id half replicas per 4 lanes) ----------------
 wire [15:0] rv_l;wire [19:0] rid[0:15];
 for(genvar l=0;l<16;l=l+1)begin:gid
  assign rv_l[l]=rawr[l*EW];assign rid[l]=rawr[l*EW+17+:20];
 end
 wire anyv;wire [15:0] hsel;
 ot_hidx_s3_pri u_pri(.v(rv_l),.oh(hsel),.any(anyv));
 reg [19:0] ln;
 always @*begin
  ln=20'd0;
  for(integer l=0;l<W;l=l+1)if(hsel[l])ln=ln|rid[l];
 end
 wire [19:0] lid[0:3];
 for(genvar g=0;g<4;g=g+1)begin:glid
  (* keep *) reg [9:0] lo,hi;
  wire en0=s16_l[2*g]&&anyv,en1=s16_l[2*g+1]&&anyv;
  always @(posedge clk or negedge rr[8+g])begin
   if(!rr[8+g])begin lo<=0;hi<=0;end
   else begin
    if(en0)lo<=ln[9:0];else if(op1l[g])lo<=0;
    if(en1)hi<=ln[19:10];else if(op1l[g])hi<=0;
   end
  end
  assign lid[g]={hi,lo};
 end
 reg [15:0] idbad;
 always @(posedge clk or negedge rr[6])begin
  if(!rr[6])idbad[7:0]<=0;
  else for(integer l=0;l<8;l=l+1)idbad[l]<=s16_id&&rv_l[l]&&(s1_addr!=0||l!=0)&&rid[l]<=lid[l/4];
 end
 always @(posedge clk or negedge rr[7])begin
  if(!rr[7])idbad[15:8]<=0;
  else for(integer l=8;l<16;l=l+1)idbad[l]<=s16_id&&rv_l[l]&&rid[l]<=lid[l/4];
 end
 // ---------------- control registers (reset) ----------------
 reg [5:0] wp;reg [13:0] selected;reg [7:0] hz;reg qfault;reg [10:0] rtag;
 wire [13:0] selected_next;
 wire selected_over,selected_low_carry;
 generate if(FAST_COUNT)begin:g_fast_count
  ot_hidx_s3_acc14 u_sum(.a(selected),.b(c_cnt[0]),.mut(DMUT==7),.y(selected_next),.low_carry(selected_low_carry));
  // Exact full-domain range decomposition of selected+count>512 (count5).
  // Below512 only480..511 can overflow512, and only when low5sum>32.
  assign selected_over=(|selected[13:10])||
    (selected[9]&&((|selected[8:0])||(|c_cnt[0])))||
    ((&selected[8:5])&&selected_low_carry&&(|selected_next[4:0]));
 end else begin:g_original_count
  assign selected_next=selected+14'(c_cnt[0]);
  assign selected_low_carry=1'b0;
  assign selected_over=int'(selected)+int'(c_cnt[0])>512;
 end endgenerate

 wire wr_pk=s4v_f[4]&&nf_q[4]>=16;     // pack write (master replica)
 wire wr_fl=op7f[4]&&fr_q[4]!=0;       // op7 flush of a partial line
 always @(posedge clk or negedge rr[0])begin
  if(!rr[0])begin
   rv<=0;s16_id<=0;s16_c<=0;s14<=0;s16_l<=0;s2v_m<=0;s3v_b<=0;s3v_h<=0;sel_v<=0;wreq<=0;hz<=0;qfault<=0;
  end else begin
   rv<=qop==4||qop==6;
   s16_id<=rv&&rop==6;s16_c<=rv&&rop==6;s16_l<={8{rv&&rop==6}};s14<=rv&&rop==4;
   s2v_m<=s16_c;s3v_b<=s2v_m;s3v_h<=s2v_m;sel_v<=s2v_m;
   wreq<=wr_pk||wr_fl;
   // schedule hazards the compiler must never issue (registered terms, sticky OR one edge later)
   hz[0]<=qop==2&&(rv&&rop==6||s16_c||s2v_m||s3v_b||s4v_f[4]||wreq);
   hz[1]<=qop==7&&(rv&&rop==6||s16_c||s2v_m||s3v_b||s4v_f[4]);
   hz[2]<=qop==3&&(rv&&rop==4||s14||f_h7[0]||f_h2v[0][0]);
   hz[3]<=s3v_h&&selected_over;
   hz[4]<=wr_pk&&({2'd0,wp}>s4_addr);   // never overwrite an unread source line
   hz[7:5]<=3'd0;
   if((|hz)||(|idbad))qfault<=1;
  end
 end
 always @(posedge clk or negedge rr[1])begin
  if(!rr[1])begin s2v_l<=0;s2v_t<=0;s3v_f<=0;s4v_f<=0;end
  else begin s2v_l<={4{s16_c}};s2v_t<={8{s16_c}};s3v_f<={5{s2v_m}};s4v_f<=s3v_f;end
 end
 always @(posedge clk or negedge rr[2])begin
  if(!rr[2])wp<=0;
  else begin
   if(op1f[4])wp<=0;
   if(wr_pk||wr_fl)wp<=wp+1;
  end
 end
 always @(posedge clk)if(wr_pk||wr_fl)wa_r<=wp;
 always @(posedge clk or negedge rr[5])begin
  if(!rr[5])selected<=0;
  else if(s3v_b)selected<=selected_next;
  else if(op1s)selected<=0;
 end
 always @(posedge clk or negedge rr[4])begin
  if(!rr[4])rtag<=0;else rtag<={qop==1,qop==3,qop==5,qpass,qaddr[5:0]};
 end
 // ---- output pin flops ----
 always @(posedge clk)begin
  ret<={rtag,(DMUT==5)?hrd_d:hrd_q};
  selected_v_o<=sel_v;selected_line_o<=sel_line;
  qfault_o<=qfault;
 end
endmodule
`default_nettype wire
