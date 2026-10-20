`timescale 1ns/1ps
`default_nettype none
// Adapter for CLOSED ot_su12_sfu, whose lane index is physically fixed at5.
// Four registered edges; native broadcast/retirement must price and bind them.
module ot_hgi_sfu_lane_map #(parameter integer MUT_LANE=0,
 // LH-SU (10-19): PASS_OHREP > 0 replicates the pass ring's one-hot per PASS_OHREP bits (ot_hdc_delay_ring OHREP)
 parameter integer PASS_OHREP=0) (
 input wire clk, rst_n,
 input wire [3:0] lane_j,
 input wire [479:0] ld_terms,
 input wire [23:0] i_o_v, i_i_v, i_krow,
 input wire [3:0] i_ls, i_lvw,
 input wire i_emit,
 input wire [460:0] i_pass,
 output reg [1199:0] o_ld_c,
 output reg [23:0] o_o_v, o_i_v, o_krow,
 output reg [3:0] o_ls, o_lvw,
 output reg o_emit,
 output wire [460:0] o_pass
);
 reg f_rst; always @(posedge clk) f_rst<=rst_n;
 reg [479:0] terms0;
 reg [23:0] ov0,iv0,row0;
 reg [3:0] ls0,lvw0,j0;
 reg emit0,emit1,emit2;
 reg [79:0] meta1,meta2;
 // ld is control, not retained payload: reset must not replay a ring slot.
 reg [3:0] ld_pipe;
 generate if(PASS_OHREP>0)begin:g_prep
  ot_hdc_delay_ring_rep #(.W(460),.D(4),.OHREP(PASS_OHREP)) u_pass (.clk(clk),.rst_n(rst_n),.d(i_pass[459:0]),.q(o_pass[459:0]));
 end else begin:g_pring
  ot_hdc_delay_ring #(.W(460),.D(4),.RING(3)) u_pass (.clk(clk),.rst_n(rst_n),.d(i_pass[459:0]),.q(o_pass[459:0]));
 end endgenerate
 assign o_pass[460]=ld_pipe[3];
 reg [23:0] term1[0:19],pair2[0:9];
 always @(posedge clk) begin
  terms0<=ld_terms; ov0<=i_o_v; iv0<=i_i_v; row0<=i_krow;
  ls0<=i_ls; lvw0<=i_lvw; j0<=lane_j ^ 4'(MUT_LANE);
  // All integer expressions wrap at24 bits, as the frozen lane's kadd.
  meta1<={24'(ov0 + (24'(j0)>>ls0) - (24'd5>>ls0)),
          24'(iv0 + (24'(j0)&((24'd1<<ls0)-1)) - (24'd5&((24'd1<<ls0)-1))),
          24'(row0 + (24'(j0)>>ls0) - (24'd5>>ls0)),
          ls0,(lvw0<3 ? 4'd3 : lvw0)};
  meta2<=meta1;
  {o_o_v,o_i_v,o_krow,o_ls,o_lvw}<=meta2;
  for(integer s=0;s<5;s=s+1) begin
   for(integer k=0;k<4;k=k+1)
    term1[s*4+k]<=j0[k] ? terms0[(s*4+k)*24+:24] : 24'd0;
   pair2[s*2]<=term1[s*4]+term1[s*4+1];
   pair2[s*2+1]<=term1[s*4+2]+term1[s*4+3];
   o_ld_c[s*240+:240]<={216'd0,24'(pair2[s*2]+pair2[s*2+1])};
  end
  if(!f_rst) begin emit0<=0;emit1<=0;emit2<=0;o_emit<=0;ld_pipe<=0;end
  else begin emit0<=i_emit;emit1<=emit0 && (24'(j0)<(24'd1<<lvw0));emit2<=emit1;o_emit<=emit2;ld_pipe<={ld_pipe[2:0],i_pass[460]};end
 end
endmodule
`default_nettype wire
// LH-SU (10-19, safe-design item 3): ot_hdc_delay_ring RING form (D >= 4: D-1 slots + output register, slot written at
// edge e read into q at edge e + D - 1) with REPLICATED one-hot slot registers: ceil(W / OHREP) kept copies
// ((* keep *), ot_keep_regs.tcl), copy c driving only bits [c*OHREP, (c+1)*OHREP), so each one-hot bit sees OHREP write
// enables + OHREP read ANDs instead of 2*W loads (W = 460: 1,381). Same q edge for edge as ot_hdc_delay_ring RING.
// (Kept in this file: the closed lane manifest freezes ot_hdc_delay_ring.sv, and every lane_map source list carries this file.)
module ot_hdc_delay_ring_rep #(
    parameter integer W = 32,
    parameter integer D = 4,
    parameter integer RESET = 0,
    parameter integer OHREP = 16
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    generate
        if (D < 4) begin : g_bad
            ot_hdc_delay_ring_rep_requires_D_ge_4 u_refuse();
        end else begin : g_ringr
            localparam integer N = D - 1;
            localparam integer RW = (OHREP > 0 && OHREP < W) ? OHREP : W;   // bits per one-hot copy
            localparam integer NC = (W + RW - 1) / RW;          // one-hot copies
            genvar c, j;
            for (c = 0; c < NC; c = c + 1) begin : g_c
                localparam integer LO = c * RW, HI = ((c + 1) * RW > W) ? W : (c + 1) * RW, CW = HI - LO;
                (* keep = "true", dont_touch = "true" *) reg [N-1:0] oh;   // this copy's one-hot slot
                always @(posedge clk or negedge rst_n)
                    if (!rst_n) oh <= {{(N-1){1'b0}}, 1'b1};
                    else oh <= {oh[N-2:0], oh[N-1]};
                wire [CW*N-1:0] slots;
                for (j = 0; j < N; j = j + 1) begin : g_s
                    reg [CW-1:0] m;
                    if (RESET != 0) begin : g_rst
                        always @(posedge clk or negedge rst_n)
                            if (!rst_n) m <= {CW{1'b0}}; else if (oh[j]) m <= d[HI-1:LO];
                    end else begin : g_nrst
                        always @(posedge clk) if (oh[j]) m <= d[HI-1:LO];
                    end
                    assign slots[j*CW +: CW] = m & {CW{oh[j]}};
                end
                reg [CW-1:0] r;
                integer i;
                always @(*) begin
                    r = {CW{1'b0}};
                    for (i = 0; i < N; i = i + 1) r = r | slots[i*CW +: CW];
                end
                reg [CW-1:0] qr;
                if (RESET != 0) begin : g_qrst
                    always @(posedge clk or negedge rst_n) if (!rst_n) qr <= {CW{1'b0}}; else qr <= r;
                end else begin : g_qnrst
                    always @(posedge clk) qr <= r;
                end
                assign q[HI-1:LO] = qr;
            end
        end
    endgenerate
endmodule
`timescale 1ns/1ps
`default_nettype none
// L2H-SU-FB k9x (10-19, safe-design items 2/3/5; grid BTREE=3): the controller -> 16 lane-mapper broadcast as a
// FOUR-LEVEL REGISTERED DISTRIBUTION TREE that uses exactly the mapper's own four registered edges (no added edge).
// Why: k9s2/k9r/k9w gates stalled in GPL (congestion 1.08-1.17, 4% tiles overflowed, 39k long wires, 424k-net
// timing repair). The mono mapper (BTREE=0) had every one of the 1,022 broadcast bits drive 16 lane captures spread
// over the whole 1.9 mm tile (one unregistered star hop from the N-face control register to all four faces), and
// each lane kept its own 460-bit x 4-edge pass delay (29k flops: 22,080 ring slots + 7,360 outputs).
// Here the four mapper edges ARE the distance hops:
//   L0 (edge 0, 2 kept copies)  A = lanes 0-3 + 12-15 (W + S faces), B = lanes 4-11 (N + E faces)   -- pure capture
//   L1 (edge 1, 4 kept copies)  one per face group q = j/4                                          -- pure capture
//   L2 (edge 2, 8 copies)       one per lane pair p = j/2: both lanes' pair sums + mapped metadata (j is constant)
//   L3 (edge 3, 16)             one per lane: ld_c final add, metadata, emit, pass
// Same function edge for edge as ot_hgi_sfu_lane_map (mono): o_ld_c / o_o_v.. / o_emit / o_pass at edge 3 of a
// capture at edge 0. The pass payload is a plain delay, so its 4 edges are the 4 tree levels (no per-lane ring):
// 460 x (2+4+8+16) = 13.8k flops instead of 29k, every hop <= ~450 um on the floorplan (N face -> W/S corner over
// 6 registered segments incl. the pin and quarter control registers). Clock: each level runs on the clk_map root of
// its first lane (same die clock, flop-to-flop crossings judged per pair like BTREE=1); reset: each level clears its
// emit/ld bits on its own registered rst_map_n copy (all rst_map_n release on the same edge, RST_TREE).
module ot_hgi_sfu_bcast_tree4 #(parameter integer MUT_TREE=0) (   // MUT_TREE 1: lane 13's pass skips L2 (must FAIL)
 input wire [15:0] clk_map, rst_map_n,
 input wire [479:0] ld_terms,
 input wire [23:0] i_o_v, i_i_v, i_krow,
 input wire [3:0] i_ls, i_lvw,
 input wire i_emit,
 input wire [460:0] i_pass,
 output wire [16*1200-1:0] o_ld_c,
 output wire [16*24-1:0] o_o_v, o_i_v, o_krow,
 output wire [16*4-1:0] o_ls, o_lvw,
 output wire [15:0] o_emit,
 output wire [16*461-1:0] o_pass
);
 localparam integer CW=480+72+8+1+461;   // terms, o/i/row, ls/lvw, emit, pass (incl. ld)
 // ---- L0: two kept capture copies
 wire [CW-1:0] l0 [0:1];
 for(genvar a=0;a<2;a=a+1)begin:g_l0
  localparam integer CK=(a==0)?0:4;
  reg f_rst; always @(posedge clk_map[CK]) f_rst<=rst_map_n[CK];
  (* keep = "true" *) reg [CW-3:0] d;   // data (no reset)
  (* keep = "true" *) reg emit, ld;
  always @(posedge clk_map[CK]) begin
   d<={ld_terms,i_o_v,i_i_v,i_krow,i_ls,i_lvw,i_pass[459:0]};
   if(!f_rst)begin emit<=1'b0;ld<=1'b0;end else begin emit<=i_emit;ld<=i_pass[460];end
  end
  assign l0[a]={d,emit,ld};
 end
 // ---- L1: one kept copy per face group q (q0 W, q3 S from A; q1 N, q2 E from B)
 wire [CW-1:0] l1 [0:3];
 for(genvar q=0;q<4;q=q+1)begin:g_l1
  localparam integer CK=4*q;
  localparam integer SRC=(q==0||q==3)?0:1;
  reg f_rst; always @(posedge clk_map[CK]) f_rst<=rst_map_n[CK];
  (* keep = "true" *) reg [CW-3:0] d;
  (* keep = "true" *) reg emit, ld;
  always @(posedge clk_map[CK]) begin
   d<=l0[SRC][CW-1:2];
   if(!f_rst)begin emit<=1'b0;ld<=1'b0;end else begin emit<=l0[SRC][1];ld<=l0[SRC][0];end
  end
  assign l1[q]={d,emit,ld};
 end
 // ---- L2 (per lane pair) + L3 (per lane)
 for(genvar p=0;p<8;p=p+1)begin:g_l2
  localparam integer CK=2*p;
  reg f_rst; always @(posedge clk_map[CK]) f_rst<=rst_map_n[CK];
  wire [479:0] t1; wire [23:0] ov1,iv1,row1; wire [3:0] ls1,lvw1; wire [459:0] ps1; wire emit1,ld1;
  assign {t1,ov1,iv1,row1,ls1,lvw1,ps1,emit1,ld1}=l1[p/2];
  (* keep = "true" *) reg [459:0] ps2;
  (* keep = "true" *) reg ld2;
  always @(posedge clk_map[CK]) begin
   ps2<=ps1;
   if(!f_rst) ld2<=1'b0; else ld2<=ld1;
  end
  for(genvar h=0;h<2;h=h+1)begin:g_ln
   localparam integer J=2*p+h;
   localparam [3:0] JJ=4'(J);
   // edge 2 (mono: pair2 / meta1 -> meta2 / emit1 -> emit2), computed from the L1 copy (= mono's edge-0 capture,
   // one edge later); mono's edge-1 term select by the constant lane index is wiring here
   reg [23:0] pair2[0:9];
   reg [79:0] meta2;
   reg emit2;
   always @(posedge clk_map[CK]) begin
    for(integer s=0;s<5;s=s+1)begin
     pair2[s*2]  <=(JJ[0]?t1[(s*4+0)*24+:24]:24'd0)+(JJ[1]?t1[(s*4+1)*24+:24]:24'd0);
     pair2[s*2+1]<=(JJ[2]?t1[(s*4+2)*24+:24]:24'd0)+(JJ[3]?t1[(s*4+3)*24+:24]:24'd0);
    end
    meta2<={24'(ov1 + (24'(JJ)>>ls1) - (24'd5>>ls1)),
            24'(iv1 + (24'(JJ)&((24'd1<<ls1)-1)) - (24'd5&((24'd1<<ls1)-1))),
            24'(row1 + (24'(JJ)>>ls1) - (24'd5>>ls1)),
            ls1,(lvw1<3 ? 4'd3 : lvw1)};
    if(!f_rst) emit2<=1'b0; else emit2<=emit1 && (24'(JJ)<(24'd1<<lvw1));
   end
   // edge 3: the lane's own registers on its clk_map[J] root
   reg f3; always @(posedge clk_map[J]) f3<=rst_map_n[J];
   reg [1199:0] ldc3; reg [23:0] ov3,iv3,row3; reg [3:0] ls3,lvw3; reg emit3, ld3; reg [459:0] ps3;
   always @(posedge clk_map[J]) begin
    for(integer s=0;s<5;s=s+1) ldc3[s*240+:240]<={216'd0,24'(pair2[s*2]+pair2[s*2+1])};
    {ov3,iv3,row3,ls3,lvw3}<=meta2;
    ps3<=(MUT_TREE!=0 && J==13) ? ps1 : ps2;
    if(!f3)begin emit3<=1'b0;ld3<=1'b0;end else begin emit3<=emit2;ld3<=ld2;end
   end
   assign o_ld_c[J*1200+:1200]=ldc3;
   assign o_o_v[J*24+:24]=ov3; assign o_i_v[J*24+:24]=iv3; assign o_krow[J*24+:24]=row3;
   assign o_ls[J*4+:4]=ls3; assign o_lvw[J*4+:4]=lvw3; assign o_emit[J]=emit3;
   assign o_pass[J*461+:461]={ld3,ps3};
  end
 end
endmodule
`default_nettype wire
