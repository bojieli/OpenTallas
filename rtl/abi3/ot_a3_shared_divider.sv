`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ABI 3.0 shared integer divider (docs/CHIP_ARCHITECTURE_DESIGN.md section 3.5).
//
// One restoring divider -- 64-bit numerator, 32-bit divisor, 64-bit quotient
// and remainder -- shared by the loop stack (requester 0: the two ceiling
// divisions of LOOP_SETUP) and the six view-resolver lanes (requesters 1..6:
// amendment A18's two divisions by ``extent_unit``).  It replaces the private
// divider each of those blocks carried.
//
// Throughput choice, not a contract.  Section 3.5 sizes a radix-4 pipelined
// divider (33 cycles, II 1); this block is radix-2 and sequential, 64
// iterations plus one cycle to latch and one to release, because no shipped
// view resolution enters it at all (a unit and numerator of one bypass it,
// which is every view written before A18) and LOOP_SETUP is its only shipped
// user.  Quotients are integer floors either way, so nothing observable
// depends on the choice.
//
// Arbitration is fixed priority: the loop stack first, then lane 0..5.  A
// requester holds ``req`` with its operands until it sees its ``done`` pulse,
// then drops it; the divider spends one cycle idle after every result so the
// released request is never re-latched.  ``clear`` aborts a division in
// flight without a done pulse, which is what lets a transaction that traps
// mid-resolution leave nothing behind for the next one to mistake for its own
// quotient.  A divisor of zero is never presented -- every caller substitutes
// one, exactly as the blocks did with their private dividers.
//
// The package is referenced by scope, never wildcard-imported [OI-43].
// ---------------------------------------------------------------------------
module ot_a3_shared_divider #(
    parameter integer REQUESTERS = 7
) (
    input  wire                     clk,
    input  wire                     rst_n,
    input  wire                     clear,

    input  wire [REQUESTERS-1:0]    req,
    input  wire [REQUESTERS*64-1:0] num,
    input  wire [REQUESTERS*32-1:0] den,

    output reg  [REQUESTERS-1:0]    grant,      // one-hot while serving
    output reg                      busy,
    output reg  [REQUESTERS-1:0]    done,       // one-cycle pulse, per requester
    output reg  [63:0]              quot,
    output reg  [63:0]              rem
);
    localparam [1:0] S_IDLE  = 2'd0;
    localparam [1:0] S_RUN   = 2'd1;
    localparam [1:0] S_REST  = 2'd2;
    localparam [1:0] S_PAUSE = 2'd3;

    reg [1:0]  state;
    reg [63:0] shift;
    reg [63:0] remainder;
    reg [63:0] quotient;
    reg [31:0] divisor;
    reg [6:0]  count;
    wire [63:0] trial = {remainder[62:0], shift[63]};

    // fixed-priority pick
    reg [REQUESTERS-1:0] pick;
    reg                  any_req;
    integer k;
    always @* begin
        pick = {REQUESTERS{1'b0}};
        any_req = 1'b0;
        for (k = REQUESTERS - 1; k >= 0; k = k - 1) begin
            if (req[k]) begin
                pick = {REQUESTERS{1'b0}};
                pick[k] = 1'b1;
                any_req = 1'b1;
            end
        end
    end

    reg [63:0] pick_num;
    reg [31:0] pick_den;
    always @* begin
        pick_num = 64'd0;
        pick_den = 32'd1;
        for (k = 0; k < REQUESTERS; k = k + 1) begin
            if (pick[k]) begin
                pick_num = num[k*64 +: 64];
                pick_den = den[k*32 +: 32];
            end
        end
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE;
            grant <= {REQUESTERS{1'b0}};
            busy <= 1'b0;
            done <= {REQUESTERS{1'b0}};
            quot <= 64'd0;
            rem <= 64'd0;
            shift <= 64'd0;
            remainder <= 64'd0;
            quotient <= 64'd0;
            divisor <= 32'd1;
            count <= 7'd0;
        end else begin
            done <= {REQUESTERS{1'b0}};
            if (clear) begin
                state <= S_IDLE;
                grant <= {REQUESTERS{1'b0}};
                busy <= 1'b0;
            end else begin
                case (state)
                    S_IDLE: begin
                        if (any_req) begin
                            grant <= pick;
                            busy <= 1'b1;
                            shift <= pick_num;
                            divisor <= (pick_den == 32'd0) ? 32'd1 : pick_den;
                            remainder <= 64'd0;
                            quotient <= 64'd0;
                            count <= 7'd64;
                            state <= S_RUN;
                        end
                    end
                    S_RUN: begin
                        if (trial >= {32'd0, divisor}) begin
                            remainder <= trial - {32'd0, divisor};
                            quotient <= {quotient[62:0], 1'b1};
                        end else begin
                            remainder <= trial;
                            quotient <= {quotient[62:0], 1'b0};
                        end
                        shift <= {shift[62:0], 1'b0};
                        count <= count - 7'd1;
                        if (count == 7'd1) begin
                            state <= S_REST;
                        end
                    end
                    S_REST: begin
                        // The result of the last iteration has settled into
                        // quotient/remainder; publish it to the granted
                        // requester and rest one cycle before re-arbitrating.
                        quot <= quotient;
                        rem <= remainder;
                        done <= grant;
                        grant <= {REQUESTERS{1'b0}};
                        busy <= 1'b0;
                        state <= S_PAUSE;
                    end
                    S_PAUSE: begin
                        // The requester sees its done pulse this cycle and
                        // drops req at the next edge; arbitrating now would
                        // re-latch the request it has just been answered.
                        state <= S_IDLE;
                    end
                    default: state <= S_IDLE;
                endcase
            end
        end
    end
endmodule
