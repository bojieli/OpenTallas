module ot_rst_relay #(
    parameter integer REGIONS     = 4,
    parameter integer SYNC_STAGES = 2,
    parameter integer TREE_STAGES = 1
) (
    input  wire               clk,
    input  wire               rst_n_in,
    output wire [REGIONS-1:0] rst_n
);
    localparam integer RELEASE_CYCLES = SYNC_STAGES + TREE_STAGES;

`line 27 "/srv/opentallas-scratch2/claude/codex-hbm-bind-restore-1101/current/physical/die_plan/hbm/bind/r18h5_bundle/rtl/lib/ot_rst_relay.sv" 0
    (* async_reg = "true" *) reg [SYNC_STAGES-1:0] sync_q;
    always @(posedge clk or negedge rst_n_in) begin
        if (!rst_n_in)
            sync_q <= {SYNC_STAGES{1'b0}};
        else
            sync_q <= {sync_q[SYNC_STAGES-2:0], 1'b1};
    end

`line 35 "/srv/opentallas-scratch2/claude/codex-hbm-bind-restore-1101/current/physical/die_plan/hbm/bind/r18h5_bundle/rtl/lib/ot_rst_relay.sv" 0
     
    (* keep = "true", dont_touch = "true" *) reg [REGIONS-1:0] relay_q [0:TREE_STAGES-1];
    genvar t;
    generate
        for (t = 0; t < TREE_STAGES; t = t + 1) begin : g_stage
            always @(posedge clk or negedge rst_n_in) begin
                if (!rst_n_in)
                    relay_q[t] <= {REGIONS{1'b0}};
                else if (t == 0)
                    relay_q[t] <= {REGIONS{sync_q[SYNC_STAGES-1]}};
                else
                    relay_q[t] <= relay_q[(t == 0) ? 0 : t-1];
            end
        end
    endgenerate

`line 51 "/srv/opentallas-scratch2/claude/codex-hbm-bind-restore-1101/current/physical/die_plan/hbm/bind/r18h5_bundle/rtl/lib/ot_rst_relay.sv" 0
    assign rst_n = relay_q[TREE_STAGES-1];

`line 53 "/srv/opentallas-scratch2/claude/codex-hbm-bind-restore-1101/current/physical/die_plan/hbm/bind/r18h5_bundle/rtl/lib/ot_rst_relay.sv" 0
 
    initial begin
        if (SYNC_STAGES < 2) $error("ot_rst_relay: SYNC_STAGES must be >= 2 (release crosses from the async port)");
        if (TREE_STAGES < 1) $error("ot_rst_relay: TREE_STAGES must be >= 1");
        if (REGIONS < 1)     $error("ot_rst_relay: REGIONS must be >= 1");
    end

`line 60 "/srv/opentallas-scratch2/claude/codex-hbm-bind-restore-1101/current/physical/die_plan/hbm/bind/r18h5_bundle/rtl/lib/ot_rst_relay.sv" 0
endmodule
