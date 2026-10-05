`timescale 1ns/1ps
module f_power_controller;
    (* gclk *) reg clk;
    reg rst_n = 1'b0;
    reg f_past_valid = 1'b0;
    (* anyseq *) reg power_good, clock_stable, core_ready, hbm_ready, link_ready;
    (* anyseq *) reg bist_done, bist_pass, service_request, quiesce_request;
    (* anyseq *) reg core_quiescent, thermal_warning, thermal_fatal, fatal_error;
    (* anyseq *) reg requalify, test_enable;
    wire [3:0] state;
    wire core_reset_n, service_enable, isolation_enable, throttle_enable, safe;
    wire quiesce_ack, stop_ack;
    wire [7:0] reset_cause;

    ot_power_reset_controller dut (
        .aon_clk(clk),.aon_rst_n(rst_n),.power_good(power_good),
        .clock_stable(clock_stable),.core_ready(core_ready),.hbm_ready(hbm_ready),
        .link_ready(link_ready),.bist_done(bist_done),.bist_pass(bist_pass),
        .service_request(service_request),.quiesce_request(quiesce_request),
        .core_quiescent(core_quiescent),.thermal_warning(thermal_warning),
        .thermal_fatal(thermal_fatal),.fatal_error(fatal_error),.requalify(requalify),
        .test_enable(test_enable),.state(state),.core_reset_n(core_reset_n),
        .service_enable(service_enable),.isolation_enable(isolation_enable),
        .throttle_enable(throttle_enable),.safe(safe),.quiesce_ack(quiesce_ack),
        .stop_ack(stop_ack),.reset_cause(reset_cause));

    always @(posedge clk) begin
        f_past_valid <= 1'b1;
        rst_n <= 1'b1;
        if (rst_n) begin
            assert(state <= 4'd4);
            assert(service_enable == ((state == 4'd2) || (state == 4'd3)));
            assert(throttle_enable == (state == 4'd3));
            assert(safe == (state == 4'd4));
            if (safe) begin
                assert(isolation_enable);
                assert(!service_enable);
                assert(!core_reset_n);
            end
            if (core_reset_n) begin
                assert(power_good && clock_stable);
                assert(state == 4'd1 || state == 4'd2 || state == 4'd3);
            end
            if (f_past_valid && $past(rst_n &&
                (!power_good || !clock_stable || thermal_fatal || fatal_error)))
                assert(safe);
            if (f_past_valid && $past(rst_n && test_enable && service_enable))
                assert(safe);
            cover(state == 4'd2);
            cover(state == 4'd3);
            cover(state == 4'd4);
        end
    end
endmodule
