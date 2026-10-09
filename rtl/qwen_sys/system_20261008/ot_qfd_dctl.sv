`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// Die master qfd_dctl (stream qwen-system, 2026-10-08): the per-die STAGE STEPPER of the full-shape Qwen3-8B ROM die.
//
// At full shape a decode step is NS = 38 stages (E: embedding, L0..L35, H: lm_head + argmax all-gather); the C++
// host of results/rtl/qwen_plain_ar_stream4_P8191_20261005 (tools/runtime/qwen_baseline_ar_stream4/
// qwen_rom_rt_w12_stream4_fulltoken.cpp) stepped them: per stage it set rm_layer / rm_next_layer, swapped the stage
// images and pulsed h_start with the step's {token, position}; it waited for s_done (after seeing it low: the
// done_armed rule), stopped on any sequencer / core / collective fault, consumed seq_ntok / seq_nval at H, and after H
// waited for the posted KV write-back to drain.  This block is that loop in hardware, per die:
//
//   d_start (token, pos)  ->  for s in 0..NS-1:
//        stage = s, st_layer = layer(s) (63 = no KV: E, H), st_next_layer = layer(s+1) (the KV prefetch notice),
//        st_code / st_scale = the stage's weight-ROM / scale-ROM bases, st_prog = its program (0 E, 1 layer, 2 head),
//        crom stage index = layer (HEAD = 36 at H): from the stage table (STAB, generated: tools/qwen_system/ctl_golden.py)
//        h_start one cycle (the sequencer master latches tp_token / tp_pos with it), then wait s_done (armed)
//   at H: next_token / next_val = seq_ntok / seq_nval (rejected if >= VOCAB: fault)
//   then wait kv_write_drained; d_done = 1 with {next_token, next_val} until the next d_start.
// Faults (sticky, fail closed: the step completes at once with d_fault): sequencer / core / collective fault, a stage
// longer than WDOG cycles, an out-of-vocabulary token, a d_start while busy.  Stage switch: the next stage's table
// entry is registered while a stage runs, so its h_start leaves on the edge after the (stationed) s_done; the first
// stage of a step waits ST_GAP edges for its table read.
// Interface timing: every input is stationed (one IS flop), every output leaves from a flop.
// ---------------------------------------------------------------------------------------------------------------------
module ot_qfd_dctl #(
    parameter integer NW     = 18,
    parameter integer AW     = 24,
    parameter integer NS     = 38,
    parameter integer SW_    = 6,             // stage index bits
    parameter integer VOCAB  = 151936,
    parameter integer WDOG   = 1 << 20,       // cycles a stage may take
    parameter integer ST_GAP = 2,
    // WDQ (struct-close 2026-10-09, drive-0849 / coordinator: ICUT sequencer compact outline -525 = u_dctl.q_start -> u_dctl.wd,
    // ~1 ns: the start-busy priority + state case + 32-bit increment + the wd >= WDOG compare in one stage): WDQ = 1 moves the
    // watchdog to its own always block (no q_start priority; its value is unused once the step faults to S_DONE and is
    // cleared at the next h_start) and replaces wd >= WDOG by a register updated with wd (exact).  0 cycles.
    parameter integer WDQ    = 0,
    // stage table: per stage {prog[1:0], layer[5:0], code_base[AW-1:0], scale_base[AW-1:0]} (NS entries, entry 0 low)
    parameter [NS*(2+6+2*AW)-1:0] STAB = '0
) (
    input  wire              clk,
    input  wire              rst_n,
    // package control (stationed in)
    input  wire              d_start,
    input  wire [NW-1:0]     d_token,
    input  wire [NW-1:0]     d_pos,
    input  wire [1:0]        d_gen,            // step generation: the done report names the step it completes
    output reg               d_done,
    output reg  [1:0]        d_done_gen,
    output reg  [NW-1:0]     d_next_token,
    output reg  [31:0]       d_next_val,
    output reg               d_drained,
    output reg               d_fault,
    output reg  [3:0]        d_fault_code,     // 1 seq 2 core 3 coll 4 wdog 5 vocab 6 start-busy
    output reg  [31:0]       d_cycles,
    // to the sequencer master (qfd_sp_constants_sequencer) and the memory services
    output reg               h_start,
    output reg  [NW-1:0]     tp_token,
    output reg  [NW-1:0]     tp_pos,
    output reg  [SW_-1:0]    stage,
    output reg  [1:0]        st_prog,
    output reg  [5:0]        st_layer,         // KV layer of this stage (63: none)
    output reg  [5:0]        st_next_layer,    // KV layer of the next stage (63: none): the prefetch notice
    output reg  [5:0]        st_crom,          // constant-ROM stage index (layer, 36 at H)
    output reg  [AW-1:0]     st_code,
    output reg  [AW-1:0]     st_scale,
    input  wire              s_done,
    input  wire [NW-1:0]     seq_ntok,
    input  wire [31:0]       seq_nval,
    input  wire              s_fault,
    input  wire              core_fault,
    input  wire              coll_fault,
    input  wire              kv_write_drained
);
    localparam integer EW = 2 + 6 + 2*AW;
    localparam [2:0] S_IDLE = 0, S_LOAD = 1, S_GO = 2, S_ARM = 3, S_WAIT = 4, S_DRAIN = 5, S_DONE = 6;

    // ---- input stations ----
    reg          q_start, q_done, q_sf, q_cf, q_lf, q_dr;
    reg [NW-1:0] q_tok, q_pos, q_ntok;
    reg [1:0]    q_gen;
    reg [31:0]   q_nval;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin q_start <= 0; q_done <= 0; q_sf <= 0; q_cf <= 0; q_lf <= 0; q_dr <= 0; end
        else begin
            q_start <= d_start; q_done <= s_done; q_sf <= s_fault; q_cf <= core_fault; q_lf <= coll_fault;
            q_dr <= kv_write_drained;
        end
    end
    always @(posedge clk) begin q_gen <= d_gen; q_tok <= d_token; q_pos <= d_pos; q_ntok <= seq_ntok; q_nval <= seq_nval; end

    // ---- stage table read (registered) ----
    reg  [SW_-1:0] s;
    reg  [EW-1:0]  ent, ent_n, ent_nn;
    wire [SW_-1:0] s_n = s + 1'b1;
    always @(posedge clk) begin
        ent   <= STAB[s * EW +: EW];
        ent_n <= (s_n < NS) ? STAB[s_n * EW +: EW] : {2'd0, 6'd63, {(2*AW){1'b0}}};
        ent_nn <= (s_n + 1 < NS) ? STAB[(s_n + 1) * EW +: EW] : {2'd0, 6'd63, {(2*AW){1'b0}}};
    end

    reg [2:0]  st;
    reg [31:0] wd;
    // WDQ: the watchdog counter and its expiry flag, outside the start-busy priority (see the parameter)
    reg [31:0] wdq; reg wd_ge;
    wire wd_clr = (st == S_LOAD && gap + 1 >= ST_GAP) ||
                  (st == S_WAIT && !fault_in && !wd_ge && q_done && st_prog != 2'd2 && s_n != NS);
    wire wd_cnt = (st == S_ARM) || (st == S_WAIT);
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin wdq <= 0; wd_ge <= 1'b0; end
        else if (WDQ != 0) begin
            if (wd_clr) begin wdq <= 0; wd_ge <= 1'b0; end
            else if (wd_cnt) begin wdq <= wdq + 1; wd_ge <= (wdq + 1 >= WDOG); end
        end
    reg [1:0]  gap;
    wire       fault_in = q_sf || q_cf || q_lf;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; s <= 0; wd <= 0; gap <= 0; h_start <= 1'b0; d_done <= 1'b0; d_drained <= 1'b0;
            d_fault <= 1'b0; d_fault_code <= 0; d_cycles <= 0; d_next_token <= 0; d_next_val <= 0; d_done_gen <= 0;
            tp_token <= 0; tp_pos <= 0; stage <= 0; st_prog <= 0; st_layer <= 6'd63; st_next_layer <= 6'd63;
            st_crom <= 0; st_code <= 0; st_scale <= 0;
        end else begin
            h_start <= 1'b0;
            if (st != S_IDLE && st != S_DONE) d_cycles <= d_cycles + 1;
            if (q_start && st != S_IDLE && st != S_DONE) begin
                d_fault <= 1'b1; d_fault_code <= 4'd6; st <= S_DONE; d_done <= 1'b1;
            end else case (st)
                S_IDLE, S_DONE:
                    if (q_start) begin
                        // a new step: d_done falls on the edge that samples the start (the pkg_ctl contract)
                        d_done <= 1'b0; d_drained <= 1'b0; d_cycles <= 0; d_fault <= 1'b0; d_fault_code <= 0;
                        tp_token <= q_tok; tp_pos <= q_pos; s <= 0; gap <= 0; st <= S_LOAD; d_done_gen <= q_gen;
                    end
                S_LOAD: begin
                    // ST_GAP edges: the table entry of s is registered, then driven with h_start
                    gap <= gap + 1'b1;
                    if (gap + 1 >= ST_GAP) begin
                        stage <= s; st_prog <= ent[EW-1 -: 2]; st_layer <= ent[2*AW +: 6];
                        st_crom <= (ent[EW-1 -: 2] == 2'd2) ? 6'd36 : ent[2*AW +: 6];
                        st_next_layer <= ent_n[2*AW +: 6];
                        st_code <= ent[AW +: AW]; st_scale <= ent[0 +: AW];
                        h_start <= 1'b1; wd <= 0; st <= S_ARM;
                    end
                end
                S_ARM: begin
                    // done_armed: the sequencer's done of the previous stage must fall first
                    wd <= wd + 1;
                    if (fault_in) begin d_fault <= 1'b1; d_fault_code <= q_sf ? 4'd1 : q_cf ? 4'd2 : 4'd3; st <= S_DONE; d_done <= 1'b1; end
                    else if (!q_done) st <= S_WAIT;
                end
                S_WAIT: begin
                    wd <= wd + 1;
                    if (fault_in) begin d_fault <= 1'b1; d_fault_code <= q_sf ? 4'd1 : q_cf ? 4'd2 : 4'd3; st <= S_DONE; d_done <= 1'b1; end
                    else if ((WDQ != 0) ? wd_ge : (wd >= WDOG)) begin d_fault <= 1'b1; d_fault_code <= 4'd4; st <= S_DONE; d_done <= 1'b1; end
                    else if (q_done) begin
                        if (st_prog == 2'd2) begin
                            d_next_token <= q_ntok; d_next_val <= q_nval;
                            if (q_ntok >= VOCAB) begin d_fault <= 1'b1; d_fault_code <= 4'd5; st <= S_DONE; d_done <= 1'b1; end
                            else st <= S_DRAIN;
                        end else if (s_n == NS) st <= S_DRAIN;
                        else begin
                            // the next stage's entry (ent_n, registered while this stage ran) issues at once
                            s <= s_n; stage <= s_n; st_prog <= ent_n[EW-1 -: 2]; st_layer <= ent_n[2*AW +: 6];
                            st_crom <= (ent_n[EW-1 -: 2] == 2'd2) ? 6'd36 : ent_n[2*AW +: 6];
                            st_next_layer <= ent_nn[2*AW +: 6];
                            st_code <= ent_n[AW +: AW]; st_scale <= ent_n[0 +: AW];
                            h_start <= 1'b1; wd <= 0; st <= S_ARM;
                        end
                    end
                end
                S_DRAIN: if (q_dr) begin d_drained <= 1'b1; d_done <= 1'b1; st <= S_DONE; end
                default: st <= S_IDLE;
            endcase
        end
    end
endmodule
