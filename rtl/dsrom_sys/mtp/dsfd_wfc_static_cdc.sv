`timescale 1ns/1ps
`default_nettype none
// WFC-specific fixed-width CDC masters. Actual logic from 54a2299de dependency snapshot.
// These are separate hardware identities: no module aliases or width parameters.
// x34 uses the original direct-bank calendar (NAT=0); not a native timing claim.

module dsfd_wfc_ss_x43_t (
    input  wire         t_ck, t_rst_n,
    input  wire         s_v, input wire [527-1:0] s_d,
    output reg  [527:0]   b0, b2, b3,
    output reg  [2:0]   bpar,
    output reg          t_mark,
    output reg          ph1_bad
);
    // tp = index of the last stream edge (3 at reset: the next edge is epoch edge 0)
    reg [1:0] tp; reg te;                       // te = parity of the epoch whose edge 0 was the latest
    wire [1:0] tn = tp + 2'd1;                  // sample index of THIS edge
    always @(posedge t_ck or negedge t_rst_n)
        if (!t_rst_n) begin tp <= 2'd3; te <= 1'b0; bpar <= 3'b000; t_mark <= 1'b0; ph1_bad <= 1'b0; end
        else begin
            tp <= tn;
            t_mark <= tn == 2'd1;               // high from stream edge 1 to stream edge 2
            case (tn)
                2'd0: begin te <= ~te; bpar[0] <= ~te; end
                2'd2: bpar[1] <= te;
                2'd3: bpar[2] <= te;
                default: if (s_v) ph1_bad <= 1'b1;
            endcase
        end
    always @(posedge t_ck)
        case (tn)
            2'd0: b0 <= {s_v, s_d};
            2'd2: b2 <= {s_v, s_d};
            2'd3: b3 <= {s_v, s_d};
            default: ;
        endcase
endmodule

module dsfd_wfc_ss_x43_s (
    input  wire         s_ck, s_rst_n,
    input  wire [527:0]   b0, b2, b3,
    input  wire [2:0]   bpar,
    input  wire         t_mark,
    input  wire         ph1_bad,
    output reg          o_v, output reg [527-1:0] o_d,
    output reg          fault
);
    // sp = phase index of the last serial edge (2 at reset: the next edge is epoch edge 0)
    reg [1:0] sp; reg se; reg warm; reg mk;
    wire [1:0] sn = (sp == 2'd2) ? 2'd0 : sp + 2'd1;   // serial edge index of THIS edge
    always @(posedge s_ck or negedge s_rst_n)
        if (!s_rst_n) begin sp <= 2'd2; se <= 1'b0; warm <= 1'b0; o_v <= 1'b0; fault <= 1'b0; mk <= 1'b0; end
        else begin
            sp <= sn;
            mk <= t_mark;
            // PHASE ASSERTION: t_mark sampled at serial edge 1 (1.111 ns) is high; at edges 0 / 2 low.  mk holds the
            // previous edge's sample: after serial edge 1 (sn == 2 now) mk must be 1, else 0.
            if (warm && mk != (sn == 2'd2)) fault <= 1'b1;
            if (ph1_bad) fault <= 1'b1;
            case (sn)
`ifdef OT_VM_X43_MUT_PHASE
                2'd0: begin se <= ~se; o_v <= b3[527]; if (warm && bpar[2] != se) fault <= 1'b1; end
                2'd1: begin warm <= 1'b1; o_v <= b2[527]; end
`else
                2'd0: begin se <= ~se; o_v <= b2[527]; if (warm && bpar[1] != se) fault <= 1'b1; end
                2'd1: begin warm <= 1'b1; o_v <= b3[527]; if (warm && bpar[2] != ~se) fault <= 1'b1; end
`endif
                default: begin o_v <= b0[527]; if (warm && bpar[0] != se) fault <= 1'b1; end
            endcase
        end
    always @(posedge s_ck)
        case (sn)
`ifdef OT_VM_X43_MUT_PHASE
            2'd0: o_d <= b3[527-1:0];
            2'd1: o_d <= b2[527-1:0];
`else
            2'd0: o_d <= b2[527-1:0];
            2'd1: o_d <= b3[527-1:0];
`endif
            default: o_d <= b0[527-1:0];
        endcase
endmodule

module dsfd_wfc_ss_x34_s (
    input  wire         s_ck, s_rst_n,
    input  wire         s_v, input wire [514-1:0] s_d,
    output reg  [514:0]   b0, b1, b2,
    output reg  [2:0]   bpar,
    output reg          s_mark
);
    reg [1:0] sp; reg se;               // phase of the cycle that FOLLOWS the last edge; epoch parity
    always @(posedge s_ck or negedge s_rst_n)
        if (!s_rst_n) begin sp <= 2'd2; se <= 1'b0; bpar <= 3'b000; s_mark <= 1'b0; end   // first edge after release = epoch edge 0
        else begin
            s_mark <= sp == 2'd0;           // set by serial edge 1, cleared by serial edge 2
            // the edge that ends cycle sp writes bank (sp + 1) mod 3 (edge 0 of the epoch writes bank 0)
            case (sp)
                2'd2: begin bpar[0] <= ~se; end
                2'd0: begin bpar[1] <= se; end
                default: begin bpar[2] <= se; end
            endcase
            if (sp == 2'd2) begin sp <= 2'd0; se <= ~se; end else sp <= sp + 2'd1;
        end
    // data banks (no reset: the parity and v bit gate their use)
    generate if (1) begin : mux_wr
    always @(posedge s_ck) begin
        case (sp)
            2'd2: b0 <= {s_v, s_d};
`ifdef OT_VM_X34_MUT_SBANK
            2'd0: b2 <= {s_v, s_d};         // MUTANT: serial phase-1 word written into bank 2
`else
            2'd0: b1 <= {s_v, s_d};
`endif
            default: b2 <= {s_v, s_d};
        endcase
    end
    end endgenerate
endmodule

module dsfd_wfc_ss_x34_t (
    input  wire         t_ck, t_rst_n,
    input  wire [514:0]   b0, b1, b2,
    input  wire [2:0]   bpar,
    input  wire         s_mark,
    output reg          o_v, output reg [514-1:0] o_d,
    output reg          fault
);
    reg [1:0] tp; reg te; reg warm; reg mk;    // tp = index of the last stream edge (3 at reset: the next edge is epoch edge 0)
    always @(posedge t_ck or negedge t_rst_n)
        if (!t_rst_n) begin tp <= 2'd3; te <= 1'b0; warm <= 1'b0; o_v <= 1'b0; fault <= 1'b0; mk <= 1'b0; end
        else begin
            tp <= tp + 2'd1;
            // PHASE ASSERTION: the marker is sampled high by stream edge 2 only (0.557 ns after serial edge 1), low by
            // edges 0 / 1 / 3; mk holds the previous edge's sample, so after edge 2 (tp == 2) mk must be 1, else 0
            mk <= s_mark;
            if (warm && mk != (tp == 2'd2)) fault <= 1'b1;
            if (tp == 2'd3) begin te <= ~te; warm <= 1'b1; end
            case (tp)
`ifdef OT_VM_X34_MUT_PHASE
                2'd0: begin o_v <= b0[514]; if (warm && bpar[0] != te) fault <= 1'b1; end     // MUTANT: one stream edge early
`else
                2'd1: begin o_v <= b0[514]; if (warm && bpar[0] != te) fault <= 1'b1; end
`endif
                2'd2: begin o_v <= b1[514]; if (warm && bpar[1] != te) fault <= 1'b1; end
                2'd3: begin o_v <= b2[514]; if (warm && bpar[2] != te) fault <= 1'b1; end
                default: o_v <= 1'b0;
            endcase
        end
    always @(posedge t_ck)
        case (tp)
`ifdef OT_VM_X34_MUT_PHASE
            2'd0: o_d <= b0[514-1:0];
`else
            2'd1: o_d <= b0[514-1:0];
`endif
            2'd2: o_d <= b1[514-1:0];
            2'd3: o_d <= b2[514-1:0];
            default: ;
        endcase
endmodule

`default_nettype wire
