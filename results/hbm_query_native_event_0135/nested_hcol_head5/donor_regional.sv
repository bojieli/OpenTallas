`timescale 1ns/1ps
`default_nettype none
// Additive physical master: regional copies of the query/key input pins.
// Each input bit has exactly one capture flop on its own clk_pair region.
// Parent must connect BOTH slices to the same original logical bus; no shared
// capture or cross-region data fanout is introduced. Cycle count and all
// arithmetic/reset logic are identical to ot_hidx_score_hcol.
// PREP ONLY: +1113 data input pins, +0 FF, +0 cycles. Parent pin/window and
// lane capacity must be replanned before physical release. Existing masters
// and production bindings remain unchanged.
module ot_hidx_score_hcol_regional #(
    parameter integer HALF = 0,
    parameter integer MUT  = 0,          // bench mutant (the parent passes it to column 0 only)
    parameter integer DELIVERED_RESET = 0
) (
    input  wire [1:0]      clk_pair,     // regions 2*HALF, 2*HALF+1 of this column
    input  wire            rst_col,      // rr[g] of the glue (column reset relay output)
    input  wire [1:0]      qv_b,
    input  wire [2*QW-1:0] q_b,
    input  wire [2*KW-1:0] key,
    input  wire [4*8-1:0]  hid4,         // head ids 4*HALF .. 4*HALF+3
    input  wire [31:0]     cs_in,        // cs[4*HALF] (HALF 0: tie 0)
    input  wire            cf_in,
    output wire [31:0]     cs_out,       // cs[4*HALF+4]
    output wire            cf_out,
    output wire [1:0]      prdy
);
    localparam integer NB = 4, FPL = 7, FML = 5, QL = 5;
    localparam integer KW = NB * 136;
    localparam integer QW = 8 + NB * 128 + NB * 8 + 16;
    wire [31:0] cs [0:4]; wire cf [0:4];
    assign cs[0] = cs_in; assign cf[0] = cf_in;
    genvar r, hh, bb;
    generate for (r = 0; r < 2; r = r + 1) begin : g_rgn
        localparam integer RR = 2 * HALF + r;            // region within the column (0..3)
        wire ck = clk_pair[r];
        wire [0:0] srr; wire rs = srr[0];
        if(DELIVERED_RESET!=0)begin:g_delivered_reset
            ot_rst_delivered3 #(.REGIONS(1)) u_rr(.clk(ck),.rst_n_in(rst_col),.rst_n(srr));
        end else begin:g_legacy_reset
            ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_rr (.clk(ck), .rst_n_in(rst_col), .rst_n(srr));
        end
        reg rn_p, onl;
        always @(posedge ck) rn_p <= rs;
        always @(posedge ck or negedge rs) if (!rs) onl <= 1'b0; else onl <= rs && rn_p;
        assign prdy[r] = onl;
        reg qv_p; reg [QW-1:0] q_p; reg [KW-1:0] key_p;
        always @(posedge ck) begin qv_p <= qv_b[r] && rn_p; q_p <= q_b[r*QW +: QW]; key_p <= key[r*KW +: KW]; end
        wire [7:0] qh_p = q_p[QW-1 -: 8];
        for (hh = 0; hh < 2; hh = hh + 1) begin : g_h
            localparam integer H = 2 * RR + hh;          // head within the chunk column (0..7)
            localparam integer HL = 2 * r + hh;          // head within this half (0..3)
            reg [7:0] hid_p; always @(posedge ck) hid_p <= hid4[8*HL +: 8];
            reg q_we; reg [QW-9:0] q2; reg [NB*128-1:0] qc; reg [NB*8-1:0] qs; reg [15:0] qw;
            always @(posedge ck) begin
                q_we <= qv_p && rn_p && (qh_p == hid_p);
                q2 <= q_p[QW-9:0];
                if (q_we) {qc, qs, qw} <= q2;
            end
            wire [NB*32-1:0] acc; wire [NB-1:0] afault;
            for (bb = 0; bb < NB; bb = bb + 1) begin : g_blk
                localparam integer DS = (bb == 0) ? 0 : FPL * (bb - 1);
                wire [31:0] bv0; wire bo0; wire [31:0] bv; wire bo;
                ot_hdc_v41x_q4dot_l #(.QL(QL)) u_d (.clk(ck), .a(qc[bb*128 +: 128]), .b(key_p[128*bb +: 128]),
                    .ua(qs[bb*8 +: 8]), .ub(key_p[NB*128 + 8*bb +: 8]), .y(bv0), .ovf(bo0));
                ot_hdc_delay #(.W(33), .D(DS)) u_bd (.clk(ck), .rst_n(1'b1), .d({bo0, bv0}), .q({bo, bv}));
                if (bb == 0) begin : g_first
                    assign acc[31:0] = bv; assign afault[0] = bo;
                end else begin : g_add
                    wire [1:0] err; wire vo_unused; wire pf, bo_d;
                    ot_hdc_delay #(.W(1), .D(FPL)) u_pf (.clk(ck), .rst_n(1'b1), .d(afault[bb-1]), .q(pf));
                    ot_hdc_v41x_faddl #(.LAT(FPL)) u_a (.clk(ck), .rst_n(rs), .valid_in(1'b1),
                        .a(acc[32*(bb-1) +: 32]), .b(bv), .y(acc[32*bb +: 32]), .err(err), .valid_out(vo_unused));
                    ot_hdc_delay #(.W(1), .D(FPL)) u_bf (.clk(ck), .rst_n(1'b1), .d(bo), .q(bo_d));
                    assign afault[bb] = pf || bo_d || (err != 2'd0);
                end
            end
            wire [15:0] sc16; wire sco;
            ot_hdc_v41x_bf16 u_sb (.x(acc[32*(NB-1) +: 32]), .y(sc16), .ovf(sco));
            reg [15:0] rsc; reg rscf;
            always @(posedge ck) begin rsc <= sc16; rscf <= afault[NB-1] || sco; end
            wire [15:0] tm0; wire tmo, rscf_d;
            ot_hdc_v41x_bmul_l #(.ML(FML)) u_m (.clk(ck), .a(rsc), .w(qw), .y(tm0), .ovf(tmo));
            ot_hdc_delay #(.W(1), .D(FML)) u_tf (.clk(ck), .rst_n(1'b1), .d(rscf), .q(rscf_d));
            wire [15:0] tm; wire tf;
            ot_hdc_delay #(.W(17), .D((FPL + 2) * H)) u_td (.clk(ck), .rst_n(1'b1), .d({rscf_d || tmo, tm0}), .q({tf, tm}));
            reg [31:0] csi_p; reg cfi_p; reg [31:0] cs_o; reg cf_o;
            if (MUT == 1 && H == 4) begin : g_mseam   // bench mutant (column 0 only): the half seam one edge late
                reg [31:0] cs_x; reg cf_x;
                always @(posedge ck) begin cs_x <= cs[HL]; cf_x <= cf[HL]; csi_p <= cs_x; cfi_p <= cf_x; end
            end else begin : g_nseam
                always @(posedge ck) begin csi_p <= cs[HL]; cfi_p <= cf[HL]; end
            end
            if (H == 0) begin : g_seed
                wire [32:0] seed_d;
                ot_hdc_delay #(.W(33), .D(FPL)) u_sd (.clk(ck), .rst_n(1'b1),
                    .d({tf, (tm[14:0] == 15'd0) ? 32'd0 : {tm, 16'd0}}), .q(seed_d));
                always @(posedge ck) begin cs_o <= seed_d[31:0]; cf_o <= seed_d[32]; end
            end else begin : g_sum
                wire [1:0] err; wire vo_unused; wire [31:0] sum; wire pf;
                ot_hdc_v41x_faddl #(.LAT(FPL)) u_a (.clk(ck), .rst_n(rs), .valid_in(1'b1),
                    .a(csi_p), .b({tm, 16'd0}), .y(sum), .err(err), .valid_out(vo_unused));
                ot_hdc_delay #(.W(1), .D(FPL)) u_pf (.clk(ck), .rst_n(1'b1), .d(cfi_p || tf), .q(pf));
                always @(posedge ck) begin cs_o <= sum; cf_o <= pf || (err != 2'd0); end
            end
            assign cs[HL + 1] = cs_o; assign cf[HL + 1] = cf_o;
        end
    end endgenerate
    assign cs_out = cs[4]; assign cf_out = cf[4];
endmodule

`default_nettype wire
