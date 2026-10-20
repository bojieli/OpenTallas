`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// HBM-PGLG3 2026-10-20: soft glue of the TWO-HALF form of the LIGHT SU port-group slice (H.STA.BLK.15.3 successor of the
// one-column landed parent hbm_su_pgslice_lg_light_d4g, lg4 FAIL 65cea4293: aspect 2.47, fill 67.7 %, read-slot counter
// rc[0] 4,181 loads, raw macro clock cotiming). The column R0 | R1 | S | R2 | R3 is cut through the S band into two
// hardened halves, each <= 1,577 um tall (aspect 1.28) with its own regional roots:
//   H_LO = R0 | R1 | S_lo  (store groups 0/1, hi 0): face relays, u_sinh #(HI 0), u_schk (the S checks), u_sout (drain
//          select, reducer operand, pre-tree pass-through, inject / pt data, sticky fault) -- reads groups 2/3 returns from
//          the seam (landed: ot_pl_land_phys_chunk_r in the H_LO kit top).
//   H_HI = S_hi | R2 | R3  (store groups 2/3, hi 1): face relays, u_sinh #(HI 1); returns ret2d / ret3b leave on the seam
//          (ot_pl_land_phys_chunk_w in the H_HI kit top, region r2 root).
// The flat composition H_LO + H_HI (seam = wires) is EXACTLY the flat region parent ot_hbm_su_static_pgslice_rgf: the
// S service u_sin is split into two copies of its per-store-group part (ot_hbm_su_pgrg_sinh, identical registers and
// edges) plus the S checks (ot_hbm_su_pgrg_schk = u_sin's check cone, pipelined 3 as before); nothing else changes.
// ---------------------------------------------------------------------------------------------------------------------

// ------------------------------------------------------------------------------------------- S: inbound, one half
// = ot_hbm_su_pgrg_sin minus the S checks, store groups r = 2*HI + h only. dia = di<2HI>, dib = di<2HI+1>.
module ot_hbm_su_pgrg_sinh #(
 parameter integer HI=0,READ_RETURN=10,MULTIRATE=1,COLLPORT=1,RF_LOCAL=1,MUT=0
)(
 input wire ck, input wire rst_n,
 input wire [2*30-1:0] vmr_cmd,
 input wire [2*39-1:0] vmw_cmd,
 input wire [2*257-1:0] su_rr,
 input wire [1:0] ij_v,                     // ij_v[2*HI +: 2]
 input wire [17:0] ij_row,                  // ij_row[18*HI +: 18]
 input wire [4*32-1:0] rf_bword,
 input wire [4*9-1:0] rf_bcmd,
 input wire dw_v,                           // dw_v[HI]
 input wire [8:0] dw_row,                   // dw_row[9*HI +: 9]
 input wire [511:0] dw_d,                   // dw_d[512*HI +: 512]
 output wire [163:0] rf_u,
 output wire [541:0] dia, dib
);
 // ---- FILL destination delay line (as pgslice / u_sin)
 localparam integer RR=MULTIRATE ? 12 : READ_RETURN;
 localparam integer FD=(MUT==1)?RR-1:RR;
 reg [10:0] fd [0:1][0:RR];
 reg [1:0] fr_v; reg [1:0] fr_hi; reg [8:0] fr_row [0:1]; reg [255:0] fr_dat [0:1];
 for(genvar h=0;h<2;h=h+1)begin:g_fill
  wire [29:0] c=vmr_cmd[h*30+:30];
  integer k;
  always @(posedge ck)
   if(!rst_n)begin for(k=0;k<=RR;k=k+1)fd[h][k]<=11'd0; fr_v[h]<=1'b0; end
   else begin
    fd[h][0]<={c[29],c[12],c[8:0]};for(k=1;k<=RR;k=k+1)fd[h][k]<=fd[h][k-1];
    fr_v[h]<=fd[h][FD][10];
   end
  always @(posedge ck)begin fr_hi[h]<=fd[h][FD][9];fr_row[h]<=fd[h][FD][8:0];fr_dat[h]<=su_rr[h*257+:256];end
 end
 // ---- RF local copy
 wire [4*32-1:0] rf_bword_u; wire [4*9-1:0] rf_bcmd_u;
 if(RF_LOCAL)begin:g_rf_local
  reg [4*32-1:0] rf_bword_l; reg [4*8-1:0] rf_badr_l; reg [3:0] rf_bv_l; integer vb;
  always @(posedge ck)begin
   rf_bword_l<=rf_bword;
   for(vb=0;vb<4;vb=vb+1)rf_badr_l[vb*8+:8]<=rf_bcmd[vb*9+:8];
  end
  always @(posedge ck)
   if(!rst_n)rf_bv_l<=4'd0;
   else for(vb=0;vb<4;vb=vb+1)rf_bv_l[vb]<=rf_bcmd[vb*9+8];
  assign rf_bword_u=rf_bword_l;
  assign rf_bcmd_u={rf_bv_l[3],rf_badr_l[24+:8],rf_bv_l[2],rf_badr_l[16+:8],rf_bv_l[1],rf_badr_l[8+:8],rf_bv_l[0],rf_badr_l[0+:8]};
 end else begin:g_rf_direct
  assign rf_bword_u=rf_bword; assign rf_bcmd_u=rf_bcmd;
 end
 assign rf_u={rf_bword_u,rf_bcmd_u};
 // ---- per store group bundles of this half (drain / inject port-5 read, fill write, delivery write)
 wire [541:0] di [0:1];
 for(genvar h=0;h<2;h=h+1)begin:g_dis
  wire [38:0] w=vmw_cmd[h*39+:39];
  wire dr_v=w[38]&&!w[37]; wire dr_hi=w[36]; wire [8:0] dr_row=w[32:24];
  wire fw=fr_v[h]&&fr_hi[h]==1'(HI);
  wire drn=dr_v&&dr_hi==1'(HI);
  wire ijn=ij_v[h];
  wire [8:0] ra5=ijn?ij_row[9*h+:9]:dr_row;
  wire dwn=(COLLPORT!=0)&&dw_v;
  wire [255:0] dwd;
  for(genvar j=0;j<8;j=j+1)begin:g_w
   assign dwd[j*32+:32]=dw_d[32*((MUT==10)?15-(8*h+j):(8*h+j))+:32];
  end
  assign di[h]={fw,fr_row[h],fr_dat[h],drn||ijn,ra5,dwn,dw_row,dwd};
 end
 assign dia=di[0]; assign dib=di[1];
endmodule

// ------------------------------------------------------------------------------------------- S: checks (H_LO only)
// = the check cone of ot_hbm_su_pgrg_sin: command-far, RF drain, inject-vs-drain per store group, ij_bad, strap class.
module ot_hbm_su_pgrg_schk #(
 parameter integer QID=1,G=2,STRAP=1,MUT=0
)(
 input wire ck, input wire rst_n,
 input wire [3:0] pos,
 input wire [2*30-1:0] vmr_cmd,
 input wire [2*39-1:0] vmw_cmd,
 input wire [3:0] ij_v, input wire ij_bad,
 input wire pg_fault,
 output wire s_cond                         // pipelined 3 (flat alignment with the region checks)
);
 wire [1:0] q_id=(STRAP!=0)?pos[3:2]:2'(QID);
 wire [1:0] g_id=(STRAP!=0&&MUT!=11)?pos[1:0]:2'(G);
 wire pos_bad=(STRAP!=0)&&((g_id[1]!=(G>=2))||((q_id==2'd0&&g_id==2'd0)!=(QID==0&&G==0)));
 wire [1:0] cmd_far, rf_drain_bad, dr_v, dr_hi;
 for(genvar h=0;h<2;h=h+1)begin:g_c
  wire [29:0] c=vmr_cmd[h*30+:30];
  wire [38:0] w=vmw_cmd[h*39+:39];
  assign cmd_far[h]=(c[29]&&c[11:9]!={g_id,1'(h)})||(w[38]&&!w[37]&&w[35:33]!={g_id,1'(h)});
  assign rf_drain_bad[h]=w[38]&&w[37]&&!(g_id==2'd0&&h==0);
  assign dr_v[h]=w[38]&&!w[37]; assign dr_hi[h]=w[36];
 end
 wire [3:0] st_inj_drain;
 for(genvar r=0;r<4;r=r+1)begin:g_r
  localparam integer H=r%2, HI=r/2;
  assign st_inj_drain[r]=(dr_v[H]&&dr_hi[H]==1'(HI))&&ij_v[2*HI+H];
 end
 wire c0=pg_fault||(|cmd_far)||(|rf_drain_bad)||(|st_inj_drain)||ij_bad||pos_bad;
 reg [2:0] cp;
 always @(posedge ck) if(!rst_n) cp<=3'd0; else cp<={cp[1:0],c0};
 assign s_cond=cp[2];
endmodule

// ------------------------------------------------------------------------------------------- SEAM landing (H_HI -> H_LO)
// The two halves abut at the cut through the S band; groups 2/3 returns {ret2d, ret3b} (2 x 521 b) cross it LANDED
// (landed-regions-standard-1018, LANDING-CONTRACT L1-L7): ring ot_pl_land_phys_local_w per 24-bit chunk in the H_HI kit top
// on H_HI's r2 root (beside the ret registers), read ot_pl_land_phys_local_r per chunk in the H_LO kit top on H_LO's S root
// (beside u_sout). D 2, E = K 1: +2 edges, fixed latency, no ready / credit. Each chunk owns its slot one-hot and its rq
// (read-slot counter copies <= 24 + 1 loads), each rq from its own leaf of a kept reset forest (ot_pl_land_reset_forest:
// DEPTH stages from the half's rst_n, 32 leaves per branch). Both kit tops use the SAME DEPTH from the slice rst_n, so the
// ring and the read release on the same edge (G == R0; die obligation: rst_n reaches both halves on one edge).
// RMUT (bench only): 1 = reader released one edge late (calendar slip: must FAIL lockstep).
module ot_hbm_su_pglg_seam_w #(
 parameter integer W=1042, CB=24, DEPTH=4,
 parameter integer C=(W+CB-1)/CB
)(
 input wire ck, input wire rst_n,
 input wire [W-1:0] i,
 output wire [2*W-1:0] bank,
 output wire [2*C-1:0] vld
);
 wire [C-1:0] rl;
 ot_pl_land_reset_forest #(.DEPTH(DEPTH),.LEAVES(C)) u_rf(.ck(ck),.d(rst_n),.q(rl));
 for(genvar c=0;c<C;c=c+1)begin:g_chunk
  localparam integer CW=(W-c*CB<CB)?W-c*CB:CB;
  wire [2*CW-1:0] cb;
  (* keep_hierarchy="yes" *) ot_pl_land_phys_local_w #(.W(CW),.D(2),.ID(c)) u_local(.ck(ck),.rsi(rl[c]),
   .i(i[c*CB+:CW]),.bank(cb),.vld(vld[c*2+:2]));
  for(genvar s=0;s<2;s=s+1)begin:g_slot assign bank[s*W+c*CB+:CW]=cb[s*CW+:CW]; end
 end
endmodule

module ot_hbm_su_pglg_seam_r #(
 parameter integer W=1042, CB=24, DEPTH=4, RMUT=0,
 parameter integer C=(W+CB-1)/CB
)(
 input wire ck, input wire rst_n,
 input wire [2*W-1:0] bank,
 input wire [2*C-1:0] vld,
 output wire [W-1:0] o
);
 wire [C-1:0] rl;
 ot_pl_land_reset_forest #(.DEPTH(DEPTH+((RMUT==1)?1:0)),.LEAVES(C)) u_rf(.ck(ck),.d(rst_n),.q(rl));
 for(genvar c=0;c<C;c=c+1)begin:g_chunk
  localparam integer CW=(W-c*CB<CB)?W-c*CB:CB;
  wire [2*CW-1:0] cb;
  for(genvar s=0;s<2;s=s+1)begin:g_slot assign cb[s*CW+:CW]=bank[s*W+c*CB+:CW]; end
  (* keep_hierarchy="yes" *) ot_pl_land_phys_local_r #(.W(CW),.D(2),.K(1),.ID(c)) u_local(.ck(ck),.rsi(rl[c]),
   .bank(cb),.vld(vld[c*2+:2]),.o(o[c*CB+:CW]));
 end
endmodule
`default_nettype wire
