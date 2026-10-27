`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// HBM-B-RTL1 (d4g plan b, 2026-10-17): SU scalar gather/broadcast TREE. Replaces the 16 point-to-point RF write relay
// routes of ot_hbm_su_static_top (reducer w -> replica d, RF_RELAY = 36 stages each, d4f rfr_* = 576 relay tiles) with
//   4 leaves (one per quadrant, at the quadrant SU core) -> 4 up-legs (41 b) -> 1 centre root -> 4 down-legs (4 x 41 b).
// EXACT: no arithmetic anywhere. Every head {v, tag[7:0], x[31:0]} of reducer w reaches replica d unchanged, and every
// replica receives it on the SAME edge (all legs have equal registered depth), so RF coherence is kept: the four replicas
// commit each word on one edge, exactly as with the d4f relay network. Only the latency changes:
//   L_TREE = 1 (leaf up pin flop) + UP + 2 (root in/out pin flops) + DN + 1 (leaf down pin flop)  = UP + DN + 4
// and the compiler uses RF_RELAY := L_TREE (RF write pins sample n+11+L_TREE, commit n+12+L_TREE).
// UP / DN are the die relay stages of one leg (set by the d4g die geometry, H-D4G; the die flow inserts them as relay
// stations on the leg edges, they are behavioural here exactly as RF_RELAY was).
// A reducing root (combine the four partials in golden order and broadcast one 41-b word) is a later compiler-lane option
// (HBM-B-RTL3); it changes RF contents and is NOT this block.
// Pin rules (owner 10-15 / NATIVE-2): every input and output pin of the two hardened tiles is a flop; rst_n is
// synchronised at the pin (2-flop, async assert / sync release) inside each tile; only valid bits are reset.
// No ready/credit/arbitration: the schedule is static.
// NLEG (HBM-BIND B2 2026-10-24, default 4 = unchanged): 2 = the B2 8-SM die (NW + NE): 2 leaves, 2 legs, root2 master.
// MUT (bench only, net level): 1 = quadrant-2 down-leg one stage shorter; 2 = root drops source 1; 3 = leaf 3 swaps tag
// bits 0/1 on its up-leg; 4 = root broadcasts source 0 one edge late to quadrant 1.
// ---------------------------------------------------------------------------------------------------------------------

// pin reset synchroniser: async assert, 2-flop synchronous release
module ot_hbm_su_stree_rsync(input wire clk, input wire rst_n, output wire rst_q_n);
 reg [1:0] s;
 always @(posedge clk or negedge rst_n) if(!rst_n) s<=2'b00; else s<={s[0],1'b1};
 assign rst_q_n=s[1];
endmodule

// LEAF tile (x4, one master): at the quadrant SU core. head_i (from qcore red pins) -> up_o (pin flop);
// dn_i (4 heads from the root) -> pin flop -> rf_wv/rf_wa/rf_wd (outputs straight from flops).
// NLEG (HBM-BIND B2 2026-10-24; default 4 = unchanged): number of tree legs = reducers = RF writers. NLEG 2 (B2 die,
// NW + NE kept): dn_i carries 2 heads (lane w = B2 leg w: 0 = NW reducer, 1 = NE reducer) and the RF write port is
// 2 writers wide (rf_wv[1:0]); same pin flops, same edges.
module ot_hbm_su_stree_leaf #(parameter integer MUT=0, NLEG=4)(
 input wire clk, input wire rst_n,
 input wire [40:0] head_i,
 output wire [40:0] up_o,
 input wire [NLEG*41-1:0] dn_i,
 output wire [NLEG-1:0] rf_wv, output wire [NLEG*8-1:0] rf_wa, output wire [NLEG*32-1:0] rf_wd
);
 initial if(NLEG!=4&&NLEG!=2) $fatal(1,"ot_hbm_su_stree_leaf: NLEG must be 4 or 2");
 wire rq_n; ot_hbm_su_stree_rsync u_rs(.clk(clk),.rst_n(rst_n),.rst_q_n(rq_n));
 reg [NLEG-1:0] dv; reg [39:0] dd [0:NLEG-1];
 reg uv; reg [39:0] ud;
 wire [40:0] hm=(MUT==3)?{head_i[40],head_i[39:34],head_i[32],head_i[33],head_i[31:0]}:head_i;
 always @(posedge clk or negedge rq_n) if(!rq_n) uv<=1'b0; else uv<=hm[40];
 always @(posedge clk) ud<=hm[39:0];
 assign up_o={uv,ud};
 integer k;
 always @(posedge clk or negedge rq_n)
  if(!rq_n) dv<='0; else for(k=0;k<NLEG;k=k+1) dv[k]<=dn_i[k*41+40];
 always @(posedge clk) for(k=0;k<NLEG;k=k+1) dd[k]<=dn_i[k*41+:40];
 for(genvar w=0;w<NLEG;w=w+1)begin:g_w
  assign rf_wv[w]=dv[w]; assign rf_wa[w*8+:8]=dd[w][39:32]; assign rf_wd[w*32+:32]=dd[w][31:0];
 end
endmodule

// ROOT tile (x1): centre strip. NLEG up-legs -> pin flops -> one broadcast register -> NLEG down-leg pin flop banks
// (one NLEG*41-b output flop bank per down-leg, so each down face is driven by its own flops: no shared high-fanout net).
// HBM-BIND B2 2026-10-24: the root logic is ot_hbm_su_stree_root_n #(NLEG); the die masters are port wrappers:
//   ot_hbm_su_stree_root  (NLEG 4, ports up0..3_i / dn0..3_o [163:0], unchanged: the r18h5 str_C master)
//   ot_hbm_su_stree_root2 (NLEG 2, ports up0..1_i / dn0..1_o [81:0]: the B2 die str_C master, leg 0 = NW, leg 1 = NE)
// A leg that does not exist has no port (no tie-off). Same edges for both: up pin flop -> out flop = 2 root edges, so
// L_TREE = UP + DN + 4 is unchanged (UP / DN = the die relay stages of one leg, set by the die geometry).
// The tree is EXACT (no arithmetic, no reduction): every replica receives every reducer's head unchanged on one edge.
module ot_hbm_su_stree_root_n #(parameter integer NLEG=4, MUT=0)(
 input wire clk, input wire rst_n,
 input wire [NLEG*41-1:0] up_i,                       // leg k at [k*41+:41]
 output wire [NLEG*NLEG*41-1:0] dn_o                  // down-leg d at [d*NLEG*41+:NLEG*41], head k at [k*41+:41] in it
);
 initial if(NLEG!=4&&NLEG!=2) $fatal(1,"ot_hbm_su_stree_root_n: NLEG must be 4 or 2");
 localparam integer DW=NLEG*41;
 wire rq_n; ot_hbm_su_stree_rsync u_rs(.clk(clk),.rst_n(rst_n),.rst_q_n(rq_n));
 reg [NLEG-1:0] iv; reg [39:0] id [0:NLEG-1];
 integer k;
 always @(posedge clk or negedge rq_n)
  if(!rq_n) iv<='0; else for(k=0;k<NLEG;k=k+1) iv[k]<=up_i[k*41+40]&&!(MUT==2&&k==1);
 always @(posedge clk) for(k=0;k<NLEG;k=k+1) id[k]<=up_i[k*41+:40];
 wire [DW-1:0] bc;
 for(genvar b=0;b<NLEG;b=b+1)begin:g_bc assign bc[b*41+:41]={iv[b],id[b]}; end
 reg late_v; reg [39:0] late_d;   // MUT 4 only
 always @(posedge clk or negedge rq_n) if(!rq_n) late_v<=1'b0; else late_v<=bc[40];
 always @(posedge clk) late_d<=bc[39:0];
 wire [40:0] late={late_v,late_d};
 for(genvar d=0;d<NLEG;d=d+1)begin:g_d
  reg [NLEG-1:0] ov; reg [NLEG*40-1:0] od;
  wire [DW-1:0] bd=(MUT==4&&d==1)?{bc[DW-1:41],late}:bc;
  always @(posedge clk or negedge rq_n)
   if(!rq_n) ov<='0; else for(k=0;k<NLEG;k=k+1) ov[k]<=bd[k*41+40];
  always @(posedge clk) for(k=0;k<NLEG;k=k+1) od[k*40+:40]<=bd[k*41+:40];
  for(genvar b=0;b<NLEG;b=b+1)begin:g_o assign dn_o[d*DW+b*41+:41]={ov[b],od[b*40+:40]}; end
 end
endmodule

// r18h5 master (4 legs, leg q = quadrant q: 0 SW, 1 SE, 2 NW, 3 NE): ports unchanged
module ot_hbm_su_stree_root #(parameter integer MUT=0)(
 input wire clk, input wire rst_n,
 input wire [40:0] up0_i, up1_i, up2_i, up3_i,       // leg q = quadrant q (0 SW, 1 SE, 2 NW, 3 NE): one face each
 output wire [163:0] dn0_o, dn1_o, dn2_o, dn3_o
);
 wire [4*164-1:0] dn_o;
 assign {dn3_o,dn2_o,dn1_o,dn0_o}=dn_o;
 ot_hbm_su_stree_root_n #(.NLEG(4),.MUT(MUT)) u_n(.clk(clk),.rst_n(rst_n),.up_i({up3_i,up2_i,up1_i,up0_i}),.dn_o(dn_o));
endmodule

// B2 master (2 legs: leg 0 = NW, leg 1 = NE); dn<d>_o = {head 1 (NE), head 0 (NW)}, 41 b each
module ot_hbm_su_stree_root2 #(parameter integer MUT=0)(
 input wire clk, input wire rst_n,
 input wire [40:0] up0_i, up1_i,
 output wire [81:0] dn0_o, dn1_o
);
 wire [2*82-1:0] dn_o;
 assign {dn1_o,dn0_o}=dn_o;
 ot_hbm_su_stree_root_n #(.NLEG(2),.MUT(MUT)) u_n(.clk(clk),.rst_n(rst_n),.up_i({up1_i,up0_i}),.dn_o(dn_o));
endmodule

// leg relay (behavioural die relay stations of one leg; N registered stages, valid reset like the d4f relays)
module ot_hbm_su_stree_leg #(parameter integer W=41, NV=1, N=1)(
 input wire clk, input wire rst_n, input wire [W-1:0] i, output wire [W-1:0] o
);
 localparam integer B=W/NV;   // NV lanes of B bits, valid = MSB of each lane
 if(N==0)begin:g_wire
  assign o=i;
 end else begin:g_st
  reg [NV-1:0] sv [0:N-1]; reg [W-NV-1:0] sd [0:N-1];
  wire [NV-1:0] iv; wire [W-NV-1:0] id;
  integer k;
  for(genvar l=0;l<NV;l=l+1)begin:g_l
   assign iv[l]=i[l*B+B-1]; assign id[l*(B-1)+:B-1]=i[l*B+:B-1];
   assign o[l*B+B-1]=sv[N-1][l]; assign o[l*B+:B-1]=sd[N-1][l*(B-1)+:B-1];
  end
  always @(posedge clk or negedge rst_n)
   if(!rst_n) for(k=0;k<N;k=k+1) sv[k]<='0;
   else begin sv[0]<=iv; for(k=1;k<N;k=k+1) sv[k]<=sv[k-1]; end
  always @(posedge clk) begin sd[0]<=id; for(k=1;k<N;k=k+1) sd[k]<=sd[k-1]; end
 end
endmodule

// NET: the full tree as the SU top instantiates it (RF_TREE=1). clk_q[q] = quadrant q's serial relay root (leaf, its
// up-leg and its down-leg); clk_root = the centre root clock. NLEG 2 (B2): legs 0 = NW, 1 = NE; root master root2.
// MUT 1 / 3 act on the last-but-one-of-4 leg (2) / last leg (3) at NLEG 4, on leg 1 at NLEG 2.
module ot_hbm_su_stree_net #(parameter integer UP=14, DN=14, MUT=0, NLEG=4)(
 input wire [NLEG-1:0] clk_q, input wire clk_root, input wire rst_n,
 input wire [NLEG*41-1:0] head,              // reducer w head at [w*41+:41]
 output wire [NLEG*NLEG-1:0] q_wv, output wire [NLEG*NLEG*8-1:0] q_wa, output wire [NLEG*NLEG*32-1:0] q_wd   // replica q at [q*NLEG+:NLEG] / [q*NLEG*8+:NLEG*8] / [q*NLEG*32+:NLEG*32]
);
 localparam integer L_TREE=UP+DN+4, DW=NLEG*41;
 localparam integer M1Q=(NLEG==4)?2:1, M3Q=NLEG-1;
 wire [NLEG*41-1:0] up_leaf, up_root; wire [NLEG*DW-1:0] dn_root, dn_leaf;
 for(genvar q=0;q<NLEG;q=q+1)begin:g_q
  ot_hbm_su_stree_leaf #(.MUT(MUT==3&&q==M3Q?3:0),.NLEG(NLEG)) u_leaf(.clk(clk_q[q]),.rst_n(rst_n),.head_i(head[q*41+:41]),
   .up_o(up_leaf[q*41+:41]),.dn_i(dn_leaf[q*DW+:DW]),.rf_wv(q_wv[q*NLEG+:NLEG]),.rf_wa(q_wa[q*NLEG*8+:NLEG*8]),
   .rf_wd(q_wd[q*NLEG*32+:NLEG*32]));
  ot_hbm_su_stree_leg #(.W(41),.NV(1),.N(UP)) u_up(.clk(clk_q[q]),.rst_n(rst_n),.i(up_leaf[q*41+:41]),.o(up_root[q*41+:41]));
  ot_hbm_su_stree_leg #(.W(DW),.NV(NLEG),.N((MUT==1&&q==M1Q)?DN-1:DN)) u_dn(.clk(clk_q[q]),.rst_n(rst_n),
   .i(dn_root[q*DW+:DW]),.o(dn_leaf[q*DW+:DW]));
 end
 if(NLEG==4)begin:g_r4
  ot_hbm_su_stree_root #(.MUT(MUT==2||MUT==4?MUT:0)) u_root(.clk(clk_root),.rst_n(rst_n),.up0_i(up_root[0+:41]),.up1_i(up_root[41+:41]),
   .up2_i(up_root[82+:41]),.up3_i(up_root[123+:41]),.dn0_o(dn_root[0+:164]),.dn1_o(dn_root[164+:164]),
   .dn2_o(dn_root[328+:164]),.dn3_o(dn_root[492+:164]));
 end else begin:g_r2
  ot_hbm_su_stree_root2 #(.MUT(MUT==2||MUT==4?MUT:0)) u_root(.clk(clk_root),.rst_n(rst_n),.up0_i(up_root[0+:41]),.up1_i(up_root[41+:41]),
   .dn0_o(dn_root[0+:82]),.dn1_o(dn_root[82+:82]));
 end
endmodule
`default_nettype wire
