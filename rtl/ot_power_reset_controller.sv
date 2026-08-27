`timescale 1ns/1ps
// AON-owned power/reset/service FSM.  This is logical power intent: physical
// switches, PLLs, isolation cells, and sensors remain external macros.
module ot_power_reset_controller (
    input  wire       aon_clk,
    input  wire       aon_rst_n,
    input  wire       power_good,
    input  wire       clock_stable,
    input  wire       core_ready,
    input  wire       hbm_ready,
    input  wire       link_ready,
    input  wire       bist_done,
    input  wire       bist_pass,
    input  wire       service_request,
    input  wire       quiesce_request,
    input  wire       core_quiescent,
    input  wire       thermal_warning,
    input  wire       thermal_fatal,
    input  wire       fatal_error,
    input  wire       requalify,
    input  wire       test_enable,
    output reg [3:0] state,
    output wire       core_reset_n,
    output wire       service_enable,
    output wire       isolation_enable,
    output wire       throttle_enable,
    output wire       safe,
    output reg        quiesce_ack,
    output reg        stop_ack,
    output reg [7:0]  reset_cause
);
    localparam [3:0] ST_STANDBY = 4'd0;
    localparam [3:0] ST_IDLE = 4'd1;
    localparam [3:0] ST_ACTIVE = 4'd2;
    localparam [3:0] ST_THROTTLED = 4'd3;
    localparam [3:0] ST_SAFE = 4'd4;
    reg [3:0] next_state;
    reg [1:0] stable_count;
    reg resources_ready;

    assign safe = (state == ST_SAFE);
    assign isolation_enable = (state == ST_STANDBY) || (state == ST_SAFE);
    assign service_enable = (state == ST_ACTIVE) || (state == ST_THROTTLED);
    assign throttle_enable = (state == ST_THROTTLED);
    assign core_reset_n = (state != ST_STANDBY) && (state != ST_SAFE) && power_good && clock_stable;

    always @* begin
        resources_ready = power_good && clock_stable && core_ready && hbm_ready &&
                          link_ready && bist_done && bist_pass;
        next_state = state;
        if (!power_good || !clock_stable || thermal_fatal || fatal_error) begin
            next_state = ST_SAFE;
        end else begin
            case (state)
                ST_STANDBY: if (resources_ready) next_state = ST_IDLE;
                ST_IDLE: begin
                    if (service_request) next_state = ST_ACTIVE;
                    else if (quiesce_request) next_state = ST_IDLE;
                end
                ST_ACTIVE: begin
                    if (thermal_warning) next_state = ST_THROTTLED;
                    else if (quiesce_request && core_quiescent) next_state = ST_IDLE;
                end
                ST_THROTTLED: begin
                    if (thermal_fatal) next_state = ST_SAFE;
                    else if (!thermal_warning && service_request) next_state = ST_ACTIVE;
                    else if (quiesce_request && core_quiescent) next_state = ST_IDLE;
                end
                ST_SAFE: if (requalify && resources_ready) next_state = ST_STANDBY;
                default: next_state = ST_SAFE;
            endcase
        end
    end

    always @(posedge aon_clk or negedge aon_rst_n) begin
        if (!aon_rst_n) begin
            state <= ST_STANDBY;
            stable_count <= 2'b0;
            quiesce_ack <= 1'b0;
            stop_ack <= 1'b0;
            reset_cause <= 8'h00;
        end else begin
            state <= next_state;
            if (!power_good) reset_cause <= 8'h01;
            else if (!clock_stable) reset_cause <= 8'h02;
            else if (thermal_fatal) reset_cause <= 8'h03;
            else if (fatal_error) reset_cause <= 8'h04;
            if (power_good && clock_stable) begin
                if (stable_count != 2'b11)
                    stable_count <= stable_count + 1'b1;
            end else begin
                stable_count <= 2'b0;
            end
            quiesce_ack <= quiesce_request && core_quiescent;
            stop_ack <= (state == ST_STANDBY) || (state == ST_SAFE);
            if (test_enable && service_enable)
                reset_cause <= 8'h05; // mutually exclusive service/test guard
        end
    end

`ifndef SYNTHESIS
    always @(posedge aon_clk) begin
        if (state == ST_ACTIVE && thermal_fatal)
            assert (next_state == ST_SAFE);
        if (state == ST_SAFE)
            assert (!service_enable && isolation_enable);
    end
`endif
endmodule
