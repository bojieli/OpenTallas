// ot_chip_v41_preramp -- schedule-driven current pre-ramp of the V4.1 ROM field (W18).
//
// The single-user token schedule is static, so the die sequencer knows, cycles ahead, when the next
// field-wide op starts and ends.  This unit turns that knowledge into a current ramp that costs no latency:
//   * ``start_in`` = cycles until the next field-wide op's first x word leaves the root (0 = none pending);
//   * over the RAMP cycles before the start, it raises a thermometer of NG group enables, one more group
//     every RAMP/NG cycles; an enabled group whose pairs have no real x word runs DUMMY work (its ICG on and
//     its datapath fed the held x word, results discarded) -- the pairs draw their busy current early;
//   * at the op start every group is on (the real op takes over, no step);
//   * ``end_in`` = cycles until the op's last issue; after it the enables fall back one group every RAMP/NG
//     cycles (a ramp-down, so the release does not ring either);
//   * groups are interleaved over the field (group = pair index mod NG, the same checkerboard idea as the
//     cap), so every IR window ramps together.
// Energy cost: the dummy work of the ramp, ~ RAMP/2 busy-field cycles per op edge (tools/w18/droop_sim.py).
module ot_chip_v41_preramp #(
    parameter int NG = 64,       // pair groups
    parameter int CW = 16
) (
    input  logic          clk,
    input  logic          rst_n,
    input  logic [CW-1:0] cfg_ramp,     // ramp length in cycles (multiple of NG, >= NG)
    input  logic [CW-1:0] start_in,     // cycles to the next field op start (0 = none scheduled)
    input  logic          op_active,    // the field op is issuing
    output logic [NG-1:0] grp_en,       // group enables (dummy or real work)
    output logic [NG-1:0] grp_dummy     // enabled groups that are running dummy work
);
    logic [CW-1:0] step;               // cycles per group
    logic [CW-1:0] cnt;
    logic [$clog2(NG+1)-1:0] level;    // enabled groups
    assign step = cfg_ramp / CW'(NG);
    // up-ramp: start when the op is at most cfg_ramp cycles away
    wire want_up = (start_in != '0) && (start_in <= cfg_ramp);
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            level <= '0; cnt <= '0;
        end else if (op_active) begin
            level <= NG[$clog2(NG+1)-1:0]; cnt <= '0;
        end else if (want_up) begin
            // level follows the remaining time: groups on = NG - ceil(start_in / step)
            if (cnt + 1'b1 >= step) begin
                cnt <= '0;
                if (32'(level) < NG) level <= level + 1'b1;
            end else cnt <= cnt + 1'b1;
        end else if (level != '0) begin
            if (cnt + 1'b1 >= step) begin cnt <= '0; level <= level - 1'b1; end
            else cnt <= cnt + 1'b1;
        end else cnt <= '0;
    end
    always_comb begin
        for (int g = 0; g < NG; g++) grp_en[g] = (g < level) || op_active;
        grp_dummy = op_active ? '0 : grp_en;
    end
endmodule
