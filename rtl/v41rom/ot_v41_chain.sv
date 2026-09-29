`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_v41_chain: one lane's golden chunk chains.  Golden csum (tools/hdc_golden_v41.py) sums each
// chunk of 8 consecutive terms sequentially from +0; the element interleaves up to NCH chunks
// (chains) of different units through ONE pipelined binary32 adder (ot_fp32_add_rne_pipe,
// LATENCY 5).  A term names its chain `slot`; `first` starts the chain from +0 (the add 0 + t is
// performed, as the golden does), `last` makes the lane emit the chunk sum instead of storing it.
// A slot may be presented again 5 cycles after its previous term (the adder's latency): the sum leaving the
// adder in that cycle is forwarded straight back as the operand.  Sooner is a violation and raises `fault`;
// the issuer (ot_v41_rom_elem) never does it.  TW tag bits ride with the chain's last term.
// ---------------------------------------------------------------------------
module ot_v41_chain #(
    parameter integer NCH = 16,
    parameter integer TW = 8
) (
    input  wire                     clk,
    input  wire                     rst_n,
    input  wire                     v,
    input  wire [$clog2(NCH)-1:0]   slot,
    input  wire                     first,
    input  wire                     last,
    input  wire [31:0]              term,
    input  wire                     term_f,
    input  wire [TW-1:0]            tag,
    output wire                     ov,
    output wire [31:0]              osum,
    output wire                     of,
    output wire [TW-1:0]            otag,
    output reg                      fault
);
    localparam integer SW = $clog2(NCH);
    reg [31:0] acc [0:NCH-1];
    reg [NCH-1:0] accf;
    reg [4:0] pv;
    reg [SW-1:0] ps [0:4];
    integer k;
    reg hazard;
    always @* begin
        hazard = 1'b0;
        for (k = 0; k < 4; k = k + 1) if (pv[k] && ps[k] == slot) hazard = 1'b1;
    end
    wire [31:0] sum;
    wire [1:0] err;
    wire sv;
    wire [31:0] a;
    wire af;
    ot_fp32_add_rne_pipe u_add (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(term), .y(sum),
                                .err(err), .valid_out(sv));
    wire [TW+2:0] dt;
    ot_hdc_delay #(.W(TW + 3), .D(5)) u_t (.clk(clk), .rst_n(rst_n), .d({tag, last, af | term_f, 1'b0}), .q(dt));
    wire d_last = dt[2];
    wire d_f = dt[1] | (err != 2'd0);
    wire fwd = sv && !d_last && ps[4] == slot;       // the slot's previous sum is leaving the adder now
    assign a = first ? 32'd0 : (fwd ? sum : acc[slot]);
    assign af = first ? 1'b0 : (fwd ? d_f : accf[slot]);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            pv <= 5'd0; fault <= 1'b0; accf <= '0;
        end else begin
            pv <= {pv[3:0], v};
            if (v && hazard) fault <= 1'b1;
            if (sv && !d_last) accf[ps[4]] <= d_f;
        end
    end
    always @(posedge clk) begin
        ps[0] <= slot;
        for (k = 1; k < 5; k = k + 1) ps[k] <= ps[k-1];
        if (sv && !d_last) acc[ps[4]] <= sum;
    end
    assign ov = sv && d_last;
    assign osum = sum;
    assign of = d_f;
    assign otag = dt[TW+2:3];
endmodule
