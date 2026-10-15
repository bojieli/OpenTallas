`timescale 1ns/1ps
// Candidate only: ck_master is a REAL continuously running 3.6GHz source.
// No such physical source output is supplied by ot_s81_pll_bb today.
// /3 is deliberately 1/3 duty: never apply legacy 50% /3 constraints.
// Lock loss invalidates immediately and drains to frame end. Reset parks
// on the next master edge: serial high may shorten to ONE master tick.
// Source must keep ticking >=12 edges after lock loss; abrupt source failure
// cannot be repaired by digital logic. Reset must cover >=1 master edge.
module ot_s81_common_clock_epoch (
    input wire ck_master, input wire rst_n, input wire source_lock,
    output reg ck_stream, output reg ck_serial,
    output wire phase_valid, output wire epoch_window,
    output reg epoch_toggle, output reg epoch_fault,
    output reg [3:0] phase, output reg running
);
    (* async_reg = "true" *) reg lock_meta, lock_sync;
    (* async_reg = "true" *) reg reset_meta, reset_sync;
    reg stop_pending, armed, window_armed, window_reg;
    wire qualified = rst_n && source_lock && lock_sync;
    wire lock_reset_n = rst_n && source_lock;
    // Async clear captures even lock drops shorter than one master period.
    always @(posedge ck_master or negedge lock_reset_n)
        if (!lock_reset_n) begin lock_meta <= 0; lock_sync <= 0; end
        else begin lock_meta <= 1; lock_sync <= lock_meta; end
    always @(posedge ck_master or negedge rst_n)
        if (!rst_n) begin reset_meta <= 0; reset_sync <= 0; end
        else begin reset_meta <= 1; reset_sync <= reset_meta; end
    assign phase_valid = qualified && running && armed && !stop_pending;
    // Registered E11..E13 window surrounds recurring common rising edges.
    // First window is E23..E25; first valid is E12. Consumers arm locally.
    assign epoch_window = phase_valid && window_reg;
    wire [3:0] next_phase = (phase == 11) ? 0 : phase + 1'b1;
    always @(posedge ck_master) begin
        if (!reset_sync) epoch_fault <= 0;
        else if (running && (!qualified || phase > 11)) epoch_fault <= 1;
        // Synchronous cold initialization: do not asynchronously truncate clocks.
        if (!reset_sync) begin
            ck_stream <= 0; ck_serial <= 0; phase <= 11; running <= 0;
            armed <= 0; window_armed <= 0; window_reg <= 0; stop_pending <= 0; epoch_toggle <= 0;
        end else if (phase > 11) begin
            ck_stream <= 0; ck_serial <= 0; running <= 0; phase <= 11;
            armed <= 0; window_armed <= 0; window_reg <= 0; stop_pending <= 1;
        end else if (!running || (phase == 11 && (stop_pending || !qualified))) begin
            ck_stream <= 0; ck_serial <= 0; phase <= 11;
            running <= 0; armed <= 0; window_armed <= 0; window_reg <= 0; stop_pending <= 0;
            if (qualified && !stop_pending) begin
                running <= 1; phase <= 0; ck_stream <= 1; ck_serial <= 1;
            end
        end else begin
            if (!qualified) stop_pending <= 1;
            phase <= next_phase;
            window_reg <= (phase == 10 && armed) || (phase == 11 && window_armed);
            ck_stream <= (next_phase == 0 || next_phase == 3 || next_phase == 6 || next_phase == 9);
            ck_serial <= (next_phase == 0 || next_phase == 1 || next_phase == 4 || next_phase == 5 || next_phase == 8 || next_phase == 9);
            if (phase == 10 && armed) window_armed <= 1;
            if (phase == 11) begin armed <= 1; epoch_toggle <= !epoch_toggle; end
        end
    end
endmodule
