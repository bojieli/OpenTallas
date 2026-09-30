`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_v41_chain2: ot_v41_chain on the LAT-stage ot_v41_fadd (W10, 1.2 GHz at SS): a slot may be presented again
// LAT cycles after its previous term.  Otherwise identical.
// ot_v41_chain: one lane's golden chunk chains.  Golden csum (tools/hdc_golden_v41.py) sums each
// chunk of 8 consecutive terms sequentially from +0; the element interleaves up to NCH chunks
// (chains) of different units through ONE pipelined binary32 adder (ot_fp32_add_rne_pipe,
// LATENCY 5).  A term names its chain `slot`; `first` starts the chain from +0 (the add 0 + t is
// performed, as the golden does), `last` makes the lane emit the chunk sum instead of storing it.
// A slot may be presented again 5 cycles after its previous term (the adder's latency): the sum leaving the
// adder in that cycle is forwarded straight back as the operand.  Sooner is a violation and raises `fault`;
// the issuer (ot_v41_rom_elem) never does it.  TW tag bits ride with the chain's last term.
// ---------------------------------------------------------------------------
module ot_v41_chain2 #(
    parameter integer NCH = 16,
    parameter integer TW = 8,
    parameter [8:0] CUT = 9'b1_0111_1011,
    parameter integer LAT = 1 + CUT[0] + CUT[1] + CUT[2] + CUT[3] + CUT[4] + CUT[5] + CUT[6] + CUT[7] + CUT[8]
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
    // input register: the chain slot's stored sum is read one cycle before the term meets the adder, so the
    // adder's operand is a 4-way choice (+0, the sum leaving the adder now, the one that left a cycle ago, the
    // stored sum) rather than a slot-wide read in front of the adder's first stage
    reg          v_r, first_r, last_r, termf_r, accf_r;
    reg [SW-1:0] slot_r;
    reg [31:0]   term_r, acc_r;
    reg [TW-1:0] tag_r;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) v_r <= 1'b0; else v_r <= v;
    always @(posedge clk) begin
        slot_r <= slot; first_r <= first; last_r <= last; term_r <= term; termf_r <= term_f; tag_r <= tag;
        acc_r <= acc[slot]; accf_r <= accf[slot];
    end
    reg [LAT-1:0] pv;
    reg [SW-1:0] ps [0:LAT-1];
    integer k;
    reg hazard;
    always @* begin
        hazard = 1'b0;
        for (k = 0; k < LAT - 1; k = k + 1) if (pv[k] && ps[k] == slot_r) hazard = 1'b1;
    end
    wire [31:0] sum;
    wire [1:0] err;
    wire sv;
    wire [31:0] a;
    wire af;
    ot_v41_fadd #(.CUT(CUT)) u_add (.clk(clk), .rst_n(rst_n), .valid_in(v_r), .a(a), .b(term_r), .y(sum),
                                     .err(err), .valid_out(sv));
    wire [TW+2:0] dt;
    ot_hdc_delay #(.W(TW + 3), .D(LAT)) u_t (.clk(clk), .rst_n(rst_n), .d({tag_r, last_r, af | termf_r, 1'b0}), .q(dt));
    wire d_last = dt[2];
    wire d_f = dt[1] | (err != 2'd0);
    // the slot's previous sum: leaving the adder now (5 cycles ago), or one cycle ago (not yet in acc_r)
    reg          sp_v, sp_f;
    reg [SW-1:0] sp_slot;
    reg [31:0]   sp_val;
    // forwarding decisions are made a cycle ahead against the incoming slot and registered (the compare no
    // longer sits in front of the adder): fwd5 = the slot's sum leaves the adder in the operand cycle,
    // fwd6 = it left one cycle before
    reg [LAT-1:0] pl;
    reg fwd5, fwd6;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin fwd5 <= 1'b0; fwd6 <= 1'b0; end
        else begin
            fwd5 <= pv[LAT-2] && !pl[LAT-2] && ps[LAT-2] == slot;
            fwd6 <= sv && !d_last && ps[LAT-1] == slot;
        end
    always @(posedge clk) pl <= {pl[LAT-2:0], last_r};
    assign a = first_r ? 32'd0 : (fwd5 ? sum : (fwd6 ? sp_val : acc_r));
    assign af = first_r ? 1'b0 : (fwd5 ? d_f : (fwd6 ? sp_f : accf_r));
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            pv <= '0; fault <= 1'b0; accf <= '0; sp_v <= 1'b0;
        end else begin
            pv <= {pv[LAT-2:0], v_r};
            if (v_r && hazard) fault <= 1'b1;
            if (sv && !d_last) accf[ps[LAT-1]] <= d_f;
            sp_v <= sv && !d_last;
        end
    end
    always @(posedge clk) begin
        ps[0] <= slot_r;
        for (k = 1; k < LAT; k = k + 1) ps[k] <= ps[k-1];
        if (sv && !d_last) acc[ps[LAT-1]] <= sum;
        sp_slot <= ps[LAT-1]; sp_val <= sum; sp_f <= d_f;
    end
    assign ov = sv && d_last;
    assign osum = sum;
    assign of = d_f;
    assign otag = dt[TW+2:3];
endmodule
