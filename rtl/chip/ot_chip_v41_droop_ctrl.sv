// ot_chip_v41_droop_ctrl -- droop detector response and clock-stretch request for a V4.1 ROM layer die (W18).
//
// Adopted design basis (root, 2026-09-30): a 50% concurrent-pair cap (ot_chip_v41_xcap) plus a droop
// detector with clock stretching, because the current ramp a field-wide op needs to stay within a 5% droop
// depends on the package loop inductance (results/physical_abi3/asap7/chip/v41_w18/peak_current.json).
//
// The sensor is a digital supply monitor sampled every cycle (a TDC / critical-path-monitor code: larger =
// more timing margin = higher local VDD).  This controller:
//   * asserts ``stretch`` on the cycle after the code falls below cfg_trip (one register: the response the
//     clock generator sees within 2 cycles of the sample), and holds it at least cfg_min cycles;
//   * releases only after the code has stayed at or above cfg_release (> cfg_trip, hysteresis) for
//     cfg_hold consecutive cycles, so it cannot chatter around one threshold;
//   * ``stretch`` asks the clock generator to drop every other edge (a divide-by-2 stretch) -- the stretch
//     itself is the generator's, outside this module;
//   * counts events and the longest stretch, and raises ``alarm`` when a stretch lasts cfg_alarm cycles
//     (a supply problem, not a transient droop).
module ot_chip_v41_droop_ctrl #(
    parameter int SW = 8,     // sensor code width
    parameter int CW = 16     // counter width
) (
    input  logic          clk,
    input  logic          rst_n,
    input  logic          en,
    input  logic [SW-1:0] code,         // sampled supply-monitor code
    input  logic [SW-1:0] cfg_trip,     // stretch when code < cfg_trip
    input  logic [SW-1:0] cfg_release,  // release threshold (>= cfg_trip)
    input  logic [7:0]    cfg_min,      // minimum stretch cycles (>= 1)
    input  logic [7:0]    cfg_hold,     // cycles at/above cfg_release before release (>= 1)
    input  logic [CW-1:0] cfg_alarm,    // stretch length that raises alarm
    output logic          stretch,
    output logic [CW-1:0] events,
    output logic [CW-1:0] longest,
    output logic          alarm
);
    logic [SW-1:0] code_q;
    logic [7:0]    min_cnt, ok_cnt;
    logic [CW-1:0] len;
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            code_q <= '1; stretch <= 1'b0; min_cnt <= '0; ok_cnt <= '0; len <= '0;
            events <= '0; longest <= '0; alarm <= 1'b0;
        end else begin
            code_q <= code;
            if (!en) begin
                stretch <= 1'b0; min_cnt <= '0; ok_cnt <= '0; len <= '0;
            end else if (!stretch) begin
                if (code_q < cfg_trip) begin
                    stretch <= 1'b1; min_cnt <= cfg_min; ok_cnt <= '0; len <= CW'(1);
                    events <= events + 1'b1;
                end
            end else begin
                len <= len + 1'b1;
                if (len + 1'b1 > longest) longest <= len + 1'b1;
                if (len + 1'b1 >= cfg_alarm) alarm <= 1'b1;
                if (min_cnt > 8'd1) min_cnt <= min_cnt - 1'b1; else min_cnt <= 8'd0;
                if (code_q >= cfg_release) ok_cnt <= (ok_cnt == 8'hff) ? ok_cnt : ok_cnt + 1'b1;
                else ok_cnt <= '0;
                if (min_cnt <= 8'd1 && code_q >= cfg_release && ok_cnt + 1'b1 >= cfg_hold) begin
                    stretch <= 1'b0; ok_cnt <= '0;
                end
            end
        end
    end
endmodule
