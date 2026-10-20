`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// QW-CB16A0-2 (10-20) A0 rc10 / REGROOT 9: LANDED crossing between two regional clock roots of the A0 ROM-leaf parent.
// Same contract as ot_pl_land_w / ot_pl_land_r (lanes/LANDING-CONTRACT.md L1-L7, PARENTS-LANDED 10-18) and the same
// census-safe physical form as ot_pl_land_phys_chunk_w/_r (main rtl/common/landed_parent/ot_pl_land_physical.sv):
//   ot_qw_lw  RING on the SOURCE root: every edge writes slot wc mod D (one-hot write pointer, KEPT per 24-bit chunk).
//   ot_qw_lr  READ on the DESTINATION root: every edge after warm-up reads slot (rc - K) mod D into o (flop-last).
// Static schedule: both pointers free-run from the same reset epoch (no ready, no credit, no occupancy, no training).
// LATENCY: o after edge n = i sampled at edge n - K; a plain destination register would hold i sampled at edge n, so the
//   landing adds exactly K edges (priced by the instantiating module: XTD / RX).
// SDC: set_multicycle_path -setup K -hold (D - 1) from the ring (u_qlw*) to the read (u_qlr*) cells (kit sdc_extra).
// RESET: rsi is sampled by one KEPT instance relay on the module's own root, then by one rq per chunk (equal depth on
//   both sides => write epoch == read epoch).  Native census: relay -> <= 32 chunk rq; rq -> 2*D; write_oh[s] -> <= 24
//   slot enables + 1 valid; read_oh[s] -> <= 24 AND + 1; each slot bit -> one AND per reader.
// ---------------------------------------------------------------------------------------------------------------------
module ot_qw_lw #(
    parameter integer W  = 128,
    parameter integer D  = 4,
    parameter integer CB = 24,
    parameter integer C  = (W + CB - 1) / CB
) (
    input  wire           ck,
    input  wire           rsi,
    input  wire [W-1:0]   i,
    output wire [D*W-1:0] bank,
    output wire [D*C-1:0] vld
);
    (* keep *) reg rr;
    always @(posedge ck) rr <= rsi;
    genvar c, s;
    generate for (c = 0; c < C; c = c + 1) begin : g_c
        localparam integer CW = (W - c*CB < CB) ? W - c*CB : CB;
        (* keep *) reg rq;
        (* keep *) reg [D-1:0] woh;
        reg [D-1:0] v;
        always @(posedge ck) rq <= rr;
        always @(posedge ck)
            if (!rq) begin woh <= {{(D-1){1'b0}}, 1'b1}; v <= {D{1'b0}}; end
            else     begin woh <= {woh[D-2:0], woh[D-1]}; v <= v | woh; end
        for (s = 0; s < D; s = s + 1) begin : g_s
            reg [CW-1:0] dq;                                   // one slot (no memory array: plain kept-name flops)
            always @(posedge ck) if (rq && woh[s]) dq <= i[c*CB +: CW];
            assign bank[s*W + c*CB +: CW] = dq;
        end
        assign vld[c*D +: D] = v;
    end endgenerate
`ifndef SYNTHESIS
    initial if (D < 2 || (D & (D - 1)) != 0 || C > 32) $fatal(1, "ot_qw_lw: D power of two >= 2, <= 32 chunks");
`endif
endmodule

module ot_qw_lr #(
    parameter integer W  = 128,
    parameter integer D  = 4,
    parameter integer K  = 2,
    parameter integer CB = 24,
    parameter integer C  = (W + CB - 1) / CB,
    parameter integer AW = (D <= 2) ? 1 : $clog2(D)
) (
    input  wire           ck,
    input  wire           rsi,
    input  wire [D*W-1:0] bank,
    input  wire [D*C-1:0] vld,
    output wire [W-1:0]   o
);
    (* keep *) reg rr;
    always @(posedge ck) rr <= rsi;
    genvar c;
    generate for (c = 0; c < C; c = c + 1) begin : g_c
        localparam integer CW = (W - c*CB < CB) ? W - c*CB : CB;
        (* keep *) reg rq;
        reg warm;
        reg [AW:0] rc;
        (* keep *) reg [D-1:0] roh;
        reg [CW-1:0] sel;
        reg sv;
        reg [CW-1:0] q;
        integer j;
        always @* begin
            sel = {CW{1'b0}}; sv = 1'b0;
            for (j = 0; j < D; j = j + 1) begin
                sel = sel | (bank[j*W + c*CB +: CW] & {CW{roh[j]}});
                sv  = sv  | (vld[c*D + j] & roh[j]);
            end
        end
        always @(posedge ck) rq <= rr;
        always @(posedge ck)
            if (!rq) begin rc <= {(AW+1){1'b0}}; warm <= 1'b0; for (j = 0; j < D; j = j + 1) roh[j] <= (j == ((D - K) % D)); end
            else begin rc <= rc + 1'b1; if (rc == K - 1) warm <= 1'b1; roh <= {roh[D-2:0], roh[D-1]}; end
        always @(posedge ck) q <= (warm && sv) ? sel : {CW{1'b0}};
        assign o[c*CB +: CW] = q;
    end endgenerate
`ifndef SYNTHESIS
    initial if (K < 1 || K > D - 1 || C > 32) $fatal(1, "ot_qw_lr: 1 <= K <= D-1, <= 32 chunks");
`endif
endmodule

// Fixed delay of D edges (q after edge n = d sampled at edge n - D + 1, identical to ot_hdc_delay) as a RING of D - 1
// slots + the output register: no flop -> flop shift chain (safe-design item 5).  At each edge the slot under the
// pointer is read into q and rewritten with d.  The pointer is a KEPT one-hot per 16-bit chunk (16 enables + 16 ANDs).
module ot_qw_ring_delay #(
    parameter integer W  = 128,
    parameter integer D  = 3,
    parameter integer CB = 16,
    parameter integer C  = (W + CB - 1) / CB
) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    localparam integer S = D - 1;
    genvar c, s;
    generate if (D < 3) begin : g_short
        ot_hdc_delay #(.W(W), .D(D)) u_d (.clk(clk), .rst_n(rst_n), .d(d), .q(q));
    end else begin : g_ring
        (* keep *) reg rr;
        always @(posedge clk) rr <= rst_n;
        for (c = 0; c < C; c = c + 1) begin : g_c
            localparam integer CW = (W - c*CB < CB) ? W - c*CB : CB;
            (* keep *) reg rq;
            (* keep *) reg [S-1:0] p;
            wire [CW*S-1:0] slot;
            reg [CW-1:0] sel;
            reg [CW-1:0] qq;
            integer j;
            always @* begin
                sel = {CW{1'b0}};
                for (j = 0; j < S; j = j + 1) sel = sel | (slot[j*CW +: CW] & {CW{p[j]}});
            end
            always @(posedge clk) rq <= rr;
            always @(posedge clk)
                if (!rq) p <= {{(S-1){1'b0}}, 1'b1};
                else     p <= (S == 1) ? p : {p[S-2:0], p[S-1]};
            for (s = 0; s < S; s = s + 1) begin : g_s
                reg [CW-1:0] sq;
                always @(posedge clk) if (p[s] || !rq) sq <= d[c*CB +: CW];   // reset fills every slot
                assign slot[s*CW +: CW] = sq;
            end
            always @(posedge clk) qq <= sel;
            assign q[c*CB +: CW] = qq;
        end
    end endgenerate
endmodule
