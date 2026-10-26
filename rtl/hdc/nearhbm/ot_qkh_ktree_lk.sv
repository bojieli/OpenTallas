`timescale 1ns/1ps
// KV-DCAL2 10-19 (K.STA.ECTL KPV_LOCKSTEP, ROOT: no blanket lockstep admission; misc_b fold applied in a hard tile).
// ot_qkh_ktree with every lane's registered q-valid read: the K-tree reduction still runs on lane 0's valid (kpv_in[0],
// unchanged timing / data path / cycles), and any lane whose kpv differs from lane 0 in the same edge is a lane fault folded
// into the existing per-lane fault input ahead of the tile's gf_r input register (XOR16 + OR, 2 gate levels, pins still land
// on flops).  The 16 independently clocked / reset lanes are therefore CHECKED in hardware every edge instead of assumed equal:
// a lane released from reset late, a lane valid lost or duplicated, a clock-crossing slip of one lane -> g_f two edges later
// (gf_r -> g_f), the same latency as a lane's own gf.  +0 schedule cycles, +0 flops (gf_r exists), 15 new N-face pins.
// Bench: tools/qwen_kv_die/ktree_lk_bench.sh (rtl/test/qwen_kv_die/tb_qkh_ktree_lk.sv): lockstep miter vs ot_qkh_ktree +
// per-lane skew injection; MUT 1 (lanes 1..15 ignored = the old kpv_in[0]-only wiring) must FAIL.
module ot_qkh_ktree_lk #(
    parameter integer ADD_LAT = 7,
    parameter integer MUL_LAT = 6,
    parameter [31:0]  SCALE = 32'h3DB504F3,
    parameter integer MUT = 0,
    // KVG3-CORES 10-24 (COORD ruling 2: boundary registers in the leaf, face_guard not relaxed): PORT_REGS=1 lands
    // kpv_in[15:1] and gf_in on their own face flops (lane 0 lands on the K-tree's kv_r as before) and compares the lanes
    // REGISTERED (kv_r vs kpv_f): the lane fault reaches gf_r one edge later -> g_f +1 edge (fault path only; sc_d / sc_f
    // data and schedule unchanged, +31 flops).  PORT_REGS=0 = the original combinational XOR16 + OR ahead of gf_r.
    parameter integer PORT_REGS = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [511:0]  kp_in,
    input  wire [15:0]   kpv_in,
    input  wire [15:0]   gf_in,
    output wire [31:0]   sc_d,
    output wire          sc_f,
    output wire          g_f
);
    // gate lk1 (FAIL reset_landing: rst_n reached the 17-region relay's 19 flops directly): land rst_n at the face in 2
    // registered stages (async assert, synchronous release) and feed the closed relay from the landed net only.
    // +2 release edges on this tile's reset (reset window only; no data / schedule cycle).
    (* keep *) reg rst_l0, rst_l1;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin rst_l0 <= 1'b0; rst_l1 <= 1'b0; end
        else begin rst_l0 <= 1'b1; rst_l1 <= rst_l0; end
    wire        kv_q;
    wire [15:0] gf_k;
    generate if (PORT_REGS != 0) begin : g_pr
        // same release edge as the K-tree's kv_r / gf_r (its ot_rst_relay: 2 sync + 1 tree stage on rst_l1)
        wire [0:0] rp;
        ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rp (.clk(clk), .rst_n_in(rst_l1), .rst_n(rp));
        reg [15:1] kpv_f;
        reg [15:0] gf_f;
        always @(posedge clk or negedge rp[0])
            if (!rp[0]) begin kpv_f <= 15'd0; gf_f <= 16'd0; end
            else begin kpv_f <= kpv_in[15:1]; gf_f <= gf_in; end
        wire [15:0] lk_f = (MUT == 1) ? 16'd0 : {kpv_f ^ {15{kv_q}}, 1'b0};
        assign gf_k = gf_f | lk_f;
    end else begin : g_comb
        wire [15:0] lk = (MUT == 1) ? 16'd0 : ({16{kpv_in[0]}} ^ kpv_in);
        assign gf_k = gf_in | lk;
    end endgenerate
    ot_qkh_ktree #(.ADD_LAT(ADD_LAT), .MUL_LAT(MUL_LAT), .SCALE(SCALE)) u_kt (
        .clk(clk), .rst_n(rst_l1), .kp_in(kp_in), .kpv_in(kpv_in[0]), .gf_in(gf_k),
        .sc_d(sc_d), .sc_f(sc_f), .g_f(g_f), .kv_q(kv_q));
endmodule
