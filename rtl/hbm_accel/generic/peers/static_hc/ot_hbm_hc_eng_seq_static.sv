`timescale 1ns/1ps
`default_nettype none
// HC engine event programme (H-NETLIST/hceng 2026-10-16): a programme SRAM (ot_sram_1r1w_1024x256) of EVENT words,
// each {magic c7a1 [255:240] (the F20 row header the folded ot_static_program_target checks), pc [233:224], payload [W-1:20], time [19:0]}. A launch runs [start_base, start_limit)
// once (start_loops must be 1). The edge counter t starts at 0 on the edge after start_v is captured; the word at the
// queue head fires (payload on `event`, event_v) on the edge where t == time, so its fields are visible to the engine
// in the cycle after that edge. Times must strictly increase; a word reaching the head after its time (late), a bad
// magic/pc, a write while running, or an illegal start faults. Words are prefetched (read -> macro -> capture -> 4-entry
// queue) so one event per edge is sustained; nothing waits on any datapath response.
module ot_hbm_hc_eng_seq_static #(
    parameter integer W = 124
)(
    input  wire          clk, rst_n,
    input  wire          cfg_we,
    input  wire [9:0]    cfg_addr,
    input  wire [255:0]  cfg_data,
    input  wire          start_v,
    input  wire [9:0]    start_base,
    input  wire [10:0]   start_limit,
    input  wire [15:0]   start_loops,
    output reg  [W-1:0]  event_word,
    output reg           event_v,
    output reg  [19:0]   t,
    output reg           active, done, fault
);
    initial if (W < 21 || W > 224) $fatal(1, "event payload must fit");
    // ---- pin flops
    reg cfg_we_q, start_v_q; reg [9:0] cfg_addr_q, start_base_q; reg [255:0] cfg_data_q;
    reg [10:0] start_limit_q; reg [15:0] start_loops_q;
    always @(posedge clk) begin cfg_addr_q <= cfg_addr; cfg_data_q <= cfg_data; start_base_q <= start_base;
        start_limit_q <= start_limit; start_loops_q <= start_loops; end
    always @(posedge clk or negedge rst_n) if (!rst_n) begin cfg_we_q <= 0; start_v_q <= 0; end
        else begin cfg_we_q <= cfg_we; start_v_q <= start_v; end
    // ---- fetch
    reg running;                                // words remain to be read
    reg [9:0] rpc; reg [10:0] limit;
    reg rv0, rv1; reg [9:0] rpc0, rpc1;
    wire [255:0] macro_data; reg [255:0] captured;
    reg [2:0] qn;                               // queued words
    wire [2:0] inflight = {2'b0, rv0} + {2'b0, rv1};
    wire issue = running && (qn + inflight) < 3'd4;
    reg [W+9:0] q [0:3];                        // {pc, payload}
    reg [1:0] qh, qt;
    reg busy;
    ot_sram_1r1w_1024x256_m2_r2c2 u_program(
        .clk(clk), .r_ce_in(issue), .r_addr_in(rpc), .rd_out(macro_data),
        .w_ce_in(cfg_we_q && !busy && !start_v_q), .w_addr_in(cfg_addr_q), .wd_in(cfg_data_q), .w_mask_in({256{1'b1}}),
        .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
    always @(posedge clk) captured <= macro_data;
    wire word_ok = captured[255:240] == 16'hc7a1 && captured[233:224] == rpc1 && captured[239:234] == 0 &&
                   captured[223:W] == 0;
    wire [W-1:0] head = q[qh][W-1:0];
    wire head_v = qn != 0;
    wire fire = head_v && head[19:0] == t;
    wire legal_start = start_limit_q > {1'b0, start_base_q} && start_limit_q <= 11'd1024 && start_loops_q == 16'd1;
    reg [19:0] last_time; reg have_last;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            running <= 0; rpc <= 0; limit <= 0; rv0 <= 0; rv1 <= 0; qn <= 0; qh <= 0; qt <= 0; busy <= 0; t <= 0;
            event_v <= 0; active <= 0; done <= 0; fault <= 0; have_last <= 0; last_time <= 0;
        end else begin
            event_v <= 1'b0; done <= 1'b0;
            if (busy) t <= t + 1'b1;
            rv0 <= issue; rv1 <= rv0; rpc0 <= rpc; rpc1 <= rpc0;
            if (issue) begin
                rpc <= rpc + 1'b1;
                if ({1'b0, rpc} + 11'd1 == limit) running <= 1'b0;
            end
            if (rv1) begin
                if (!word_ok) fault <= 1'b1;
                q[qt] <= {rpc1, captured[W-1:0]}; qt <= qt + 1'b1;
            end
            if (fire) begin
                event_word <= head; event_v <= 1'b1; qh <= qh + 1'b1;
                if (have_last && head[19:0] <= last_time) fault <= 1'b1;
                last_time <= head[19:0]; have_last <= 1'b1;
            end
            if (head_v && head[19:0] < t) fault <= 1'b1;             // late word
            qn <= qn + (rv1 ? 3'd1 : 3'd0) - (fire ? 3'd1 : 3'd0);
            // end of programme: nothing left to read, in flight or queued
            if (busy && !running && !rv0 && !rv1 && (qn == 0 || (qn == 1 && fire)) && !issue) begin
                busy <= 1'b0; done <= 1'b1;
            end
            active <= busy;
            if (cfg_we_q && (busy || start_v_q)) fault <= 1'b1;
            if (start_v_q) begin
                if (busy || cfg_we_q || !legal_start) fault <= 1'b1;
                else begin running <= 1'b1; busy <= 1'b1; rpc <= start_base_q; limit <= start_limit_q; t <= 0;
                           have_last <= 1'b0; end
            end
        end
    end
endmodule
`default_nettype wire
