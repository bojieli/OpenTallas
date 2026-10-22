`timescale 1ns/1ps
`default_nettype none
// LANDW native32 structural successor; original ot_qfd_land8 remains unchanged.
// Four-bit data regions instead of16 limit warm/select decoding to8*4=32
// final datapath loads. Region counters/reset/epochs/first-use edges unchanged.
// W<=116 bounds source en_s0 fanout at29 data+1meta+en_icg+en_qm=32.
// This modeled bound still requires mapped all-root census before any gate.
// Same-edge receiver calendar copies, one per <=4 data regions. No protocol edge is added.
(* keep_hierarchy = "yes" *)
module ot_qfd_land8_ctrl_copy #(parameter integer ID=0)(
 input wire ck, input wire rs, input wire [3:0] k,
 output wire [2:0] nxt_o, output wire [2:0] seed_o
);
 (* keep="true", dont_touch="true" *) reg rs0,rs1;
 always @(posedge ck or negedge rs) if (!rs) rs0<=1'b0;else rs0<=1'b1;
 always @(posedge ck or negedge rs0) if (!rs0) rs1<=1'b0;else rs1<=1'b1;
 (* keep="true", dont_touch="true" *) reg [3:0] k_q,rc;
`ifdef OT_QFD_LAND8_MUT_K3
 always @(posedge ck) k_q<={1'b0,k[2:0]};
`else
 always @(posedge ck) k_q<=k;
`endif
 always @(posedge ck or negedge rs1) if (!rs1) rc<=4'b0;else rc<=rc+1'b1;
`ifdef OT_QFD_LAND8_MUT_SEL
 wire [3:0] nxt=rc+4'd2-k_q;wire [3:0] seed=4'd1-k_q;
`else
 wire [3:0] nxt=rc+4'd1-k_q;wire [3:0] seed=4'd0-k_q;
`endif
 assign nxt_o=nxt[2:0];assign seed_o=seed[2:0];
endmodule

// RSL=1 calendar copy (QW-LANDW3 10-20): first reset stage comes from the parent's kept face copy rs0c (ONE face flop
// per <=8 copies), only the second stage rs1 is local.  rs -> rs0c -> rs1 -> rc releases on the same edges as the RSL=0
// copy (rs -> rs0 -> rs1 -> rc): no reset edge, K or calendar change; assert stays asynchronous through the chain.
(* keep_hierarchy = "yes" *)
module ot_qfd_land8_ctrl_copy1 #(parameter integer ID=0)(
 input wire ck, input wire rs0, input wire [3:0] k,
 output wire [2:0] nxt_o, output wire [2:0] seed_o
);
 (* keep="true", dont_touch="true" *) reg rs1;
 always @(posedge ck or negedge rs0) if (!rs0) rs1<=1'b0;else rs1<=1'b1;
 (* keep="true", dont_touch="true" *) reg [3:0] k_q,rc;
`ifdef OT_QFD_LAND8_MUT_K3
 always @(posedge ck) k_q<={1'b0,k[2:0]};
`else
 always @(posedge ck) k_q<=k;
`endif
`ifdef OT_QFD_LAND8_MUT_RSL
 // mutant: the copy lands rs0c once more (one extra release edge vs the meta/region calendar)
 (* keep="true" *) reg rs2;
 always @(posedge ck or negedge rs1) if (!rs1) rs2<=1'b0;else rs2<=1'b1;
 always @(posedge ck or negedge rs2) if (!rs2) rc<=4'b0;else rc<=rc+1'b1;
`else
 always @(posedge ck or negedge rs1) if (!rs1) rc<=4'b0;else rc<=rc+1'b1;
`endif
`ifdef OT_QFD_LAND8_MUT_SEL
 wire [3:0] nxt=rc+4'd2-k_q;wire [3:0] seed=4'd1-k_q;
`else
 wire [3:0] nxt=rc+4'd1-k_q;wire [3:0] seed=4'd0-k_q;
`endif
 assign nxt_o=nxt[2:0];assign seed_o=seed[2:0];
endmodule

module ot_qfd_land8_fan32 #(
    parameter integer W    = 32,
    parameter integer ICG  = 1,      // 1: hop-0 clock gate on ck_s (registered enable); 0: no gate (fallback)
    parameter integer RSL  = 0       // 1: rs reaches exactly 2 face flops (rs0 + kept rs0c); calendar copies take rs0c
) (
    input  wire         ck_s,        // source block root (ring write side)
    input  wire         en,          // source released reset (active high)
    input  wire [W-1:0] i,
    input  wire         ck,          // receiving block root
    input  wire         rs,          // receiving block regional reset, active low
    input  wire [3:0]   k,           // K strap (four identity straps from the instance's own tie cells)
    output wire [W-1:0] o,
    output reg          fault
);
    localparam integer NR = (W + 3) / 4;
    // ---------------------------------------------------------------- source-side en landing (registered ICG enable)
    (* keep = "true", dont_touch = "true" *) reg en_s0;
`ifdef OT_QFD_LAND8_MUT_ENCOMB
    always @(*) en_s0 = en;                                  // mutant: no en register at all (en -> gate / epoch)
`else
    always @(posedge ck_s or negedge en)
        if (!en) en_s0 <= 1'b0; else en_s0 <= 1'b1;
`endif
    (* keep = "true", dont_touch = "true" *) reg en_icg;    // the ONLY driver of the ICG enable pin
`ifdef OT_QFD_LAND8_MUT_ENCOMB
    always @(*) en_icg = en_s0;                              // mutant: en combinational into the gate (closed-view form)
`else
    always @(posedge ck_s or negedge en_s0)
        if (!en_s0) en_icg <= 1'b0; else en_icg <= 1'b1;
`endif
    wire wck;
    generate if (ICG != 0) begin : g_icg
        ot_qfd_land8_gate u_fwd0 (.ck(ck_s), .en(en_icg), .gclk(wck));
    end else begin : g_nogate
        assign wck = ck_s;
    end endgenerate
    // write epoch counter (metadata only), its own en copy
    (* keep = "true", dont_touch = "true" *) reg en_qm;
`ifdef OT_QFD_LAND8_MUT_ENCOMB
    always @(*) en_qm = en_s0;
`else
    always @(posedge ck_s or negedge en_s0)
        if (!en_s0) en_qm <= 1'b0; else en_qm <= 1'b1;
`endif
    reg [3:0] wc;
    always @(posedge wck or negedge en_qm)
        if (!en_qm) wc <= 4'b0; else wc <= wc + 1'b1;
    // ---------------------------------------------------------------- receiver-side reset landing, counters
    (* keep = "true", dont_touch = "true" *) reg rs0, rs1;
    always @(posedge ck or negedge rs)
        if (!rs) rs0 <= 1'b0; else rs0 <= 1'b1;
    always @(posedge ck or negedge rs0)
        if (!rs0) rs1 <= 1'b0; else rs1 <= 1'b1;
    reg [3:0] k_q;
`ifdef OT_QFD_LAND8_MUT_K3
    always @(posedge ck) k_q <= {1'b0, k[2:0]};              // mutant: three-pin K silently zero-extended (D4 ABI)
`else
    always @(posedge ck) k_q <= k;
`endif
    reg [3:0] rc;
    reg warm;
    wire warm_next = warm | (rc == k_q - 1'b1);
    always @(posedge ck or negedge rs1)
        if (!rs1) begin rc <= 4'b0; warm <= 1'b0; end
        else begin rc <= rc + 1'b1; warm <= warm_next; end
`ifdef OT_QFD_LAND8_MUT_SEL
    wire [3:0] nxt = rc + 4'd2 - k_q;                        // mutant: read slot one late
    wire [3:0] seed = 4'd1 - k_q;
`else
    wire [3:0] nxt = rc + 4'd1 - k_q;
    wire [3:0] seed = 4'd0 - k_q;
`endif
    // ---------------------------------------------------------------- data regions + metadata region
    wire [W-1:0] o_r;
    assign o = o_r;
    localparam integer NC=(NR+3)/4;
    wire [NC*3-1:0] local_nxt,local_seed;
    genvar c;
    generate if (RSL != 0) begin : g_rsl
      // second face copy of the first reset stage (same D/clear as rs0): the rs port net has 2 flop sinks
      (* keep = "true", dont_touch = "true" *) reg rs0c;
      always @(posedge ck or negedge rs)
          if (!rs) rs0c <= 1'b0; else rs0c <= 1'b1;
      for(c=0;c<NC;c=c+1)begin:g_ctrl
        ot_qfd_land8_ctrl_copy1 #(.ID(c)) u_ctrl(
          .ck(ck),.rs0(rs0c),.k(k),.nxt_o(local_nxt[c*3+:3]),.seed_o(local_seed[c*3+:3]));
      end
    end else begin : g_rsl0
      for(c=0;c<NC;c=c+1)begin:g_ctrl
        ot_qfd_land8_ctrl_copy #(.ID(c)) u_ctrl(
          .ck(ck),.rs(rs),.k(k),.nxt_o(local_nxt[c*3+:3]),.seed_o(local_seed[c*3+:3]));
      end
    end endgenerate
    genvar r;
    generate for (r = 0; r < NR; r = r + 1) begin : g_region
        localparam integer LO = r * 4, N = (W - LO < 4) ? W - LO : 4;
        wire [7:0] vld_u, rds_u;
        ot_qfd_land8_region #(.W(N)) u_region (
            .wck(wck), .ckw(ck_s), .en_s0(en_s0), .i(i[LO +: N]), .ck(ck), .rs0(rs0),
            .rnext(local_nxt[(r/4)*3+:3]), .rseed(local_seed[(r/4)*3+:3]), .warm_next(warm_next),
            .vld_o(vld_u), .rdsel_o(rds_u), .o(o_r[LO +: N]));
    end endgenerate
    // metadata: the write epoch of every slot, read through the region's own select into an aligned compare
    wire [7:0] vld_m, rds_m;
    wire [3:0] ep_o;
    ot_qfd_land8_region #(.W(4)) u_meta (
        .wck(wck), .ckw(ck_s), .en_s0(en_s0), .i(wc), .ck(ck), .rs0(rs0),
        .rnext(nxt[2:0]), .rseed(seed[2:0]), .warm_next(warm_next),
        .vld_o(vld_m), .rdsel_o(rds_m), .o(ep_o));
    reg [3:0] exp_d;
    reg chk_d;
    always @(posedge ck) begin exp_d <= rc - k_q; chk_d <= warm && |(rds_m & vld_m); end
    always @(posedge ck or negedge rs1)
        if (!rs1) fault <= 1'b0;
        else if (chk_d && ep_o != exp_d) fault <= 1'b1;
`ifndef SYNTHESIS
    initial if (W < 1 || W > 116) $fatal(1, "ot_qfd_land8: 1 <= W <= 116 (direct FF ring class; wider lanes -> SRAM record)");
`endif
endmodule
`default_nettype wire
