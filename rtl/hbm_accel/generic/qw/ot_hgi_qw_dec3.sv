`timescale 1ns/1ps
`default_nettype none
// ot_hgi_quant_wide_h decode, track B (el1011-hbm-fq 2026-10-12): ot_hgi_qw_dec split into three hardened tiles, each
// <= 15k clock sinks on its own root, registered on every seam, cycle for cycle and bit for bit the same as ot_hgi_qw_dec
// (same ports, same latency: tb_hgi_qw_dec3_equiv).  The one-tile decoder carried 35,679 flops on one root; 26k of them
// are the two element delay lines (actquant 13 x 1088, fp4qdq 5 x 1024 shared) and the fp4qdq result alignment
// (14 x 512).  Split:
//   X  ot_hgi_qw_dxl : the shared element line (14 x 1024 flops, no logic): x -> r1 .. r14; taps r1 (both s0
//                      registers), r8 (fp4qdq S4 copy) and r14 (actquant E copy).
//   B  ot_hgi_qw_dbq : the E4M3/FP4 path (ot_hgi_fp4qdq PIPE=1: one 31-bit max per stage, +2 edges) + 11 of the 12
//                      result-alignment registers.
//   A  ot_hgi_qw_daq : the actquant path (ot_hfd_actquant_m XEXT=1), the last alignment register (B's capture), the
//                      result select and the output registers; decode_fault.
// Edges (E1 = the one-tile decoder's input registers): X r_k at E_k; A/B s0_x = capture of r1 at E2 (as before);
// B captures r8 at E9 = s0 + 7 (PIPE=1 S4 alignment); A captures r14 at E15 = s0 + 13 (7 + MLAT); fp4qdq results go
// through 11 B registers + 1 A capture = the 12 alignment edges left after PIPE's +2 (was 14).
module ot_hgi_qw_dxl (
    input  wire          clk,
    input  wire [1023:0] x,
    output wire [1023:0] xs,     // r1 -> A and B s0_x
    output wire [1023:0] xb,     // r8 -> B x4 capture
    output wire [1023:0] xa      // r14 -> A xe capture
);
    reg [1023:0] r [1:14];
    integer k;
    always @(posedge clk) begin
        r[1] <= x;
        for (k = 2; k <= 14; k = k + 1) r[k] <= r[k-1];
    end
    assign xs = r[1]; assign xb = r[8]; assign xa = r[14];
endmodule

// header fields used by the decode: {header[127:118] (unit, op), header[71:64] (block)}
module ot_hgi_qw_dbq (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          v,
    input  wire [17:0]   hd,
    input  wire [1023:0] xs,
    input  wire [1023:0] xb,
    output wire          bvo,
    output wire          bfo,
    output wire [511:0]  byo
);
    wire [0:0] rr_n;
    ot_rst_relay #(.REGIONS(1)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rr_n));
    reg i_v; reg [17:0] i_h; reg [1023:0] xc;
    always @(posedge clk or negedge rr_n[0]) if (!rr_n[0]) i_v <= 0; else i_v <= v;
    always @(posedge clk) begin i_h <= hd; xc <= xb; end
    wire [3:0] unit_code = i_h[17:14];
    wire [5:0] op = i_h[13:8];
    wire legal = (unit_code == 4) && (op == 4 || op == 5 || (op == 6 && i_h[7:0] == 16));
    wire take = i_v && legal;
    wire bv, bf; wire [511:0] by;
    ot_hgi_fp4qdq #(.PIPE(1), .XEXT(1)) bq (.clk(clk), .rst_n(rr_n[0]), .v(take && op == 6), .x(xs), .vo(bv), .y(by),
        .fault(bf), .packed_word(), .x4_ext(xc));
    // NB-cycle latency match (byo = by delayed NB edges).  Data is a ring of ND = NB-1 enabled 512-bit entries plus
    // one output register, NOT an NB-deep shift register: the shift register was 5,120 back-to-back flop->flop pairs
    // with no logic between them, so CTS/GRT hold repair flooded (b2: ~27k hold buffers, DPL-0033 at 4_1_cts).
    // Every ring path is flop -> enable mux / one-hot read AO-tree -> flop.  Read-before-overwrite at the write slot:
    // o(edge t) = mem[wp] = by(edge t-ND), so byo(edge t) = by(edge t-NB), identical to the shift register.
    // The one-hot pointer is replicated per 64-bit lane group (8 x ND flops) so no select net fans out to 512 bits.
    localparam integer NB = 11;
    localparam integer ND = NB - 1;
    localparam integer NG = 8, GW = 512 / NG;
    reg [NB-1:0] vp, fp;
    always @(posedge clk or negedge rr_n[0])
        if (!rr_n[0]) begin vp <= 0; fp <= 0; end
        else begin vp <= {vp[NB-2:0], bv}; fp <= {fp[NB-2:0], bf}; end
    genvar g;
    generate for (g = 0; g < NG; g = g + 1) begin : g_ring
        reg [ND-1:0] wp;
        reg [GW-1:0] mem [0:ND-1];
        reg [GW-1:0] rd, o;
        integer k;
        always @(posedge clk or negedge rr_n[0])
            if (!rr_n[0]) wp <= {{(ND-1){1'b0}}, 1'b1};
            else wp <= {wp[ND-2:0], wp[ND-1]};
        always @(*) begin
            rd = {GW{1'b0}};
            for (k = 0; k < ND; k = k + 1) rd = rd | ({GW{wp[k]}} & mem[k]);
        end
        always @(posedge clk) begin
            for (k = 0; k < ND; k = k + 1) if (wp[k]) mem[k] <= by[g*GW +: GW];
            o <= rd;
        end
        assign byo[g*GW +: GW] = o;
    end endgenerate
    assign bvo = vp[NB-1]; assign bfo = fp[NB-1];
endmodule

module ot_hgi_qw_daq #(parameter integer MUTANT = 0) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          v,
    input  wire [17:0]   hd,
    input  wire [1023:0] xs,
    input  wire [1023:0] xa,
    input  wire          bvo,
    input  wire          bfo,
    input  wire [511:0]  byo,
    output reg           vo,
    output reg  [511:0]  y,
    output reg           fault,
    output reg           decode_fault
);
    wire [1:0] rr_n;
    ot_rst_relay #(.REGIONS(2)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rr_n));
    reg i_v; reg [17:0] i_h; reg [1023:0] xc;
    always @(posedge clk or negedge rr_n[0]) if (!rr_n[0]) i_v <= 0; else i_v <= v;
    always @(posedge clk) begin i_h <= hd; xc <= xa; end
    wire [3:0] unit_code = i_h[17:14];
    wire [5:0] op = i_h[13:8];
    wire e4 = op == 6;
    wire legal = (unit_code == 4) && (op == 4 || op == 5 || (op == 6 && i_h[7:0] == 16));
    wire take = i_v && legal;
    wire fp4 = (op == 5) ^ (MUTANT == 1);
    reg df;
    always @(posedge clk or negedge rr_n[1]) if (!rr_n[1]) df <= 0; else df <= i_v && !legal;
    wire av, af; wire [511:0] ay; wire [255:0] q; wire signed [9:0] exponent;
    ot_hfd_actquant_m #(.MR(1), .MLAT(6), .XEXT(1)) aq (.clk(clk), .rst_n(rr_n[1]), .v(take && !e4), .fp4(fp4), .x(xs),
        .vo(av), .q(q), .e(exponent), .y(ay), .fault(af), .xe_ext(xc));
    // B's result capture = the last alignment register
    reg cv, cf; reg [511:0] cy;
    always @(posedge clk or negedge rr_n[1]) if (!rr_n[1]) begin cv <= 0; cf <= 0; end else begin cv <= bvo; cf <= bfo; end
    always @(posedge clk) cy <= byo;
    wire d_vo = av | cv;
    always @(posedge clk or negedge rr_n[0])
        if (!rr_n[0]) begin vo <= 0; fault <= 0; decode_fault <= 0; end
        else begin vo <= d_vo; fault <= d_vo && (cv ? cf : af); decode_fault <= df; end
    always @(posedge clk) y <= cv ? cy : ay;
endmodule

// same ports and timing as ot_hgi_qw_dec; pure wiring around the three tiles
module ot_hgi_qw_dec3 #(parameter integer MUTANT = 0) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          v,
    input  wire [127:0]  header,
    input  wire [1023:0] x,
    output wire          vo,
    output wire [511:0]  y,
    output wire          fault,
    output wire          decode_fault
);
    wire [17:0] hd = {header[127:118], header[71:64]};
    wire [1023:0] xs, xb, xa; wire bvo, bfo; wire [511:0] byo;
    ot_hgi_qw_dxl u_dxl (.clk(clk), .x(x), .xs(xs), .xb(xb), .xa(xa));
    ot_hgi_qw_dbq u_dbq (.clk(clk), .rst_n(rst_n), .v(v), .hd(hd), .xs(xs), .xb(xb), .bvo(bvo), .bfo(bfo), .byo(byo));
`ifdef OT_HARD_CHILDREN
    ot_hgi_qw_daq u_daq (
`else
    ot_hgi_qw_daq #(.MUTANT(MUTANT)) u_daq (
`endif
        .clk(clk), .rst_n(rst_n), .v(v), .hd(hd), .xs(xs), .xa(xa), .bvo(bvo), .bfo(bfo),
        .byo(byo), .vo(vo), .y(y), .fault(fault), .decode_fault(decode_fault));
endmodule
`default_nettype wire
