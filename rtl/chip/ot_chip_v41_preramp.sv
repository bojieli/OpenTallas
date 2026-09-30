// ot_chip_v41_preramp -- schedule-driven current pre-ramp of the V4.1 ROM field (W18).
//
// Adopted (root, AGENTS.md c0894b1c): 50% concurrent-pair cap + a 256-cycle schedule-driven pre-ramp.
// The single-user token schedule is static, so the die sequencer knows, cycles ahead, when the next
// field-wide op starts.  This unit turns that into a current ramp that costs no latency:
//   * ``start_in`` = cycles until the next field-wide op's first x word leaves the root (0 = none pending);
//   * over the cfg_ramp cycles before a start that follows an IDLE GAP (longer than cfg_gap, the droop time
//     constant), it raises a thermometer of NG group enables, one group every cfg_ramp/NG cycles; enabled
//     groups without a real x word run DUMMY work (ICG on, datapath fed the held x word, results discarded),
//     so the pairs draw their busy current early and every group is on when the real op starts;
//   * when an op ends and the next starts within max(cfg_gap, cfg_ramp) cycles (back-to-back ops, set cfg_gap
//     to the droop time constant or longer), the field HOLDS all
//     groups on (dummy work in the gap): no ramp down and no ramp up, since the current never steps;
//   * otherwise, after an op the enables fall one group every cfg_ramp/NG cycles (ramp-down: the release
//     does not ring either);
//   * groups are interleaved over the field (group = pair index mod NG), so every IR window ramps together.
// Energy: the dummy work of ramps and held gaps (tools/w18/droop_sim.py, W16 prices it).
module ot_chip_v41_preramp #(
    parameter int NG = 64,       // pair groups
    parameter int CW = 16
) (
    input  logic          clk,
    input  logic          rst_n,
    input  logic [CW-1:0] cfg_ramp,     // ramp length in cycles (multiple of NG, >= NG)
    input  logic [CW-1:0] cfg_gap,      // gaps up to this many cycles are held, not ramped
    input  logic [CW-1:0] start_in,     // cycles to the next field op start (0 = none scheduled)
    input  logic          op_active,    // the field op is issuing
    output logic [NG-1:0] grp_en,       // group enables (dummy or real work)
    output logic [NG-1:0] grp_dummy,    // enabled groups that are running dummy work
    output logic          holding       // the field is held on through a short gap
);
    localparam int LW = $clog2(NG + 1);
    logic [CW-1:0] step;               // cycles per group
    logic [CW-1:0] cnt;
    logic [LW-1:0] level;              // enabled groups
    assign step = cfg_ramp / CW'(NG);
    wire full      = (32'(level) == NG);
    wire want_up   = (start_in != '0) && (start_in <= cfg_ramp);
    wire want_hold = full && (start_in != '0) && (start_in <= cfg_gap);
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            level <= '0; cnt <= '0; holding <= 1'b0;
        end else if (op_active) begin
            level <= LW'(NG); cnt <= '0; holding <= 1'b0;
        end else if (want_hold || holding && start_in != '0) begin
            holding <= 1'b1; cnt <= '0;                         // back-to-back: stay on through the gap
        end else if (want_up) begin
            holding <= 1'b0;
            if (cnt + 1'b1 >= step) begin
                cnt <= '0;
                if (!full) level <= level + 1'b1;
            end else cnt <= cnt + 1'b1;
        end else if (level != '0) begin
            holding <= 1'b0;
            if (cnt + 1'b1 >= step) begin cnt <= '0; level <= level - 1'b1; end
            else cnt <= cnt + 1'b1;
        end else begin
            cnt <= '0; holding <= 1'b0;
        end
    end
    always_comb begin
        for (int g = 0; g < NG; g++) grp_en[g] = (g < 32'(level)) || op_active;
        grp_dummy = op_active ? '0 : grp_en;
    end
endmodule
