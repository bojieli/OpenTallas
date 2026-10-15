`timescale 1ns/1ps
`default_nettype none
// ot_s81_static_ratio_cross -- related-ratio clock crossing on a FIXED calendar (S-NET, 2026-10-15).
//
// Static successor of ot_ratio_cdc_fifo on the S81 die seams (l2r lane -> serial VM, r2l serial -> lane) under the owner
// rule 2026-10-14 18:59: no ready / credit / DOWN-WAIT-RUN handshake, no traffic-dependent latency.  The two clocks come
// from one PLL (VCO 3.6 GHz: /3 stream 1.2 GHz, /4 serial 0.9 GHz): a hyperperiod of 12 VCO ticks holds NS source and ND
// destination edges (NS:ND = 4:3 stream -> serial, 3:4 serial -> stream).
//
// Epochs (as ot_s81_static_lane_cross): source edge 0 is the first w_ck edge with w_rst_n high (the lane's forwarded
// reset marker); the destination epoch follows the marker through two r_ck flops (r_rst_n is the local root reset and
// must release first).  Every source edge writes slot wc mod DEPTH (bubbles included) with its identity wc.
// Destination edge rc (hyperperiod h = rc / ND, phase p = rc mod ND) reads the FIXED source edge
//     src(rc) = NS*h + p - LAG    when p < NS   (ND > NS: phase p >= NS is a compiled bubble, o = 0)
// so for NS > ND the source phases ND..NS-1 of every hyperperiod are never read: the compiler must leave them empty
// (a valid bit there is a schedule fault).  The latency is therefore a pure function of the two edge counters; the
// physical margin (written >= 1 VCO tick before the read, not rewritten for DEPTH source edges) holds for every
// divider phase because the marker synchroniser already places the destination epoch 7..12 ticks after the source's:
// read - write = 6..9 + p ticks (4:3, LAG 0: >= 6 ticks) / 3..5 - p + 4*LAG (3:4, LAG 1: >= 3 ticks = one stream
// period for the DEPTH:1 read mux), inside DEPTH*T_src.  STA: the bank -> o arcs carry a set_max_delay of that window.
// Checks (assertion only, sticky fault, never re-times): identity of the read slot == src(rc) (early read sees the
// previous lap, late read the next), and no valid word (bit VBIT of the source word) in a never-read source phase.
module ot_s81_static_ratio_cross #(
    parameter integer W = 64,
    parameter integer NS = 4,             // source edges per 12-tick hyperperiod
    parameter integer ND = 3,             // destination edges per hyperperiod
    parameter integer DEPTH = 8,          // power of two, >= 2*NS
    parameter integer LAG = (NS < ND) ? 1 : 0,   // source edges of extra lag (3:4: >= 3 VCO ticks for the read mux)
    parameter integer VBIT = 0,           // valid bit of the source word (for the skipped-phase check); -1: none
    parameter integer MUT = 0             // bench mutants only: 1 mapping off by one source edge
) (
    input  wire         w_ck,
    input  wire         w_rst_n,          // source epoch marker (synchronous to w_ck)
    input  wire [W-1:0] i,
    input  wire         r_ck,
    input  wire         r_rst_n,          // destination root reset (releases before the marker)
    output reg  [W-1:0] o,
    output reg          o_live,           // destination epoch running
    output reg          fault
);
    localparam integer AW = $clog2(DEPTH);
    localparam integer CW = 24;
    reg [W-1:0]  bank [0:DEPTH-1];
    reg [AW+1:0] ident [0:DEPTH-1];
    reg [CW-1:0] wc;
    reg [$clog2(NS+1)-1:0] wp;            // source phase in hyperperiod
    reg wskip_v;                          // a valid word in a never-read source phase (source side, synchronised)
    always @(posedge w_ck or negedge w_rst_n)
        if (!w_rst_n) begin wc <= 0; wp <= 0; wskip_v <= 1'b0; end
        else begin
            bank[wc[AW-1:0]] <= i;
            ident[wc[AW-1:0]] <= wc[AW+1:0];
            wc <= wc + 1'b1;
            wp <= (wp == NS - 1) ? 0 : wp + 1'b1;
            if (NS > ND && wp >= ND && VBIT >= 0 && i[VBIT >= 0 ? VBIT : 0]) wskip_v <= 1'b1;
        end
    (* async_reg = "true" *) reg [1:0] ep;
    always @(posedge r_ck or negedge r_rst_n)
        if (!r_rst_n) ep <= 2'b00; else ep <= {ep[0], w_rst_n};
    (* async_reg = "true" *) reg [2:0] sk;
    always @(posedge r_ck) sk <= {sk[1:0], wskip_v};
    wire run = ep[1];
    reg [CW-1:0] h;                       // destination hyperperiod
    reg [$clog2(ND+1)-1:0] p;             // destination phase
    wire [CW-1:0] raw = h * NS + p;
    wire          has = ((ND <= NS) || (p < NS)) && raw >= LAG;
    wire [CW-1:0] src = raw - LAG + ((MUT == 1) ? 1 : 0);
    always @(posedge r_ck or negedge run)
        if (!run) begin h <= 0; p <= 0; o <= 0; o_live <= 1'b0; fault <= 1'b0; end
        else begin
            o_live <= 1'b1;
            if (p == ND - 1) begin p <= 0; h <= h + 1'b1; end else p <= p + 1'b1;
            if (has) begin
                o <= bank[src[AW-1:0]];
                if (ident[src[AW-1:0]] != src[AW+1:0]) fault <= 1'b1;
            end else o <= {W{1'b0}};
            if (sk[2]) fault <= 1'b1;
        end
`ifndef SYNTHESIS
    initial if (NS < 1 || ND < 1 || DEPTH < 2 * NS || (DEPTH & (DEPTH - 1)) != 0)
        $fatal(1, "ot_s81_static_ratio_cross: DEPTH a power of two >= 2*NS");
`endif
endmodule
`default_nettype wire
