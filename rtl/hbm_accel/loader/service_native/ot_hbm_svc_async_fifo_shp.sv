`default_nettype none
// SPSC Gray-pointer FIFO, SHARED-POINTER bit-sliced storage (HBMc/TILES2 kshare r5a, 2026-10-22; REVIEW REQUIRED before
// any gate: a new reviewed_gray/async_gray primitive).
// Control = ot_hbm_svc_async_fifo verbatim (same register names, same Gray/online publication and 2-stage synchronisers,
// same full/empty/ready/valid/flags).  Only the storage changes: the WIDTH-bit word is split into NS <= SW-bit slices;
// each slice owns DEPTH x B storage plus PRIVATE same-domain copies of the binary write / read slot index (wa / ra),
// advanced on the same fire as wr_bin / rd_bin and reset by a per-group ot_reset_sync on the same both_reset, so
// wa == wr_bin[AW-1:0] and ra == rd_bin[AW-1:0] on every edge after reset (no fire can occur before both online flags
// have crossed, i.e. long after every group sync released).  rd_data slice = mem_s[ra] (FWFT, as mem[rd_bin]).
// Why: r4/r4c used NS lockstep copies of the whole reviewed FIFO per lane (80 x 4 CDC FIFOs) only to keep every pointer
// / decode net <= 32 loads; here ONE pointer pair crosses per FIFO and the fan-out is carried by same-domain copies.
// Census shape: wr_fire -> NG kept group ANDs -> one kept AND per slice; read select rs[d] -> B AND pins + 1 (B <= 7);
// v4 (r5a gate 10-22, census max 57): a binary read index ra[AW-1:0] -> mem[ra] is flattened by abc into AOI terms that
// reuse every ra bit up to 2 x DEPTH/2 x B times (ra[2] QN 57 loads at DEPTH 8, B 7); the read slot is now a kept
// one-hot ring rs (rs == 1 << rd_bin[AW-1:0] every edge) and rd_data = OR_d (rs[d] & mem[d]).
// group reset sync -> GS slices x (AW + 1) <= 32.
(* keep_hierarchy = "yes" *)
module ot_hbm_svc_shp_and2(input wire a,b,output wire y); assign y=a&b; endmodule
// Group release leaf: N kept copies of the side's own online flag (D = wr_online / rd_online, NOT a constant 1: a D=1
// leaf on the same reset is logically identical to wr_online / rd_online and synthesis merged them, r5a gate 10-22).
(* keep_hierarchy = "yes" *)
module ot_hbm_svc_shp_leaf #(parameter integer N=1)(input wire clk,rst_n_in,d,output wire [N-1:0] rst_n);
 (* keep="true",dont_touch="true" *) reg [N-1:0] q;
 always @(posedge clk or negedge rst_n_in) if(!rst_n_in) q<={N{1'b0}}; else q<={N{d}};
 assign rst_n=q;
endmodule

module ot_hbm_svc_async_fifo_shp #(parameter integer WIDTH=32,DEPTH=8,SW=7,GS=7)(
 input wire wr_clk,wr_rst_n,wr_valid,output wire wr_ready,
 input wire [WIDTH-1:0] wr_data,output reg wr_overflow,
 input wire rd_clk,rd_rst_n,output wire rd_valid,input wire rd_ready,
 output wire [WIDTH-1:0] rd_data,output reg rd_underflow
);
 localparam integer AW=$clog2(DEPTH),PW=AW+1;
 localparam integer NS=(WIDTH+SW-1)/SW,NG=(NS+GS-1)/GS;
 initial if(DEPTH<4||(DEPTH&(DEPTH-1))!=0)$error("FIFO depth must be power-of-two >=4");
 wire both_reset=wr_rst_n&&rd_rst_n;wire wr_reset,rd_reset;
 ot_reset_sync u_wr_reset(.clk(wr_clk),.async_rst_n(both_reset),.sync_rst_n(wr_reset));
 ot_reset_sync u_rd_reset(.clk(rd_clk),.async_rst_n(both_reset),.sync_rst_n(rd_reset));
 reg [PW-1:0] wr_bin,wr_gray,rd_bin,rd_gray;
 (* async_reg="true" *)reg [PW-1:0] rd_gray_w1,rd_gray_w2,wr_gray_r1,wr_gray_r2;
 reg wr_online,rd_online;
 (* async_reg="true" *)reg rd_online_w1,rd_online_w2,wr_online_r1,wr_online_r2;
 wire full=wr_gray=={~rd_gray_w2[PW-1:PW-2],rd_gray_w2[PW-3:0]};
 wire empty=rd_gray==wr_gray_r2;
 assign wr_ready=wr_reset&&rd_online_w2&&!full;
 assign rd_valid=rd_reset&&wr_online_r2&&!empty;
 wire wr_fire=wr_valid&&wr_ready,rd_fire=rd_valid&&rd_ready;
 wire [PW-1:0] wr_next=wr_bin+wr_fire,rd_next=rd_bin+rd_fire;
 always @(posedge wr_clk or negedge wr_reset)begin
  if(!wr_reset)begin
   wr_bin<=0;wr_gray<=0;rd_gray_w1<=0;rd_gray_w2<=0;
   wr_online<=0;rd_online_w1<=0;rd_online_w2<=0;wr_overflow<=0;
  end else begin
   wr_online<=1;rd_online_w1<=rd_online;rd_online_w2<=rd_online_w1;
   rd_gray_w1<=rd_gray;rd_gray_w2<=rd_gray_w1;
   if(wr_valid&&!wr_ready)wr_overflow<=1;
   if(wr_fire)begin wr_bin<=wr_next;wr_gray<=(wr_next>>1)^wr_next;end
  end
 end
 always @(posedge rd_clk or negedge rd_reset)begin
  if(!rd_reset)begin
   rd_bin<=0;rd_gray<=0;wr_gray_r1<=0;wr_gray_r2<=0;
   rd_online<=0;wr_online_r1<=0;wr_online_r2<=0;rd_underflow<=0;
  end else begin
   rd_online<=1;wr_online_r1<=wr_online;wr_online_r2<=wr_online_r1;
   wr_gray_r1<=wr_gray;wr_gray_r2<=wr_gray_r1;
   if(rd_ready&&!rd_valid)rd_underflow<=1;
   if(rd_fire)begin rd_bin<=rd_next;rd_gray<=(rd_next>>1)^rd_next;end
  end
 end
 // ---- shared-pointer storage
 genvar g,s;
 wire [NG-1:0] gw_reset,gr_reset,gw_fire,gr_fire;
 // Group reset leaves (r5a gate 10-22: per-group ot_reset_sync copies are logically identical and synthesis merged them
 // back into one 140-load flop): ONE ot_reset_sync per side (u_wr_reset / u_rd_reset, above) resets a KEPT same-domain
 // leaf per group that copies the side's online flag (release = wr_reset / rd_reset + 2 edges).  A write fire needs
 // rd_online_w2, a read fire wr_online_r2: both are themselves reset by wr_reset / rd_reset, so they rise >= 2 own-clock
 // edges after it and the slot-index copies are out of reset by the first fire (bench invariant + release margin).
 // Bench-only mutant OT_SHP_MUT_RS_DEEP adds one more leaf stage (review 10:45 (b)).
 wire [NG-1:0] gw_l0,gr_l0;
 ot_hbm_svc_shp_leaf #(.N(NG)) u_gw_leaf(.clk(wr_clk),.rst_n_in(wr_reset),.d(wr_online),.rst_n(gw_l0));
 ot_hbm_svc_shp_leaf #(.N(NG)) u_gr_leaf(.clk(rd_clk),.rst_n_in(rd_reset),.d(rd_online),.rst_n(gr_l0));
`ifdef OT_SHP_MUT_RS_DEEP
 ot_rst_fanout #(.N(1)) u_gw_mut[NG-1:0](.clk(wr_clk),.rst_n_in(gw_l0),.rst_n(gw_reset));
 ot_rst_fanout #(.N(1)) u_gr_mut[NG-1:0](.clk(rd_clk),.rst_n_in(gr_l0),.rst_n(gr_reset));
`else
 assign gw_reset=gw_l0; assign gr_reset=gr_l0;
`endif
 generate for(g=0;g<NG;g=g+1)begin:g_g
  (* keep="true" *) ot_hbm_svc_shp_and2 u_gw(.a(wr_fire),.b(gw_reset[g]),.y(gw_fire[g]));
  (* keep="true" *) ot_hbm_svc_shp_and2 u_gr(.a(rd_fire),.b(gr_reset[g]),.y(gr_fire[g]));
 end
 for(s=0;s<NS;s=s+1)begin:g_s
  localparam integer B=(WIDTH-s*SW<SW)?WIDTH-s*SW:SW;
  wire wf,rf;
  // u_wf / u_rf re-AND the group reset already inside gw_fire / gr_fire (logically redundant, review 10:45 (d)): kept on
  // purpose as the per-slice kept driver, so each group fire net drives GS AND pins, not GS x (B write enables + AW).
  (* keep="true" *) ot_hbm_svc_shp_and2 u_wf(.a(gw_fire[s/GS]),.b(gw_reset[s/GS]),.y(wf));
  (* keep="true" *) ot_hbm_svc_shp_and2 u_rf(.a(gr_fire[s/GS]),.b(gr_reset[s/GS]),.y(rf));
  (* keep="true",dont_touch="true" *) reg [AW-1:0] wa;   // per-slice copy: must not be merged
  // per-slice one-hot read slot (v4): rs == 1 << rd_bin[AW-1:0]; each rs[d] drives B AND pins + the next ring stage
  (* keep="true",dont_touch="true",fsm_encoding="none" *) reg [DEPTH-1:0] rs;
  (* mem2reg *) reg [B-1:0] mem[0:DEPTH-1];   // explicit flops, like the reviewed FIFO (async_fifo_hierarchy_audit)
  always @(posedge wr_clk or negedge gw_reset[s/GS]) if(!gw_reset[s/GS]) wa<=0; else if(wf) wa<=wa+1'b1;
  always @(posedge wr_clk) if(wf) mem[wa]<=wr_data[s*SW+:B];
  always @(posedge rd_clk or negedge gr_reset[s/GS]) if(!gr_reset[s/GS]) rs<={{(DEPTH-1){1'b0}},1'b1};
   else if(rf) rs<={rs[DEPTH-2:0],rs[DEPTH-1]};
  reg [B-1:0] rdm; integer d;
  always @* begin rdm={B{1'b0}}; for(d=0;d<DEPTH;d=d+1) rdm=rdm|({B{rs[d]}}&mem[d]); end
  assign rd_data[s*SW+:B]=rdm;
 end endgenerate
endmodule
`default_nettype wire
