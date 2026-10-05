`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ABI 3.0 inter-chip fabric: one 5-port mesh router.
//
// Dimension-ordered (X then Y) routing over single-flit packets.  Dimension
// order makes the channel-dependency graph acyclic, so this fabric needs no
// virtual channel to stay live and the endpoint's credit and retry behaviour
// can be observed without a wormhole confound.
//
// The crossbar itself is combinational: every cycle of a traversal is spent in
// the link channel (wire pipeline plus receive buffer), not in the router.
// That is deliberate -- it keeps `cycles per traversal` a property of the
// endpoint contract rather than of an arbitrary pipeline depth chosen here.
//
// Port order is fixed and shared with every block that talks to this one:
//   0 EAST (+x)   1 WEST (-x)   2 SOUTH (+y)   3 NORTH (-y)   4 LOCAL
// ---------------------------------------------------------------------------
module ot_a3_mesh_router #(
    parameter integer FLIT_W = 64,
    parameter integer MY_X   = 0,
    parameter integer MY_Y   = 0
) (
    input  wire                  clk,
    input  wire                  rst_n,

    input  wire [4:0]            in_valid,
    input  wire [5*FLIT_W-1:0]   in_flit,
    output reg  [4:0]            in_ready,

    output reg  [4:0]            out_valid,
    output reg  [5*FLIT_W-1:0]   out_flit,
    input  wire [4:0]            out_ready,

    output reg  [31:0]           flits_forwarded,
    output reg  [31:0]           flits_delivered_local,
    output reg                   misroute_error
);
    localparam integer P_EAST = 0;
    localparam integer P_WEST = 1;
    localparam integer P_SOUTH = 2;
    localparam integer P_NORTH = 3;
    localparam integer P_LOCAL = 4;

    localparam [3:0] MY_X4 = MY_X[3:0];
    localparam [3:0] MY_Y4 = MY_Y[3:0];

    reg [2:0] rr [0:4];          // rotating priority, one per output port
    reg [2:0] route_of [0:4];    // requested output port, one per input
    reg [4:0] req [0:4];         // req[out][in]
    reg [2:0] grant_of [0:4];    // granted input, one per output
    reg [4:0] granted;           // outputs with a grant
    reg [4:0] input_granted;     // inputs that won their requested output

    integer i;
    integer o;
    integer k;
    integer idx;
    reg found;
    reg [3:0] dx;
    reg [3:0] dy;
    reg [FLIT_W-1:0] f;

    always @* begin
        for (i = 0; i < 5; i = i + 1) begin
            f = in_flit[i*FLIT_W +: FLIT_W];
            dx = ot_a3_link_pkg::flit_dest_x(f);
            dy = ot_a3_link_pkg::flit_dest_y(f);
            if (dx > MY_X4)
                route_of[i] = P_EAST[2:0];
            else if (dx < MY_X4)
                route_of[i] = P_WEST[2:0];
            else if (dy > MY_Y4)
                route_of[i] = P_SOUTH[2:0];
            else if (dy < MY_Y4)
                route_of[i] = P_NORTH[2:0];
            else
                route_of[i] = P_LOCAL[2:0];
        end

        for (o = 0; o < 5; o = o + 1) begin
            req[o] = 5'b0;
            for (i = 0; i < 5; i = i + 1)
                if (in_valid[i] && (route_of[i] == o[2:0]))
                    req[o][i] = 1'b1;
        end

        granted = 5'b0;
        input_granted = 5'b0;
        for (o = 0; o < 5; o = o + 1) begin
            grant_of[o] = 3'd0;
            found = 1'b0;
            for (k = 0; k < 5; k = k + 1) begin
                idx = (rr[o] + k) % 5;
                if (!found && req[o][idx]) begin
                    found = 1'b1;
                    grant_of[o] = idx[2:0];
                end
            end
            granted[o] = found;
        end

        out_valid = 5'b0;
        out_flit = {(5*FLIT_W){1'b0}};
        for (o = 0; o < 5; o = o + 1) begin
            if (granted[o]) begin
                out_valid[o] = 1'b1;
                out_flit[o*FLIT_W +: FLIT_W] = in_flit[grant_of[o]*FLIT_W +: FLIT_W];
                if (out_ready[o])
                    input_granted[grant_of[o]] = 1'b1;
            end
        end
        in_ready = input_granted;
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (i = 0; i < 5; i = i + 1)
                rr[i] <= 3'd0;
            flits_forwarded <= 32'd0;
            flits_delivered_local <= 32'd0;
            misroute_error <= 1'b0;
        end else begin
            for (o = 0; o < 5; o = o + 1)
                if (granted[o] && out_ready[o])
                    rr[o] <= (grant_of[o] == 3'd4) ? 3'd0 : (grant_of[o] + 3'd1);
            for (i = 0; i < 5; i = i + 1)
                if (in_valid[i] && in_ready[i]) begin
                    if (route_of[i] == P_LOCAL[2:0])
                        flits_delivered_local <= flits_delivered_local + 32'd1;
                    else
                        flits_forwarded <= flits_forwarded + 32'd1;
                end
            // A flit that arrives on the local port and is routed straight back
            // out of the local port has no destination this router can serve.
            for (i = 0; i < 5; i = i + 1)
                if (in_valid[i] && (i == P_LOCAL) && (route_of[i] == P_LOCAL[2:0]))
                    misroute_error <= 1'b1;
        end
    end
endmodule
