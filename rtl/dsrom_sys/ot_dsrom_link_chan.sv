`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_dsrom_link_chan: the PHY + FEC + flight stand-in.  A fixed-latency delay
// line (MAXD registers; with DYN=1 the tap min(delay, MAXD) is selected, delay
// held constant during a run) plus deterministic error injection: with
// ERR_PERIOD = N > 0, one bit of every Nth valid frame entering the channel is
// flipped (first at frame N - ERR_OFFSET mod N), the bit position advancing by
// ERR_STRIDE mod W per injected error so every field (sequence, last, data,
// CRC) is hit over a run.  Not a synthesis target.
// ---------------------------------------------------------------------------
module ot_dsrom_link_chan #(
    parameter integer W          = 64,
    parameter integer MAXD       = 8,
    parameter integer DYN        = 0,
    parameter integer ERR_PERIOD = 0,
    parameter integer ERR_OFFSET = 0,
    parameter integer ERR_STRIDE = 37
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [15:0]   delay,
    input  wire          in_valid,
    input  wire [W-1:0]  in_data,
    output wire          out_valid,
    output wire [W-1:0]  out_data,
    output reg  [31:0]   err_injected
);
    localparam integer P = (ERR_PERIOD > 0) ? ERR_PERIOD : 1;
    reg  [31:0] phase, bitpos;
    wire        hit  = (ERR_PERIOD > 0) && in_valid && (phase == P - 1);
    wire [W-1:0] flip = hit ? ({{(W-1){1'b0}}, 1'b1} << bitpos) : {W{1'b0}};
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            phase <= ERR_OFFSET % P; bitpos <= 0; err_injected <= 0;
        end else if (in_valid) begin
            phase <= (phase == P - 1) ? 0 : phase + 1;
            if (hit) begin
                bitpos <= (bitpos + ERR_STRIDE >= W) ? bitpos + ERR_STRIDE - W : bitpos + ERR_STRIDE;
                err_injected <= err_injected + 1;
            end
        end
    end

    reg          lv [0:MAXD-1];
    reg  [W-1:0] ld [0:MAXD-1];
    genvar k;
    generate for (k = 0; k < MAXD; k = k + 1) begin : g_line
        if (k == 0) begin : g_first
            always @(posedge clk or negedge rst_n)
                if (!rst_n) lv[k] <= 1'b0;
                else begin lv[k] <= in_valid; ld[k] <= in_data ^ flip; end
        end else begin : g_rest
            always @(posedge clk or negedge rst_n)
                if (!rst_n) lv[k] <= 1'b0;
                else begin lv[k] <= lv[k-1]; ld[k] <= ld[k-1]; end
        end
    end endgenerate

    generate if (DYN != 0) begin : g_dyn
        localparam [31:0] MAXD32 = MAXD;
        wire [15:0] dsel = (delay > MAXD32[15:0]) ? MAXD32[15:0] : delay;
        assign out_valid = (dsel == 0) ? in_valid : lv[dsel - 1];
        assign out_data  = (dsel == 0) ? (in_data ^ flip) : ld[dsel - 1];
    end else begin : g_static
        assign out_valid = lv[MAXD-1];
        assign out_data  = ld[MAXD-1];
        wire unused_delay = &{1'b0, delay};
    end endgenerate
endmodule
