`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// ot_s81_hc_caq (s81-suhc-hier-1011 comb v2, 2026-10-11): one FP8 act-quant unit of the HC combine region, a hard
// tile hardened once and stepped x S_RT (ot_s81_hc_comb is a wires-only wrapper of the comb tiles).  Every input is
// captured at the pin (run / kind / row valid / h-row tag / the row's 512 b / its {vector, row} index straight from
// the ot_s81_hc_crx return flops); the aq12 output registers and the index line's last stage are the output flops.
// Own clock root sk, tile-local 2-flop reset relay.  Latency vs the flat comb: +1 in (the writer adds +1 more at its
// capture); the writer's done is count-based, so the codes / exps rows only move later in time.
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81_hc_caq (
    input  wire          sk, srs,
    input  wire          run,
    input  wire [2:0]    kind,
    input  wire          rv_u,         // the returned row's valid
    input  wire          t_u,          // the row is an h-store row (not a y row)
    input  wire [511:0]  x,            // the row (32 BF16)
    input  wire [23:0]   iq,           // {vector, row} of the block
    output wire          vo,
    output wire [255:0]  q,
    output wire [9:0]    e,
    output wire          f,
    output wire [23:0]   iqo
);
    localparam [2:0] K_NORM = 4;
    reg [1:0] rsr;
    always @(posedge sk) rsr <= {rsr[0], srs};
    wire rs_n = rsr[1];
    reg          run_q, rv_q, t_q;
    reg [2:0]    kind_q;
    reg [511:0]  x_q;
    reg [23:0]   iq_q;
    always @(posedge sk or negedge rs_n)
        if (!rs_n) begin run_q <= 1'b0; rv_q <= 1'b0; end
        else begin run_q <= run; rv_q <= rv_u; end
    always @(posedge sk) begin t_q <= t_u; kind_q <= kind; x_q <= x; iq_q <= iq; end
    reg [1023:0] xx;
    integer e_;
    always @(*) for (e_ = 0; e_ < 32; e_ = e_ + 1) xx[32 * e_ +: 32] = {x_q[16 * e_ +: 16], 16'h0000};
    wire [511:0] unused_y;
    wire signed [9:0] ee;
    ot_dsrom_aq12 u_aq (.clk(sk), .rst_n(rs_n), .v(rv_q && !t_q && run_q && kind_q == K_NORM), .x(xx),
                        .vo(vo), .q(q), .e(ee), .y(unused_y), .fault(f));
    assign e = ee;
    ot_hdc_delay #(.W(24), .D(18)) u_iq (.clk(sk), .rst_n(rs_n), .d(iq_q), .q(iqo));
endmodule
